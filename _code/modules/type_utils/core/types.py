# -*- coding: utf-8 -*-
# type_utils/core/types.py
# 타입 추론을 위한 타입 정의

"""
Type Utils - Core Types
=======================

파일 타입 추론 및 분류를 위한 핵심 타입 정의.
"""

from typing import Literal, Set, Dict, Union
from pathlib import Path

# 파일 타입 분류
FileType = Literal["image", "text", "file", "video", "audio", "document", "archive", "unknown"]

# URL 타입
URLType = Literal["http", "https", "ftp", "data", "blob", "unknown"]

# MIME 타입 카테고리
MimeCategory = Literal["image", "video", "audio", "text", "application", "unknown"]

# 확장자 매핑 타입
ExtensionMap = Dict[str, FileType]

# 값 타입 (추론 대상)
ValueType = Union[str, bytes, bytearray, Path]

# 확장자 집합 (불변)
IMAGE_EXTENSIONS: Set[str] = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", 
    ".ico", ".tiff", ".tif", ".heic", ".heif", ".avif"
}

VIDEO_EXTENSIONS: Set[str] = {
    ".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".3gp"
}

AUDIO_EXTENSIONS: Set[str] = {
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma",
    ".opus", ".alac"
}

DOCUMENT_EXTENSIONS: Set[str] = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".odt", ".ods", ".odp", ".txt", ".rtf", ".csv"
}

ARCHIVE_EXTENSIONS: Set[str] = {
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
    ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz"
}

# MIME 타입 매핑 (선택적, 향후 확장)
MIME_TO_CATEGORY: Dict[str, MimeCategory] = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/gif": "image",
    "image/webp": "image",
    "image/svg+xml": "image",
    "video/mp4": "video",
    "video/webm": "video",
    "audio/mpeg": "audio",
    "audio/wav": "audio",
    "text/plain": "text",
    "text/html": "text",
    "application/json": "text",
    "application/pdf": "application",
    "application/zip": "application",
}

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
]
