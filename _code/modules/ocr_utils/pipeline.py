"""Main orchestration for OCR runs.

The pipeline exposes a single function `run_ocr(cfg_like)` which accepts
either a path to YAML, a dict representing the `ocr` section, or None
to use defaults. It returns (items_final, meta_dict, saved_meta_path).

High level steps:
- normalize config -> pydantic OcrConfig
- load image and optionally resize
- construct provider instances
- run recognition -> normalize and dedupe results
- optionally save artifacts (image copy and meta JSON)

TODO: wire a font policy into the saved meta so downstream overlay
renderers can pick appropriate fonts and fallback chains.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import time

from .models import OcrConfig, OCRItemModel
from .utils import (
    load_yaml, section_or_root, as_list, load_image, save_image, save_meta_json, _bbox_from_quad, _angle_from_quad, strip_specials_keep_alnum_space, is_number_or_symbol_only
)
from .recognizer import build_paddle_instances, predict_with_paddle


def _defaults_from_cfg_like(cfg_like: Union[str, Path, dict, None]) -> OcrConfig:
    if cfg_like is None:
        return OcrConfig(**{})
    if isinstance(cfg_like, (str, Path)):
        root = load_yaml(str(cfg_like))
        sec = section_or_root(root, "ocr")
        return OcrConfig(**{"file": sec.get("file", {}), "provider": sec.get("provider", {}), "preprocess": sec.get("preprocess", {}), "debug": sec.get("debug", False)})
    if isinstance(cfg_like, dict):
        sec = section_or_root(cfg_like, "ocr")
        return OcrConfig(**{"file": sec.get("file", {}), "provider": sec.get("provider", {}), "preprocess": sec.get("preprocess", {}), "debug": sec.get("debug", False)})
    raise TypeError("cfg_like must be str|Path|dict|None")


def _postprocess_items(raw_items: List[OCRItemModel], prefer_lang_order: List[str] = ["ch", "en"]) -> List[OCRItemModel]:
    # sanitize text
    out = []
    for it in raw_items:
        new_text = strip_specials_keep_alnum_space(it.text)
        if not new_text:
            continue
        it.text = new_text
        if is_number_or_symbol_only(new_text):
            continue
        out.append(it)
    # dedupe by bbox overlap simple heuristic
    kept: List[OCRItemModel] = []
    def lang_rank(lang: str) -> int:
        return prefer_lang_order.index(lang) if lang in prefer_lang_order else len(prefer_lang_order)
    items_sorted = sorted(out, key=lambda it: (-float(it.conf), lang_rank(it.lang)))
    for it in items_sorted:
        if any(_iou_bbox(it.bbox, k.bbox) >= 0.7 for k in kept):
            continue
        kept.append(it)
    return kept


def _iou_bbox(a: Dict[str, float], b: Dict[str, float]) -> float:
    ix0 = max(a["x0"], b["x0"]) ; iy0 = max(a["y0"], b["y0"])
    ix1 = min(a["x1"], b["x1"]) ; iy1 = min(a["y1"], b["y1"])
    iw = max(0.0, ix1 - ix0); ih = max(0.0, iy1 - iy0)
    inter = iw * ih
    area_a = max(0.0, (a["x1"] - a["x0"])) * max(0.0, (a["y1"] - a["y0"]))
    area_b = max(0.0, (b["x1"] - b["x0"])) * max(0.0, (b["y1"] - b["y0"]))
    union = area_a + area_b - inter
    return (inter / union) if union > 0 else 0.0


def run_ocr(cfg_like: Union[str, Path, dict, None]) -> Tuple[List[OCRItemModel], Dict[str, Any], Optional[Path]]:
    cfg = _defaults_from_cfg_like(cfg_like)
    if not cfg.file.file_path:
        raise ValueError("ocr.file.file_path is empty")

    t0_all = time.time()
    t0 = time.time()
    img, img_meta = load_image(cfg.file.file_path, convert="RGB")
    t_load = int((time.time() - t0) * 1000)

    # resize if requested
    mw = cfg.preprocess.max_width
    if mw and img.width > mw:
        ratio = mw / float(img.width)
        img = img.resize((mw, int(round(img.height * ratio))))

    # build recognizer instances
    insts = build_paddle_instances(cfg.provider.langs, device=cfg.provider.paddle_device, use_angle_cls=cfg.provider.paddle_use_angle_cls, existing=cfg.provider.paddle_instance)

    t0 = time.time()
    raw_items, timings_each = predict_with_paddle(img, cfg.provider.langs, insts, min_conf=cfg.provider.min_conf)
    t_ocr = int((time.time() - t0) * 1000)

    cfg.provider.paddle_instance = insts

    items_final = _postprocess_items(raw_items)

    counts = {"raw": len(raw_items), "final": len(items_final)}

    # optional save image copy
    if cfg.file.save_img:
        srcp = Path(cfg.file.file_path)
        out_dir = Path(cfg.file.save_dir) if cfg.file.save_dir else srcp.parent
        out_name = f"{srcp.stem}{cfg.file.save_suffix}{srcp.suffix}"
        save_image(img, out_dir / out_name)

    total_ms = int((time.time() - t0_all) * 1000)
    meta = {
        "schema_version": "ocr-overlay-v1",
        "provider": cfg.provider.provider,
        "langs": cfg.provider.langs,
        "preprocess": cfg.preprocess.dict(),
        "timings_ms": {"load": t_load, "ocr_each": timings_each, "total": total_ms},
        "image": {"src_path": str(cfg.file.file_path), "width": img_meta.get("width"), "height": img_meta.get("height"), "mode": img.mode, "format": img_meta.get("format")},
        "counts": counts,
        "items": [it.dict() for it in items_final],
        "items_raw": [],
    }

    saved_meta_path = None
    if cfg.file.save_ocr_meta:
        srcp = Path(cfg.file.file_path)
        mdir = Path(cfg.file.ocr_meta_dir) if cfg.file.ocr_meta_dir else srcp.parent
        mname = cfg.file.ocr_meta_name or "meta_ocr.json"
        saved_meta_path = save_meta_json(meta, mdir, mname)

    return items_final, meta, saved_meta_path
