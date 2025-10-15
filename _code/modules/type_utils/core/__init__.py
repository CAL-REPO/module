# -*- coding: utf-8 -*-
# type_utils/core/__init__.py
# Core types and policies

from .types import (
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
    MIME_TO_CATEGORY,
)

from .policy import (
    InferencePolicy,
    DefaultInferencePolicy,
)

__all__ = [
    # Types
    "FileType",
    "URLType",
    "MimeCategory",
    "ExtensionMap",
    "ValueType",
    
    # Extension Sets
    "IMAGE_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    "AUDIO_EXTENSIONS",
    "DOCUMENT_EXTENSIONS",
    "ARCHIVE_EXTENSIONS",
    
    # MIME Mapping
    "MIME_TO_CATEGORY",
    
    # Policies
    "InferencePolicy",
    "DefaultInferencePolicy",
]
