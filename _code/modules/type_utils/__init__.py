# -*- coding: utf-8 -*-
# type_utils/__init__.py
# Type inference and file type detection utilities

"""
Type Utils
==========

파일 타입 추론 및 확장자 검출 유틸리티.

주요 기능:
- URL/파일경로에서 타입 자동 추론 (image/video/audio/document/archive/text/file)
- 확장자 추출 및 정규화
- 커스터마이징 가능한 추론 정책

Examples:
    >>> from type_utils import infer_type, extract_extension
    >>> 
    >>> # 타입 추론
    >>> infer_type("https://example.com/photo.jpg")
    'image'
    >>> infer_type("Hello World")
    'text'
    >>> infer_type(b"binary data")
    'file'
    >>> 
    >>> # 확장자 추출
    >>> extract_extension("https://example.com/photo.jpg")
    'jpg'
    >>> extract_extension("archive.tar.gz")
    'gz'
"""

from __future__ import annotations

# Core types
from .core.types import (
    FileType,
    URLType,
    MimeCategory,
    ExtensionMap,
    ValueType,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    ARCHIVE_EXTENSIONS,
)

# Core policies
from .core.policy import (
    InferencePolicy,
    DefaultInferencePolicy,
)

# Services
from .services.inferencer import (
    TypeInferencer,
    get_default_inferencer,
    infer_type,
    infer_extension,
    is_url,
)

from .services.extension import (
    ExtensionDetector,
    get_default_detector,
    extract_extension,
    extract_all_extensions,
    normalize_extension,
)

__version__ = "1.0.0"

__all__ = [
    # Core Types
    "FileType",
    "URLType",
    "MimeCategory",
    "ExtensionMap",
    "ValueType",
    
    # Extension Constants
    "IMAGE_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    "AUDIO_EXTENSIONS",
    "DOCUMENT_EXTENSIONS",
    "ARCHIVE_EXTENSIONS",
    
    # Policies
    "InferencePolicy",
    "DefaultInferencePolicy",
    
    # Type Inferencer
    "TypeInferencer",
    "get_default_inferencer",
    "infer_type",
    "infer_extension",
    "is_url",
    
    # Extension Detector
    "ExtensionDetector",
    "get_default_detector",
    "extract_extension",
    "extract_all_extensions",
    "normalize_extension",
]
