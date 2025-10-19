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
    
    # Adapter policies (source 없음)
    ImageLoadPolicy,
    ImageTextRecognizePolicy,
    ImageOverlayPolicy,
    
    # EntryPoint policies (source 포함)
    ImageLoaderPolicy,
    ImageTextRecognizerPolicy,
    ImageOverlayerPolicy,
    
    # Sub-policies
    ImageProcessPolicy,
    OCRProviderPolicy,
    OCRPreprocessPolicy,
    OCRPostprocessPolicy,
    OverlayItemPolicy,
)

from .models import OCRItem

__all__ = [
    # Common policies
    "ImageSourcePolicy",
    "ImageSavePolicy",
    "ImageMetaPolicy",
    
    # Adapter policies (source 없음)
    "ImageLoadPolicy",
    "ImageTextRecognizePolicy",
    "ImageOverlayPolicy",
    
    # EntryPoint policies (source 포함)
    "ImageLoaderPolicy",
    "ImageTextRecognizerPolicy",
    "ImageOverlayerPolicy",
    
    # Sub-policies
    "ImageProcessPolicy",
    "OCRProviderPolicy",
    "OCRPreprocessPolicy",
    "OCRPostprocessPolicy",
    "OverlayItemPolicy",
    
    # Data models
    "OCRItem",
]
