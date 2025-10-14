# -*- coding: utf-8 -*-
"""pillow_utils — SRP-friendly image processing toolkit with 3 entrypoints.

Three main entrypoints:
1. ImageLoader - Load/copy/resize images with metadata
2. ImageOCR (in ocr_utils) - Run OCR with resize tracking
3. ImageOverlay - Overlay text/graphics from OCR or manual input
"""

from .core.policy import (
    ImageSourcePolicy,
    ImagePolicy,
    ImageMetaPolicy,
    ImageProcessorPolicy,
    ImageLoaderPolicy,
    ImageOverlayPolicy,
    OverlayTextPolicy,
)
from .services.io import ImageReader, ImageWriter
from .services.processor import ImageProcessor
from .services.renderer import OverlayTextRenderer
from .adapter.loader import ImageLoader
from .adapter.image_overlay import ImageOverlay

# Re-export FontPolicy from font_utils for convenience
from font_utils import FontPolicy

__all__ = [
    # Policy models
    "ImageSourcePolicy",
    "ImagePolicy",
    "ImageMetaPolicy",
    "ImageProcessorPolicy",
    "ImageLoaderPolicy",
    "ImageOverlayPolicy",
    "OverlayTextPolicy",
    "FontPolicy",
    # I/O
    "ImageReader",
    "ImageWriter",
    # Processing
    "ImageProcessor",
    # Rendering (pure functional)
    "OverlayTextRenderer",
    # Entrypoints
    "ImageLoader",
    "ImageOverlay",
]

"""Lightweight utilities for loading, copying and resizing a single image.

This subpackage provides a simple API for loading an image from disk and
optionally copying it to a target directory and/or resizing it.  It can
persist metadata about the operation.  It does not depend on any
crawling infrastructure and is designed to be used as a standalone
component after an image has been downloaded.

Exports:
    ImageLoaderPolicy: Pydantic model describing how to load/copy/resize
        an image and control metadata output.
    ImageLoader: runner class that performs the load/copy/resize and writes
        metadata.  Uses :mod:`fso_utils` to build safe file paths and
        :mod:`log_utils` to emit logs.
"""



