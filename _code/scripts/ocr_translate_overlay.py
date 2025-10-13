# -*- coding: utf-8 -*-
"""
scripts/run_translate_overlay.py

단일 이미지에 대해:
  1) OCR → 2) 번역 → 3) 번역문 오버레이 → 4) 저장(+로그)
- 절대경로만 받음(이 스크립트 내부에서는 paths.local.yaml 사용 안함)
- 섹션 키: image/ocr/translate/overlay/oto (없어도 동작; 필요한 것만 사용)
- 파일 경로 우선순위(이미지 소스): oto > overlay > ocr > image

필수 외부 모듈:
  modules.ocr.run_ocr
  modules.translate.run_translate
  modules.overlay.render_overlay
  modules.fileio: resolve_file_path, must_abs, default_log_dir_for, ensure_log_file, append_log
  modules.datautil: dedupe_keep_order, is_blank, is_number_or_symbol_only, norm_text_key
  modules.yamlutil: load_yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import os

# --- 단순 import --------------------------------------------------------------
from modules.yamlutil import load_yaml
from modules.fileio import resolve_file_path, must_abs, default_log_dir_for, ensure_log_file, append_log
from modules.datautil import (
    dedupe_keep_order,
    is_blank,
    is_number_or_symbol_only,
    norm_text_key,
)
from ocr.ocr import run_ocr
from translate.translate import run_translate
from pillow_utils.overlay import render_overlay


__all__ = ["run_oto"]


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------
PathLike = Union[str, Path]

def _as_dict(cfg_like: Union[Dict[str, Any], PathLike]) -> Dict[str, Any]:
    if isinstance(cfg_like, (str, Path)):
        data = load_yaml(cfg_like) or {}
        if not isinstance(data, dict):
            raise ValueError("YAML 루트는 dict여야 합니다.")
        return data
    if not isinstance(cfg_like, dict):
        raise TypeError("cfg_like 는 dict|str|Path 여야 합니다.")
    return dict(cfg_like)  # shallow copy

def _get_secs(cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """루트에서 image/ocr/translate/overlay/oto 섹션만 추출(없으면 빈 dict)."""
    return {
        "image": dict(cfg.get("image") or {}),
        "ocr": dict(cfg.get("ocr") or {}),
        "translate": dict(cfg.get("translate") or {}),
        "overlay": dict(cfg.get("overlay") or {}),
        "oto": dict(cfg.get("oto") or {}),
    }

def _ensure_file_paths_inherit(secs: Dict[str, Dict[str, Any]], src_path: str) -> None:
    """image.file_path, ocr.file_path 가 비었으면 oto.file_path(src_path) 상속."""
    if not secs["image"].get("file_path"):
        secs["image"]["file_path"] = src_path
    if not secs["ocr"].get("file_path"):
        secs["ocr"]["file_path"] = src_path
    if not secs["overlay"].get("file_path"):
        secs["overlay"]["file_path"] = src_path

def _find_src_path(secs: Dict[str, Dict[str, Any]]) -> str:
    """파일 경로 우선순위: oto > overlay > ocr > image"""
    return resolve_file_path(secs, ["oto", "overlay", "ocr", "image"], key="file_path")

def _bbox_to_poly(bbox: List[float]) -> List[List[float]]:
    x0, y0, x1, y1 = map(float, bbox)
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

def _pick_triple_from_translate(res: Any) -> Tuple[List[str], Optional[str], Dict[str, Any]]:
    """
    run_translate 반환값을 (out_texts, saved_tr_json, meta_tr)로 정규화.
    """
    outs: List[str] = []
    saved: Optional[str] = None
    meta: Dict[str, Any] = {}
    if isinstance(res, (list, tuple)):
        # 관례: (outs, saved_tr_json, meta_tr)
        if len(res) >= 1 and isinstance(res[0], list):
            outs = res[0]
        if len(res) >= 2 and isinstance(res[1], (str, type(None))):
            saved = res[1]
        if len(res) >= 3 and isinstance(res[2], dict):
            meta = res[2]
    elif isinstance(res, dict):
        outs = list(res.get("outs") or [])
        saved = res.get("saved_tr_json")
        meta = dict(res.get("meta") or {})
    return outs, saved, meta

def _extract_ocr_triplets(meta_ocr: Dict[str, Any]) -> tuple[
    list[str], list[str], list[Optional[list[list[float]]]]
]:
    """OCR items에서 (원문, 키, poly) 배출."""
    texts_src, texts_key, item_polys = [], [], []
    items = [it for it in meta_ocr.get("items", []) if isinstance(it, dict)]
    for it in items:
        t = str(it.get("text", "") or "")
        if not t:
            continue
        if is_number_or_symbol_only(t):
            continue
        k = norm_text_key(t)
        if not k:
            continue

        if isinstance(it.get("poly"), list) and len(it["poly"]) == 4:
            poly = it["poly"]
        elif isinstance(it.get("quad"), list) and len(it["quad"]) == 4:
            poly = it["quad"]
        elif isinstance(it.get("bbox"), (list, tuple)) and len(it["bbox"]) == 4:
            poly = _bbox_to_poly(it["bbox"])
        else:
            poly = None

        texts_src.append(t)
        texts_key.append(k)
        item_polys.append(poly)

    return texts_src, texts_key, item_polys

def _build_translation_map(texts_key: list[str], texts_src: list[str], outs: list[str]) -> dict[str, str]:
    """정규화 키 기준 dedupe 후 번역 결과를 키에 매핑."""
    # key→첫 원문
    key_to_first_text: Dict[str, str] = {}
    for k, t in zip(texts_key, texts_src):
        if k not in key_to_first_text:
            key_to_first_text[k] = t
    dedup_keys = dedupe_keep_order(list(key_to_first_text.keys()))
    # outs는 run_translate 호출 직후의 결과여야 정렬 일치
    return {k: str(o or "") for k, o in zip(dedup_keys, outs)}, dedup_keys, [key_to_first_text[k] for k in dedup_keys]

def _compose_overlay_items(
    texts_src: list[str],
    texts_key: list[str],
    item_polys: list[Optional[list[list[float]]]],
    tr_map: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """OCR 순서 그대로 overlay 'ol' 리스트 생성 + 통계 반환."""
    ol_items: list[dict[str, Any]] = []
    matched = 0
    skipped_no_poly = 0
    for t_src, k, poly in zip(texts_src, texts_key, item_polys):
        if not poly:
            skipped_no_poly += 1
            continue
        t_tr = tr_map.get(k, t_src)
        if k in tr_map:
            matched += 1
        # 번역이 없어도(빈 문자열) 항목은 넣는다. overlay가 알아서 skip.
        ol_items.append({"text": t_tr, "poly": poly})
    stats = {"matched": matched, "skipped_no_poly": skipped_no_poly, "total": len(texts_src)}
    return ol_items, stats

# ---------------------------------------------------------------------------
# 메인 파이프라인
# ---------------------------------------------------------------------------
def run_oto(cfg_like: Union[Dict[str, Any], PathLike]) -> Dict[str, Any]:
    """
    OCR → TRANSLATE → OVERLAY → SAVE
    - 입력: 섹션 dict 루트 또는 YAML 경로
    - 출력: dict (요약/결과 경로 등)
    """
    cfg_root = _as_dict(cfg_like)
    secs = _get_secs(cfg_root)

    # 0) 소스 이미지 경로 확정
    src_path = _find_src_path(secs)
    must_abs(src_path, "oto.file_path (source)")
    _ensure_file_paths_inherit(secs, src_path)

    # 1) OCR
    ocr_cfg = dict(secs["ocr"]); ocr_cfg["file_path"] = src_path
    ocr_items, meta_ocr, _ = run_ocr({"ocr": ocr_cfg})  # 명시 언패킹
    # OCR → triplets
    texts_src, texts_key, item_polys = _extract_ocr_triplets(meta_ocr)

    # 2) TRANSLATE (입력: key dedupe → 첫 원문)
    tr_cfg = dict(secs["translate"])
    parent_dir = str(Path(src_path).parent)
    if is_blank(tr_cfg.get("db_dir")): tr_cfg["db_dir"] = parent_dir
    else: must_abs(tr_cfg["db_dir"], "translate.db_dir")
    if is_blank(tr_cfg.get("tr_dir")): tr_cfg["tr_dir"] = parent_dir
    else: must_abs(tr_cfg["tr_dir"], "translate.tr_dir")

    # dedupe용 key 리스트와 번역 입력
    tr_map_dummy, dedup_keys, dedup_texts_for_translate = _build_translation_map(texts_key, texts_src, [])
    # 실제 매핑 완성
    if not dedup_texts_for_translate:
        # Nothing to translate — skip calling provider
        outs, saved_tr_json, meta_tr = [], None, {"skipped": True, "reason": "no_texts_for_translation"}
    else:
        outs, saved_tr_json, meta_tr = _pick_triple_from_translate(
            run_translate({"translate": {**tr_cfg, "text": dedup_texts_for_translate}})
        )
    tr_map, _, _ = _build_translation_map(texts_key, texts_src, outs)

    # 3) OVERLAY 입력 구성
    overlay_in = dict(secs["overlay"])
    overlay_in.setdefault("file_path", src_path)
    overlay_in.setdefault("save_ol_img", True)
    ol_items, ol_stats = _compose_overlay_items(texts_src, texts_key, item_polys, tr_map)
    overlay_in["ol"] = ol_items

    render_overlay({"overlay": overlay_in})

    # 4) LOG
    ot = secs.get("oto") or {}
    log_dir = ot.get("log_dir") or str(default_log_dir_for(src_path))
    must_abs(log_dir, "oto.log_dir")
    log_file = ensure_log_file(log_dir)
    append_log(log_file, {
        "stage": "run_oto",
        "src": src_path,
        "counts": {
            "ocr_items": len(meta_ocr.get("items", [])),
            "overlay_items": len(ol_items),
            "matched": ol_stats["matched"],
            "skipped_no_poly": ol_stats["skipped_no_poly"],
            "translate_in": len(dedup_texts_for_translate),
            "translate_out": len(outs),
        },
    })
