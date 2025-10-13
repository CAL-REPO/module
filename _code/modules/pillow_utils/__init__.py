# -*- coding: utf-8 -*-
"""pillow_refactor — SRP-friendly image toolkit."""

from .models import ImageMeta, ImagePipelineResult
from .policy import (
    ImageSourcePolicy,
    ImageTargetPolicy,
    ImageMetaPolicy,
    ImageProcessingPolicy,
    ImagePipelinePolicy,
    OverlayFontPolicy,
    OverlayTextPolicy,
    OverlayPolicy,
)
from .io import ImageReader, ImageWriter
from .processor import ImageProcessor
from .pipeline import ImagePipeline
from .overlay import OverlayRenderer
from .image_loader import ImageLoaderPolicy, ImageLoader

__all__ = [
    "ImageMeta",
    "ImagePipelineResult",
    "ImageSourcePolicy",
    "ImageTargetPolicy",
    "ImageMetaPolicy",
    "ImageProcessingPolicy",
    "ImagePipelinePolicy",
    "OverlayFontPolicy",
    "OverlayTextPolicy",
    "OverlayPolicy",
    "ImageReader",
    "ImageWriter",
    "ImageProcessor",
    "ImagePipeline",
    "OverlayRenderer",
    "ImageLoaderPolicy",
    "ImageLoader"
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



