"""Utility helpers used by the OCR pipeline.

This module intentionally provides a compact set of helpers so the
`ocr_utils` package can be run independently during refactor. Long-term
these functions should be replaced by calls to the project's canonical
utilities (e.g. `modules.data_utils`, `modules.fileio`, `pillow_utils`).

TODO: The project also needs a font policy for rendering/overlaying
translated text; the font policy/config should be added under
`configs/` and consumed here or by a separate `font_utils` adapter.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import json
import math
import yaml
import re
from PIL import Image


def load_yaml(path: str) -> Dict[str, Any]:
    """Load a YAML file and return a dict. Returns {} when the file missing."""
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp) or {}


def section_or_root(root: Dict[str, Any], section: str) -> Dict[str, Any]:
    """Return `root[section]` if present and a dict, otherwise return root.

    The pipeline accepts either a full YAML where the keys live under
    an `ocr:` section, or a flat dict that is already the `ocr` section.
    """
    if not isinstance(root, dict):
        return {}
    v = root.get(section)
    if isinstance(v, dict):
        return v
    return root


def ensure_dir(path_like: Union[str, Path]) -> Path:
    """Ensure the directory exists and return the Path."""
    p = Path(path_like)
    p.mkdir(parents=True, exist_ok=True)
    return p


def as_list(x) -> List[Any]:
    """Normalize non-list values into a list for config flexibility."""
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def is_number_or_symbol_only(s: str) -> bool:
    """Return True when a string contains no alphabetic characters.

    Used to drop purely numeric or symbolic OCR hits.
    """
    if not s:
        return True
    s2 = str(s).strip()
    if not s2:
        return True
    if any(ch.isalpha() for ch in s2):
        return False
    return True


def strip_specials_keep_alnum_space(s: str) -> str:
    """Strip punctuation but keep alphanumeric and CJK characters and spaces."""
    if not s:
        return ""
    out = re.sub(r"[^0-9A-Za-z\u4E00-\u9FFF\s]", "", s)
    return " ".join(out.split())


def _bbox_from_quad(quad: List[List[float]]) -> Dict[str, float]:
    xs = [float(p[0]) for p in quad]
    ys = [float(p[1]) for p in quad]
    return {"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)}


def _angle_from_quad(quad: List[List[float]]) -> float:
    (x1, y1), (x2, y2) = quad[0], quad[1]
    return math.degrees(math.atan2(y2 - y1, x2 - x1))


def load_image(path: str, convert: Optional[str] = None):
    """Load image via Pillow and return (Image, meta_dict)."""
    p = Path(path)
    img = Image.open(p)
    if convert:
        img = img.convert(convert)
    meta = {"width": img.width, "height": img.height, "format": img.format, "exif_bytes_len": len(img.info.get("exif", b"")) if img.info.get("exif") else None}
    return img, meta


def save_image(img: Image.Image, out_path: Union[str, Path]):
    """Save a Pillow image to disk, creating parent directory if needed."""
    outp = Path(out_path)
    ensure_dir(outp.parent)
    img.save(outp)


def save_meta_json(meta: Dict[str, Any], save_dir: Union[str, Path], file_name: str) -> Path:
    """Write meta JSON to disk and return the Path."""
    d = ensure_dir(save_dir)
    out = d / file_name
    with out.open("w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=2)
    return out
