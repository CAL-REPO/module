"""Adapter alias exposing the text recognizer entry point."""

from ..entry_point.text_recognizer import ImageTextRecognizer


class ImageTextRecognize(ImageTextRecognizer):
    """Backwards compatible adapter that inherits the ImageTextRecognizer."""

    __slots__ = ()
