from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

from .pipeline import run_ocr as _pipeline_run_ocr


class ImageOCRService:
    """Small SRP wrapper around the legacy run_ocr function.

    Responsibilities:
    - Accept a config path or dict describing the `ocr` section.
    - Expose a `run` method that returns the same tuple as `run_ocr`.
    """

    def __init__(self, cfg_like: Union[str, Path, Dict[str, Any], None]):
        self.cfg_like = cfg_like

    def run(self) -> Tuple[List[Any], Dict[str, Any], Optional[Path]]:
        """Execute OCR and return (items, meta, saved_meta_path).

        The cfg_like may be a path string, a Path object, a dict matching the
        `ocr` section, or None for defaults. We pass this directly to the
        pipeline which will normalize it.
        """
        return _pipeline_run_ocr(self.cfg_like)


def run_ocr(cfg_like: Union[str, Path, Dict[str, Any], None]):
    """Convenience wrapper for pipeline.run_ocr accepting Path as well."""
    return _pipeline_run_ocr(cfg_like)
