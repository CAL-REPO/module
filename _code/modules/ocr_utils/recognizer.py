"""OCR recognizer adapters.

This module contains thin adapters that construct and call vendor OCR
implementations. Keep the dependency on `paddleocr` isolated so the
rest of the pipeline can handle provider failures gracefully.

The functions here expect that callers have already normalized input
images (Pillow Image objects) and configuration. The recognizer maps
language codes to Paddle's expected short codes and caches per-language
instances.

Note: this module intentionally avoids importing heavy vendor packages
at import time so test suites without paddle can still import the
package. Any ImportError or runtime TypeError from the vendor library
is caught and logged with a helpful hint.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from dataclasses import dataclass
import logging
import time
import numpy as np

from .models import OCRItemModel

logger = logging.getLogger(__name__)


@dataclass
class PaddleInstance:
    name: str
    engine: Any


def _map_lang_to_paddle(code: str) -> str:
    s = (code or "").strip().lower()
    if s in {"ch", "chi", "zh", "zh_cn", "ch_sim", "chinese"}:
        return "ch"
    if s in {"en", "eng", "english"}:
        return "en"
    if s in {"ko", "kor", "korean"}:
        # Use Chinese model as a fallback for languages without a
        # dedicated Paddle model in some installations.
        return "ch"
    return "en"


def build_paddle_instances(langs, device=None, use_angle_cls=True, existing=None):
    """Create or reuse PaddleOCR instances for the requested languages.

    Returns a dict mapping short-lang -> PaddleOCR instance. `existing`
    may be provided to reuse already-constructed instances.
    """
    insts = dict(existing or {})
    try:
        from paddleocr import PaddleOCR
    except Exception as e:  # pragma: no cover - environment specific
        logger.exception("Could not import paddleocr: %s", e)
        raise

    for lang in set(_map_lang_to_paddle(l) for l in langs):
        if lang not in insts:
            kwargs = {}
            if device is not None:
                kwargs["device"] = device
            try:
                insts[lang] = PaddleOCR(lang=lang, use_angle_cls=use_angle_cls, **kwargs)
            except TypeError as te:
                logger.exception(
                    "Failed to initialize PaddleOCR for lang=%s. This often means the installed\n"
                    "paddle/paddleocr versions are incompatible. Consider pinning matching versions.\n"
                    "Original error: %s",
                    lang,
                    te,
                )
            except Exception as e:
                logger.exception("Failed to create PaddleOCR instance: %s", e)
    return insts


def predict_with_paddle(img, langs, insts: Dict[str, Any], min_conf: float = 0.5) -> Tuple[List[OCRItemModel], Dict[str, int]]:
    """Run OCR with each Paddle instance and return normalized OCRItemModel list.

    Returns (items, timings_ms) where items is a list of OCRItemModel and
    timings_ms maps language -> milliseconds spent.
    """
    arr = np.array(img)
    if arr.ndim == 3 and arr.shape[2] == 3:
        arr_bgr = arr[:, :, ::-1]
    else:
        arr_bgr = arr

    results: List[OCRItemModel] = []
    timings: Dict[str, int] = {}
    order = 0
    mapped = [m for m in (_map_lang_to_paddle(x) for x in langs) if m]
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
                results.append(OCRItemModel(text=str(t), conf=conf, quad=quad, bbox=bbox, angle_deg=0.0, lang=lang, order=order))
                order += 1

    return results, timings
