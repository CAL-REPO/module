"""ocr_utils package — thin, class-based wrappers for the legacy OCR module.

This package provides a minimal class-based API while delegating the heavy
lifting to the existing implementation in `modules.ocr.ocr`. The goal is to
introduce a stable, testable surface (`ImageOCRService`, `run_ocr`) while the
internal implementation can be refactored incrementally.
"""
from .service import ImageOCRService, run_ocr

__all__ = ["ImageOCRService", "run_ocr"]
