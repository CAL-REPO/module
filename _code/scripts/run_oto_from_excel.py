# -*- coding: utf-8 -*-
"""
Excel 기반 OTO 배치 실행기 — run_xloto

프로세스:
  1) paths.local.yaml 로드 → 모든 경로 변수 확정
  2) configs_oto(oto.yaml) 로드/치환 → 베이스 cfg_like 확보
  3) Excel(all_product_xl_file_path) 읽기 → (Download==True) & (Translation blank/False) 행 필터
  4) 각 CAS No에 대해:
     - src  : output_data_images_dir/<CAS>
     - outT : public_img_dir/<CAS>/translated     (overlay 결과 저장)
     - outR : public_img_dir/<CAS>/removed
     - outF : public_img_dir/<CAS>/final
     - src 내 이미지 파일들 순회 → 이미지별 cfg_like 생성 → run_oto(cfg_like)
  5) Excel 저장

주의:
  - run_oto는 절대경로만 받습니다. (이 스크립트에서 치환/절대화 완료 후 전달)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List
from datetime import date

# --- 단순 import --------------------------------------------------------------
from modules.yamlutil import load_yaml, normalize_with_placeholders
from modules.paths import P, _PathsProxy
from modules.fileio import list_image_files, ensure_dir, must_abs
from modules.excel import xw_load_excel, eligible_rows, xw_set_cell_value
from modules.datautil import is_blank
from scripts.ocr_translate_overlay import run_oto

__all__ = ["run_xloto"]

# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------
def _paths_ctx(paths_yaml: str | Path | None) -> _PathsProxy:
    """주어진 paths.yaml 로 읽는 컨텍스트(없으면 ENV CASHOP_PATHS 사용)."""
    return _PathsProxy(paths_yaml) if paths_yaml else P

def _load_and_resolve_yaml(yaml_path: str | Path, vars_map: Dict[str, Any]) -> Dict[str, Any]:
    """YAML 로드 → ${}/{} 치환 → *_dir 절대경로화."""
    raw = load_yaml(yaml_path) or {}
    return normalize_with_placeholders(
        raw, vars_map=vars_map, root_key="root", dir_suffix="_dir", pass_count=2
    )

def _build_overlay_dirs(paths_cfg: Dict[str, Any], cas: str) -> Dict[str, Path]:
    """
    public_img_dir/<CAS>/<translated|removed|final> 폴더 생성
    (dirname 키들은 '폴더 이름'이므로 경로가 아님)
    """
    base_public_cas = ensure_dir(Path(paths_cfg["public_img_dir"]).resolve() / cas)
    d_tr = ensure_dir(base_public_cas / paths_cfg["public_img_tr_dirname"])
    d_rm = ensure_dir(base_public_cas / paths_cfg["public_img_rm_dirname"])
    d_fi = ensure_dir(base_public_cas / paths_cfg["public_img_final_dirname"])
    return {"base": base_public_cas, "translated": d_tr, "removed": d_rm, "final": d_fi}

def _build_cfg_for_image(
    base_cfg: Dict[str, Any],
    *,
    img_path: Path,
    log_dir: Path,
    ov_save_dir: Path,
    db_dir: Path,
) -> Dict[str, Any]:
    """
    한 장의 이미지에 사용할 통합 cfg_like 생성.
      - oto.file_path: 이미지 절대경로
      - oto.log_dir  : output_xloto_logs_dir
      - overlay.ol_save_dir: public_img_dir/<CAS>/translated
      - translate.db_dir: db_dir (비었을 때만 run_oto에서 부모폴더로 보정하므로 우선 지정)
    """
    cfg = dict(base_cfg)  # shallow copy
    oto = dict(cfg.get("oto") or {})
    overlay = dict(cfg.get("overlay") or {})
    tr = dict(cfg.get("translate") or {})

    oto["file_path"] = str(img_path.resolve())
    oto["log_dir"] = str(log_dir.resolve())

    # 오버레이 저장 디렉터리 (CAS/translated)
    overlay["ol_save_dir"] = str(ov_save_dir.resolve())

    # 번역 캐시 DB 디렉터리 (절대경로)
    if is_blank(tr.get("db_dir")):
        tr["db_dir"] = str(db_dir.resolve())
    # tr_dir은 비워두면 run_oto가 이미지 부모 폴더로 보정 (정책 유지)

    cfg["oto"] = oto
    cfg["overlay"] = overlay
    cfg["translate"] = tr
    return cfg


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

# 필수 '경로' 키 검증 (dirname 키 제외)
required_path_keys = [
    "all_product_xl_file_path",
    "output_data_images_dir",
    "public_img_dir",
    "output_xloto_logs_dir",
    "db_dir",
]

# 폴더 이름 키 검증 (경로 아님)
dirname_keys = [
    "public_img_tr_dirname",
    "public_img_rm_dirname",
    "public_img_final_dirname",
]

def run_xloto(
    *,
    paths_yaml: str | Path | None = None,   # 생략 시 ENV CASHOP_PATHS 사용
    oto_yaml: str | Path | None = None,     # 생략 시 paths.configs_oto 사용
    cas_col: str = "CAS No",
    download_col: str = "download",
    translation_col: str = "translation",
) -> Dict[str, Any]:
    """
    Excel 기반 일괄 OTO 파이프라인 실행.
    - Paddle 인스턴스는 최초 1회만 생성 → 이후 모든 run_oto 호출에 주입(생성 없음)
    - translated 폴더에 결과와 동일 파일명이 있으면 해당 이미지는 스킵

    Returns:
        {
          "excel": "<엑셀경로>",
          "num_rows": <엑셀 총 행수>,
          "num_targets": <필터 후 대상 행수>,
          "processed_cas": [<CAS 리스트>],
          "num_cas": <처리 CAS 수>,
        }
    """
    # 0) paths 컨텍스트 / 변수 준비
    PT = _paths_ctx(paths_yaml)
    paths_cfg = PT.cfg()  # dict (이미 normalize_with_placeholders 적용됨)

    for k in required_path_keys:
        if k not in paths_cfg:
            raise KeyError(f"paths.local.yaml에 '{k}' 키가 없습니다.")
        must_abs(paths_cfg[k], k)

    for k in dirname_keys:
        if is_blank(paths_cfg.get(k)):
            raise KeyError(f"paths.local.yaml의 '{k}'(폴더 이름)이 비어 있습니다.")

    # 1) oto.yaml 베이스 로드
    oto_yaml_path = Path(oto_yaml or paths_cfg.get("configs_oto") or "").resolve()
    if not oto_yaml_path.exists():
        raise FileNotFoundError("configs_oto 경로가 비어있거나 파일이 없습니다.")
    base_cfg = _load_and_resolve_yaml(str(oto_yaml_path), paths_cfg)
    
    # 2) Excel 로드
    xl_path = Path(paths_cfg["all_product_xl_file_path"]).resolve()
    must_abs(xl_path, "Excel 파일 경로")
    xl_sheet = paths_cfg.get("all_product_xl_file_sheet")
    df = xw_load_excel(xl_path, xl_sheet, create_if_missing=True, visible=True)

    # 3) 대상 행 필터: Download is not blank AND Translation is blank/false
    spec = {
        "include": [
            {"col": download_col, "op": "not_blank"},
            {"col": translation_col, "op": "blank_or_false"},
        ]
    }
    targets = eligible_rows(df, spec=spec)

    trow = ((targets.index).astype(int) + 1).tolist()
    tcol = targets.columns.get_loc(translation_col) + 2

    processed: List[str] = []
    # 4) CAS 단위 반복
    for _, row in targets.iterrows():
        cas = str(row.get(cas_col, "")).strip()
        if not cas:
            continue

        print(f'{cas}' " 작업 시작")
        # 소스 폴더: output_data_images_dir/<CAS>
        src_dir = Path(paths_cfg["output_data_images_dir"]).resolve() / cas

        # 결과 폴더: public_img_dir/<CAS>/{translated,removed,final}
        ov_dirs = _build_overlay_dirs(paths_cfg, cas)
        out_tr_dir = ov_dirs["translated"]  # overlay 저장 목적지

        # 이미지 목록
        imgs = list_image_files(src_dir, recursive=True)

        if not imgs:
            continue

        for img in imgs:
            # Skip if already translated image exists with same filename
            translated_path = out_tr_dir / img.name
            if translated_path.exists():
                continue
            must_abs(img, "입력 이미지 경로")
            cfg_one = _build_cfg_for_image(
                base_cfg,
                img_path=img,
                log_dir=Path(paths_cfg["output_xloto_logs_dir"]),
                ov_save_dir=out_tr_dir,                 # CAS/translated
                db_dir=Path(paths_cfg["db_dir"]),
            )
            run_oto(cfg_one)
        
        processed.append(cas)
        print(f'{cas}' " 작업 완료")
    # 5) 완료 CAS → Translation에 오늘 날짜 기록 & 저장
    if processed:
        for r in map(int, trow):

            xw_set_cell_value(path=xl_path, sheet=xl_sheet,
                            row=r, col=tcol, value=date.today(), 
                            number_format="yyyy-mm-dd", save=True)

    return {
        "excel": str(xl_path),
        "processed_cas": processed,
        "num_cas": len(processed),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _cli() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Excel-driven xloto batch runner")
    p.add_argument("--paths-yaml", default=None, help="configs/paths.local.yaml (생략 시 ENV CASHOP_PATHS 사용)")
    p.add_argument("--oto-yaml",   default=None, help="paths.configs_oto를 기본값으로 사용")
    p.add_argument("--cas-col", default="CAS No")
    p.add_argument("--download-col", default="Download")
    p.add_argument("--translation-col", default="Translation")
    args = p.parse_args()

    res = run_xloto(
        paths_yaml=args.paths_yaml,
        oto_yaml=args.oto_yaml,
        cas_col=args.cas_col,
        download_col=args.download_col,
        translation_col=args.translation_col,
    )
    print(f"Excel: {res['excel']} | Processed CAS: {res['processed_cas']} ({res['num_cas']})")
    return 0

if __name__ == "__main__":
    raise SystemExit(_cli())
