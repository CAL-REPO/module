"""PaddleOCR provider adapter."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from functools import lru_cache
import logging
import time
import numpy as np

from ..policy import OCRItem
from ..lang_mapper import map_lang_to_paddle

logger = logging.getLogger(__name__)


def _freeze_items(d: Dict[str, Any]) -> Tuple[Tuple[str, Any], ...]:
    """Convert dict to hashable tuple for lru_cache."""
    return tuple(sorted(d.items()))


@lru_cache(maxsize=64)
def _get_paddle_cached(
    lang: str,
    extra_items: Tuple[Tuple[str, Any], ...],
):
    """Create cached PaddleOCR instance for specific language and settings.
    
    PaddleOCR 3.0.3 + paddle 3.0.0: Minimal initialization.
    The package has internal issues with parameter passing - only lang works.
    """
    from paddleocr import PaddleOCR
    
    # PaddleOCR 3.0.3 has a bug where passing use_angle_cls or device causes
    # "PaddlePredictorOption.__init__() takes 1 positional argument but 2 were given"
    # Use lang only for stable initialization
    return PaddleOCR(lang=lang)


def build_paddle_instances(langs, device=None, use_angle_cls=True, existing=None):
    """Create or reuse PaddleOCR instances for requested languages.
    
    Note: device and use_angle_cls parameters are ignored due to paddleocr 3.0.3 bug.
    Uses lru_cache to avoid re-initialization issues.
    """
    insts = dict(existing or {})
    
    # device and use_angle_cls are ignored - paddleocr 3.0.3 has parameter passing bug
    extra = {}  # For future extension (model paths, etc.)
    frozen = _freeze_items(extra)
    
    for lang in set(map_lang_to_paddle(l) for l in langs):
        if lang not in insts:
            try:
                insts[lang] = _get_paddle_cached(lang, frozen)
                logger.info(f"✅ Initialized PaddleOCR for lang={lang}")
            except Exception as e:
                logger.exception(f"❌ Failed to initialize PaddleOCR for lang={lang}: {e}")
    
    return insts

def predict_with_paddle(img, langs, insts: Dict[str, Any], min_conf: float = 0.5) -> Tuple[List[OCRItem], Dict[str, int]]:
    """Run OCR with Paddle instances and return normalized OCRItem list."""
    arr = np.array(img)
    if arr.ndim == 3 and arr.shape[2] == 3:
        arr_bgr = arr[:, :, ::-1]
    else:
        arr_bgr = arr

    results: List[OCRItem] = []
    timings: Dict[str, int] = {}
    order = 0
    mapped = [m for m in (map_lang_to_paddle(x) for x in langs) if m]
    if not mapped:
        mapped = ["en"]

    for lang in mapped:
        t0 = time.time()
        ocr = insts.get(lang)
        if ocr is None:
            continue
        out = ocr.predict(arr_bgr)
        timings[lang] = int((time.time() - t0) * 1000)

        for item in out:
            boxes = item.get("rec_boxes")
            texts = item.get("rec_texts")
            scores = item.get("rec_scores")
            if hasattr(boxes, "tolist"):
                boxes = boxes.tolist()
            if not (isinstance(boxes, list) and isinstance(texts, list)):
                continue
            if not isinstance(scores, list):
                scores = [1.0] * len(texts)
            for b, t, s in zip(boxes, texts, scores):
                if not (isinstance(b, (list, tuple)) and len(b) == 4):
                    continue
                x1, y1, x2, y2 = map(float, b)
                quad = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                try:
                    conf = float(s)
                except Exception:
                    conf = 0.0
                if not t or conf < float(min_conf):
                    continue
                bbox = {"x0": min(x1, x2), "y0": min(y1, y2), "x1": max(x1, x2), "y1": max(y1, y2)}
                results.append(OCRItem(text=str(t), conf=conf, quad=quad, bbox=bbox, angle_deg=0.0, lang=lang, order=order))
                order += 1

    return results, timings
