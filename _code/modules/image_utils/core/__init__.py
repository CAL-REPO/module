# -*- coding: utf-8 -*-
# image_utils/core/__init__.py
"""Core module for image_utils.

Exports:
- All policy classes (unified)
- Data models (OCRItem, etc.)
"""

from .policy import (
    # Common policies
    ImageSourcePolicy,
    ImageSavePolicy,
    ImageMetaPolicy,
    
    # ImageLoader policies
    ImageProcessPolicy,
    ImageLoaderPolicy,
    
    # ImageOCR policies
    OCRProviderPolicy,
    OCRPreprocessPolicy,
    OCRPostprocessPolicy,
    ImageOCRPolicy,
    
    # ImageOverlay policies
    OverlayTextPolicy,
    ImageOverlayPolicy,
    
    # Backward compatibility aliases (deprecated)
    ImagePolicy,
    ImageProcessorPolicy,
)

from .models import OCRItem

__all__ = [
    # Common policies
    "ImageSourcePolicy",
    "ImageSavePolicy",
    "ImageMetaPolicy",
    
    # ImageLoader policies
    "ImageProcessPolicy",
    "ImageLoaderPolicy",
    
    # ImageOCR policies
    "OCRProviderPolicy",
    "OCRPreprocessPolicy",
    "OCRPostprocessPolicy",
    "ImageOCRPolicy",
    
    # ImageOverlay policies
    "OverlayTextPolicy",
    "ImageOverlayPolicy",
    
    # Data models
    "OCRItem",
    
    # Backward compatibility (deprecated)
    "ImagePolicy",
    "ImageProcessorPolicy",
]
