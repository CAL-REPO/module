# -*- coding: utf-8 -*-
"""image_utils — SRP-friendly image processing toolkit with 3 entrypoints.

Three main entrypoints:
1. ImageLoader - Load/copy/resize images with metadata
2. ImageTextRecognizer - Run OCR with resize tracking
3. ImageOverlayer - Overlay text/graphics from OCR or manual input
"""

from .core.policy import (
    # Common policies
    ImageSourcePolicy,
    ImageSavePolicy,
    ImageMetaPolicy,
    
    # ImageLoader
    ImageProcessPolicy,
    ImageLoaderPolicy,
    
    # ImageTextRecognizer
    OCRProviderPolicy,
    OCRPreprocessPolicy,
    OCRPostprocessPolicy,
    ImageOCRPolicy,
    
    # ImageOverlayer
    OverlayTextPolicy,
    ImageOverlayPolicy,
    
    # Backward compatibility (deprecated)
    ImagePolicy,
    ImageProcessorPolicy,
)

from .core.models import OCRItem

from .services.io import ImageReader, ImageWriter
from .services.processor import ImageProcessor
from .services.renderer import OverlayTextRenderer

# Entry points (services → entry points로 변경)
from .entry_point.loader import ImageLoader
from .entry_point.text_recognizer import ImageTextRecognizer
from .entry_point.overlayer import ImageOverlayer

# Image downloader (동기 HTTP 다운로드)
from .services.image_downloader import ImageDownloader, ImageDownloadPolicy, download_images

# Re-export FontPolicy from font_utils for convenience
from font_utils import FontPolicy

__all__ = [
    # Common policies
    "ImageSourcePolicy",
    "ImageSavePolicy",
    "ImageMetaPolicy",
    
    # ImageLoader policies
    "ImageProcessPolicy",
    "ImageLoaderPolicy",
    
    # ImageTextRecognizer policies
    "OCRProviderPolicy",
    "OCRPreprocessPolicy",
    "OCRPostprocessPolicy",
    "ImageOCRPolicy",
    
    # ImageOverlayer policies
    "OverlayTextPolicy",
    "ImageOverlayPolicy",
    
    # Models
    "OCRItem",
    
    # Font
    "FontPolicy",
    
    # Services
    "ImageReader",
    "ImageWriter",
    "ImageProcessor",
    "OverlayTextRenderer",
    
    # Entrypoints
    "ImageLoader",
    "ImageTextRecognizer",
    "ImageOverlayer",
    
    # Image Downloader
    "ImageDownloader",
    "ImageDownloadPolicy",
    "download_images",
    
    # Backward compatibility (deprecated)
    "ImagePolicy",
    "ImageProcessorPolicy",
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



