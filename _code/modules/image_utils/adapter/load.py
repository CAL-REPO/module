"""Adapter aliases for the image loading entry point."""

from ..entry_point.loader import ImageLoader


class ImageLoad(ImageLoader):
    """Backwards compatible adapter returning the renamed ImageLoader."""

    __slots__ = ()
