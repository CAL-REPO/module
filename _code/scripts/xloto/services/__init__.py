# -*- coding: utf-8 -*-
"""XLOTO Services Package.

Excel + OTO 파이프라인의 재사용 가능한 서비스 계층.

Components:
- ImageFileManager: 이미지 파일 탐색 및 관리

Note:
- CasExtractor는 제거됨 (xl_utils.ColumnResolver + structured_data로 대체)
"""

from xloto.services.image_file_manager import ImageFileManager  # noqa: F401

__all__ = [
    "ImageFileManager",
]
