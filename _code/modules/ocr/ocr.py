# -*- coding: utf-8 -*-
"""
modules.ocr — OCR runner (dataclass defaults + provider selector)
=================================================================

구성 (기능별 정리):
1) Dataclasses & Types: 기본값, 결과 스키마
2) Config Load & Normalize: YAML/입력에서 설정/이미지 경로 정규화
3) IO & Save Helpers: 이미지 로드, OCR 메타 저장
4) Providers: 각 OCR 엔진별 실행 (paddle)
5) Runner & Public API: run_ocr / CLI

주의
- 내부 로직은 리팩토링하지 않고 오타/키 이름만 정리
- meta 저장 키: ocr_meta_dir / ocr_meta_name
- meta 파일에는 텍스트 및 위치(poly/bbox/angle) 정보 포함
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Union, Iterable
from pathlib import Path
from functools import lru_cache
import os

import json
import math
import time
import numpy as np

# local modules
from modules.datautil import as_list, is_number_or_symbol_only, strip_specials_keep_alnum_space
from modules.yamlutil import section_or_root, load_yaml
from modules.fileio import ensure_dir, parent_dir_of
from pillow.pillow import load_image, save_image  # 이미지 입출력 재사용

# ---------------------------------------------------------------------------
# 1) Dataclasses & Types
# ---------------------------------------------------------------------------
@dataclass
class OcrFileDefaults:
    # 입력 이미지
    file_path: str = ""                     # 이미지 파일 경로
    # 저장(사본)
    save_img: bool = False
    save_dir: str = ""                      # 비었으면 file_path 디렉터리
    save_suffix: str = "_copy"
    # 메타 저장
    save_ocr_meta: bool = False             # OCR 메타 JSON 저장 여부
    ocr_meta_dir: str = ""                 # 비었으면 file_path 디렉터리
    ocr_meta_name: str = "meta_ocr.json"   # 메타 파일명


@dataclass
class OcrProviderDefaults:
    provider: str = "paddle"               # 추후 확장: easyocr, tesseract 등
    langs: List[str] = field(default_factory=lambda: ["ch_sim", "en"])
    min_conf: float = 0.5                  # 최소 신뢰도 필터
    paddle_device: Optional[str] = "gpu"     # "cpu" | "gpu" | "gpu:0" (3.5 기준 device 사용)
    paddle_use_angle_cls: bool = True
    paddle_instance: Dict[str, Any] = field(default_factory=dict)  # lang→PaddleOCR 인스턴스
    # provider 별로 필요한 값이 생기면 여기에 필드 추가 (예: use_angle_cls 등)

@dataclass
class OcrPreprocessDefaults:
    resized: bool = False                  # 향후 리사이즈/전처리 플래그 등 확장
    max_width: Optional[int] = None

@dataclass
class OcrDefaults:
    file: OcrFileDefaults = field(default_factory=OcrFileDefaults)
    provider: OcrProviderDefaults = field(default_factory=OcrProviderDefaults)
    preprocess: OcrPreprocessDefaults = field(default_factory=OcrPreprocessDefaults)
    debug: bool = False

@dataclass
class OCRItem:
    text: str
    conf: float
    quad: List[List[float]]                # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    bbox: Dict[str, float]                 # {x0,y0,x1,y1}
    angle_deg: float                       # 상단 변 기준 각도(시계 방향 +)
    lang: str                              # provider 언어 태그 (예: "ch", "en" 등 매핑 결과)
    order: int                             # 감지 순서

# ---------------------------------------------------------------------------
# 2) Config Load & Normalize
# ---------------------------------------------------------------------------

def _ocr_section(cfg_like: Union[str, Path, Dict[str, Any], None]) -> Dict[str, Any]:
    """
    YAML 경로나 dict 를 받아 ocr 섹션만 추출.
    - 섹션이 없으면 루트 사용
    - None이면 {}
    """
    if cfg_like is None:
        return {}
    if isinstance(cfg_like, (str, Path)):
        root = load_yaml(str(cfg_like))
        return section_or_root(root, "ocr")
    if isinstance(cfg_like, dict):
        return section_or_root(cfg_like, "ocr")
    return {}


def _defaults_from_cfg(ocr: Dict[str, Any]) -> OcrDefaults:
    d = OcrDefaults()

    # ---------- file ----------
    f_raw = ocr.get("file") or ocr
    # file 섹션이 문자열(=경로)로 올 수도 있음 → dict로 정규화
    if isinstance(f_raw, str):
        f = {"file_path": f_raw}
    elif isinstance(f_raw, dict):
        f = f_raw
    else:
        f = {}
    d.file = OcrFileDefaults(
        file_path=str(f.get("file_path", d.file.file_path) or ""),
        save_img=bool(f.get("save_img", d.file.save_img)),
        save_dir=str(f.get("save_dir", d.file.save_dir) or ""),
        save_suffix=str(f.get("save_suffix", d.file.save_suffix) or "_copy"),
        save_ocr_meta=bool(f.get("save_ocr_meta", d.file.save_ocr_meta)),
        ocr_meta_dir=str(f.get("ocr_meta_dir", d.file.ocr_meta_dir) or ""),
        ocr_meta_name=str(f.get("ocr_meta_name", d.file.ocr_meta_name) or "meta_ocr.json"),
    )

    # ---------- provider ----------
    prov_raw = ocr.get("provider", {}) or {}
    # provider가 문자열/리스트/딕셔너리 아무거나 올 수 있도록 정규화
    if isinstance(prov_raw, str):
        prov = {"provider": prov_raw}
    elif isinstance(prov_raw, (list, tuple)):
        prov = {"langs": list(prov_raw)}
    elif isinstance(prov_raw, dict):
        prov = prov_raw
    else:
        prov = {}
    d.provider.provider = (prov.get("provider") or d.provider.provider).strip().lower()
    # 단일 문자열도 안전히 리스트로
    d.provider.langs = as_list(prov.get("langs") or d.provider.langs)
    d.provider.min_conf = float(prov.get("min_conf", d.provider.min_conf))
    # 신규 필드
    d.provider.paddle_device = prov.get("paddle_device", d.provider.paddle_device)
    d.provider.paddle_use_angle_cls = bool(prov.get("paddle_use_angle_cls", d.provider.paddle_use_angle_cls))
    if "paddle_instance" in prov and isinstance(prov["paddle_instance"], dict):
        d.provider.paddle_instance = prov["paddle_instance"]


    # ---------- preprocess ----------
    pr_raw = ocr.get("preprocess") or {}
    pr = pr_raw if isinstance(pr_raw, dict) else {}
    d.preprocess = OcrPreprocessDefaults(
         resized=bool(pr.get("resized", d.preprocess.resized)),
         # (선택) max_width를 지원한다면 여기에 추가
         # max_width=int(pr["max_width"]) if str(pr.get("max_width","")).strip() else None,
     )

    d.debug = bool(ocr.get("debug", d.debug))   
    return d

def normalize_ocr_cfg(cfg_like: Union[str, Path, Dict[str, Any], None]) -> OcrDefaults:
    """
    외부 입력을 프로젝트 내부에서 쓰기 좋게 dataclass 로 정규화
    """
    sec = _ocr_section(cfg_like)
    return _defaults_from_cfg(sec)

# ---------------------------------------------------------------------------
# 3) IO & Save Helpers
# ---------------------------------------------------------------------------

def _bbox_from_quad(quad: List[List[float]]) -> Dict[str, float]:
    xs = [float(p[0]) for p in quad]
    ys = [float(p[1]) for p in quad]
    return {"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)}


def _angle_from_quad(quad: List[List[float]]) -> float:
    # 상단변: p0→p1 가정
    (x1, y1), (x2, y2) = quad[0], quad[1]
    return math.degrees(math.atan2(y2 - y1, x2 - x1))


def _ensure_save_dir_for_file(path_like: Union[str, Path]) -> Path:
    p = Path(path_like)
    ensure_dir(p)
    return p


def _save_ocr_meta_json(
    meta: Dict[str, Any],
    *,
    save_dir: Union[str, Path],
    file_name: str,
) -> Path:
    save_dir_p = _ensure_save_dir_for_file(save_dir)
    out_path = save_dir_p / file_name
    with out_path.open("w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=2)
    return out_path


# ---------------------------------------------------------------------------
# 4) Providers (KEEP logic; typos only) — PaddleOCR
# ---------------------------------------------------------------------------

def _map_lang_to_paddle(code: str) -> Optional[str]:
    """
    프로젝트 언어코드 → Paddle lang 코드 간단 매핑
    - 입력 예: 'ch_sim','ch','zh','en','ko' ...
    """
    s = (code or "").strip().lower()
    if s in {"ch", "chi", "zh", "zh_cn", "ch_sim", "chinese"}:
        return "ch"
    if s in {"en", "eng", "english"}:
        return "en"
    if s in {"ko", "kor", "korean"}:
        # paddle은 ko 미지원(2024-), 한글은 'ch' 모델이 더 잘 인식되는 경우가 많음
        return "ch"
    # 기본 영문
    return "en"

def _freeze_items(d: Dict[str, Any]) -> Tuple[Tuple[str, Any], ...]:
    return tuple(sorted(d.items()))

@lru_cache(maxsize=64)
def _get_paddle_cached(
    lang: str,
    use_angle_cls: bool,
    device: Optional[str],
    extra_items: Tuple[Tuple[str, Any], ...],
):
    """단일 언어 PaddleOCR 인스턴스 캐시 — PaddleOCR 3.5 호환(device)."""
    from paddleocr import PaddleOCR  # ← 여기서 지연 임포트
    kwargs = dict(extra_items)
    if device is not None:
        kwargs["device"] = device             # "cpu" | "gpu" | "gpu:0"
    return PaddleOCR(lang=lang, use_angle_cls=use_angle_cls, **kwargs)

def build_paddle_instances_from_cfg(
    cfg_like: Union[str, Dict[str, Any]],
    existing_insts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    cfg_like(= {"ocr": {...}} / dict / yaml path) 기반으로 언어셋 인스턴스 생성.
    existing_insts가 주어지면 부족한 언어만 추가 생성하여 merge 후 반환.
    반환: { lang: PaddleOCR(...) }
    """
    cfg = normalize_ocr_cfg(cfg_like)
    langs = cfg.provider.langs or ["en"]
    mapped = [m for m in (_map_lang_to_paddle(x) for x in langs) if m] or ["en"]
    device = cfg.provider.paddle_device
    use_angle_cls = cfg.provider.paddle_use_angle_cls
    extra = {}  # 필요 시 모델경로 등 확장
    frozen = _freeze_items(extra)

    insts: Dict[str, Any] = dict(existing_insts or {})
    for lang in mapped:
        if lang not in insts:
            insts[lang] = _get_paddle_cached(lang, use_angle_cls, device, frozen)
    return insts

def _run_with_paddle(
    img_for_ocr,
    ocr_cfg: OcrDefaults,
    insts: Dict[str, Any],
) -> Tuple[List[OCRItem], Dict[str, int]]:
    """
    - poly → bbox/angle 계산
    - min_conf 필터 적용
    - PaddleOCR.predict 를 이용해 각 언어별로 실행.
    """
    # PIL → np.ndarray (BGR로 변환)
    arr = np.array(img_for_ocr)  # type: ignore
    if arr.ndim == 3 and arr.shape[2] == 3:
        arr_bgr = arr[:, :, ::-1]
    else:
        arr_bgr = arr

    timings_each: Dict[str, int] = {}
    results: List[OCRItem] = []
    order = 0

    # 언어 매핑
    mapped = [m for m in (_map_lang_to_paddle(x) for x in (ocr_cfg.provider.langs or ["en"])) if m]
    if not mapped:
        mapped = ["en"]

    # 언어별 실행
    for lang in mapped:
        t0 = time.time()
        ocr = insts.get(lang)
        if ocr is None:
            # 이 단계에서는 인스턴스가 반드시 있어야 함 (builder에서 미리 채움)
            raise RuntimeError(f"Missing PaddleOCR instance for lang='{lang}'.")
        out = ocr.predict(arr_bgr)  # type: ignore
        ms = int((time.time() - t0) * 1000)
        timings_each[lang] = ms

        # 기대 포맷: list[dict] with keys: rec_boxes, rec_texts, rec_scores
        for item in out:  # type: ignore[assignment]
            boxes = item.get("rec_boxes")
            texts = item.get("rec_texts")
            scores = item.get("rec_scores")

            # numpy.ndarray → list
            if hasattr(boxes, "tolist"):            # type: ignore[attr-defined]
                boxes = boxes.tolist()              # type: ignore

            if not (isinstance(boxes, list) and isinstance(texts, list)):
                continue
            if not isinstance(scores, list):
                scores = [1.0] * len(texts)

            for b, t, s in zip(boxes, texts, scores):
                # rec_boxes: [x_min, y_min, x_max, y_max]
                if not (isinstance(b, (list, tuple)) and len(b) == 4):
                    continue
                x1, y1, x2, y2 = map(float, b)
                quad = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

                try:
                    conf = float(s)
                except Exception:
                    conf = 0.0

                if not t or conf < float(ocr_cfg.provider.min_conf):
                    continue

                bbox = _bbox_from_quad(quad)
                angle = _angle_from_quad(quad)
                results.append(OCRItem(
                    text=str(t), conf=conf, quad=quad, bbox=bbox,
                    angle_deg=angle, lang=str(lang), order=order
                ))
                order += 1

    return results, timings_each

# ---------------------------------------------------------------------------
# 6) Data Selector
# ---------------------------------------------------------------------------
def filter_ocr_items_drop_numeric_symbol_only(items: List[OCRItem]) -> List[OCRItem]:
    """
    OCRItem 중 text가 숫자/기호만으로 이루어진 항목은 제거.
    (예: '100%', '---', '12345' 등은 버리고, 한글/중문/영문 포함되면 유지)
    """
    return [it for it in items if not is_number_or_symbol_only(getattr(it, "text", "") or "")]

def sanitize_ocr_items_strip_specials(items: List[OCRItem]) -> List[OCRItem]:
    """
    각 OCRItem.text에서 특수문자/구두점을 제거.
    제거 후 빈 문자열이면 버림.
    """
    out: List[OCRItem] = []
    for it in items:
        new_text = strip_specials_keep_alnum_space(it.text)
        if not new_text:
            continue
        if new_text == it.text:
            out.append(it)
        else:
            out.append(OCRItem(
                text=new_text, conf=it.conf, quad=it.quad, bbox=it.bbox,
                angle_deg=it.angle_deg, lang=it.lang, order=it.order
            ))
    return out

def _iou_bbox(a: Dict[str, float], b: Dict[str, float]) -> float:
    ix0 = max(a["x0"], b["x0"]); iy0 = max(a["y0"], b["y0"])
    ix1 = min(a["x1"], b["x1"]); iy1 = min(a["y1"], b["y1"])
    iw = max(0.0, ix1 - ix0); ih = max(0.0, iy1 - iy0)
    inter = iw * ih
    area_a = max(0.0, (a["x1"] - a["x0"])) * max(0.0, (a["y1"] - a["y0"]))
    area_b = max(0.0, (b["x1"] - b["x0"])) * max(0.0, (b["y1"] - b["y0"]))
    union = area_a + area_b - inter
    return (inter / union) if union > 0 else 0.0

def dedupe_ocr_items_by_overlap(
    items: List[OCRItem],
    *,
    iou_thresh: float = 0.7,
    prefer_lang_order: List[str] = ["ch", "ko", "en"],
) -> List[OCRItem]:
    """
    박스가 많이 겹치는 항목(같은 위치 다른 언어 인식)을 제거.
    - 정렬 우선순위: conf 내림차순 → 언어 선호도(prefer_lang_order)
    - 이미 채택된 박스와 IoU >= iou_thresh 면 스킵
    """
    def lang_rank(lang: str) -> int:
        return prefer_lang_order.index(lang) if lang in prefer_lang_order else len(prefer_lang_order)

    items_sorted = sorted(items, key=lambda it: (-float(it.conf), lang_rank(it.lang)))
    kept: List[OCRItem] = []
    for it in items_sorted:
        if any(_iou_bbox(it.bbox, k.bbox) >= iou_thresh for k in kept):
            continue
        kept.append(it)
    return kept

# ---------------------------------------------------------------------------
# 6) Runner & Public API
# ---------------------------------------------------------------------------

def run_ocr(cfg_like: Union[str, Path, Dict[str, Any], None]) -> Tuple[List[OCRItem], Dict[str, Any], Optional[Path]]:
    """
    메인 엔트리:
      - cfg_like: YAML 경로 / dict(ocr 섹션 또는 루트) / None
      - 이미지 로드 → provider 선택 → OCR 수행 → (선택) 사본/메타 저장
      - return: (items, meta_dict, saved_meta_path)
    """
    cfg = normalize_ocr_cfg(cfg_like)

    if not cfg.file.file_path:
        raise ValueError("ocr.file_path 가 비어 있습니다.")

    # 이미지 로드
    t0_all = time.time()
    t0 = time.time()
    img, img_meta = load_image(cfg.file.file_path, convert="RGB")
    t_load = int((time.time() - t0) * 1000)

    # (선택) 리사이즈
    mw = cfg.preprocess.max_width
    if mw and img.width > mw:
        ratio = mw / float(img.width)
        new_size = (mw, int(round(img.height * ratio)))
        img = img.resize(new_size)  # Pillow LANCZOS가 기본

    # provider 선택
    provider = (cfg.provider.provider or "paddle").strip().lower()
    if provider != "paddle":
        raise ValueError(f"Unsupported ocr.provider: {provider}")
    # 1) 인스턴스 맵 확보(있으면 재사용, 없으면 생성)
    insts = build_paddle_instances_from_cfg(cfg_like, existing_insts=cfg.provider.paddle_instance)
    # 2) 실행
    t0 = time.time()
    items, timings_each = _run_with_paddle(img, cfg, insts)
    t_ocr = int((time.time() - t0) * 1000)
    # 3) 최신 인스턴스 맵을 cfg에 저장(재사용 목적)
    cfg.provider.paddle_instance = insts

    # 후처리 파이프라인: 특수문자 제거 → 숫자/기호-only 제거 → 겹침 중복 제거
    items_final = items[:]
    items_step1 = sanitize_ocr_items_strip_specials(items)
    items_step2 = filter_ocr_items_drop_numeric_symbol_only(items_step1)
    items_final = dedupe_ocr_items_by_overlap(items_step2, iou_thresh=0.7, prefer_lang_order=["ch","en"])
    counts = {"raw": len(items), "final": len(items_final)}

    # (선택) 이미지 사본 저장
    if cfg.file.save_img:
        srcp = Path(cfg.file.file_path)
        out_dir = Path(cfg.file.save_dir) if cfg.file.save_dir else srcp.parent
        ensure_dir(out_dir)
        out_name = f"{srcp.stem}{cfg.file.save_suffix}{srcp.suffix}"
        out_path = out_dir / out_name
        save_image(img, out_path)

    # 메타 JSON 생성
    total_ms = int((time.time() - t0_all) * 1000)
    meta: Dict[str, Any] = {
        "schema_version": "ocr-overlay-v1",
        "provider": provider,
        "langs": list(cfg.provider.langs),
        "langs_mapped": [l for l in set(_map_lang_to_paddle(x) or "en" for x in cfg.provider.langs)],
        "preprocess": asdict(cfg.preprocess),
        "timings_ms": {
            "load": t_load,
            "preprocess": 0,
            "ocr_each": timings_each,
            "total": total_ms,
        },
        "image": {
            "src_path": str(cfg.file.file_path),
            "width": int(img_meta.get("width", img.width)),
            "height": int(img_meta.get("height", img.height)),
            "mode": img.mode,
            "format": img_meta.get("format"),
            "file_size": Path(cfg.file.file_path).stat().st_size if Path(cfg.file.file_path).exists() else None,
            "exif_bytes_len": img_meta.get("exif_bytes_len", None),
        },
        "counts": counts,
        "items": [
            {
                "id": f"li_{it.order:05d}",
                "text": it.text,
                "conf": float(it.conf),
                "lang": it.lang,
                "angle_deg": float(it.angle_deg),
                "bbox": {k: float(v) for k, v in it.bbox.items()},
                "poly": [[float(p[0]), float(p[1])] for p in it.quad],
                "order": int(it.order),
            }
            for it in items_final
        ],
        "items_raw": [],  # 필요 시 원시 출력 구조를 여기에 추가
    }

    saved_meta_path: Optional[Path] = None
    if cfg.file.save_ocr_meta:
        # 저장 경로 결정(비었으면 원본 이미지 폴더)
        srcp = Path(cfg.file.file_path)
        mdir = Path(cfg.file.ocr_meta_dir) if cfg.file.ocr_meta_dir else srcp.parent
        mname = cfg.file.ocr_meta_name or "meta_ocr.json"
        saved_meta_path = _save_ocr_meta_json(meta, save_dir=mdir, file_name=mname)

    return items_final, meta, saved_meta_path