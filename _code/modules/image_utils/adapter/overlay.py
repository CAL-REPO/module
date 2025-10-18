"""Adapter alias exposing the overlayer entry point."""

from ..entry_point.overlayer import ImageOverlayer


class ImageOverlay(ImageOverlayer):
    """Backwards compatible adapter retaining the previous class name."""

    __slots__ = ()
