"""OCR provider adapters."""

from .paddle import build_paddle_instances, predict_with_paddle

__all__ = ["build_paddle_instances", "predict_with_paddle"]
