# -*- coding: utf-8 -*-
# type_utils/core/policy.py
# 타입 추론 정책 및 규칙

"""
Type Utils - Inference Policy
==============================

타입 추론 규칙 및 설정을 정의하는 Policy 클래스.
"""

from __future__ import annotations

from typing import Optional, Dict, Set
from pydantic import BaseModel, Field

from .types import (
    FileType,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    AUDIO_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    ARCHIVE_EXTENSIONS,
)


class InferencePolicy(BaseModel):
    """
    타입 추론 정책.
    
    확장자 기반 타입 매핑, URL 판별 규칙, 바이너리 데이터 처리 규칙 등을 정의.
    """
    
    # 확장자 매핑 (커스터마이징 가능)
    image_extensions: Set[str] = Field(
        default_factory=lambda: IMAGE_EXTENSIONS.copy(),
        description="이미지 파일 확장자 집합"
    )
    video_extensions: Set[str] = Field(
        default_factory=lambda: VIDEO_EXTENSIONS.copy(),
        description="비디오 파일 확장자 집합"
    )
    audio_extensions: Set[str] = Field(
        default_factory=lambda: AUDIO_EXTENSIONS.copy(),
        description="오디오 파일 확장자 집합"
    )
    document_extensions: Set[str] = Field(
        default_factory=lambda: DOCUMENT_EXTENSIONS.copy(),
        description="문서 파일 확장자 집합"
    )
    archive_extensions: Set[str] = Field(
        default_factory=lambda: ARCHIVE_EXTENSIONS.copy(),
        description="압축 파일 확장자 집합"
    )
    
    # URL 판별 규칙
    url_schemes: Set[str] = Field(
        default_factory=lambda: {"http", "https", "ftp"},
        description="URL로 인식할 스킴 집합"
    )
    
    # 추론 규칙
    bytes_default_type: FileType = Field(
        "file",
        description="bytes 타입의 기본 파일 타입"
    )
    unknown_extension_type: FileType = Field(
        "file",
        description="알 수 없는 확장자의 기본 타입"
    )
    text_default_type: FileType = Field(
        "text",
        description="일반 문자열의 기본 타입"
    )
    
    # URL 추론 규칙
    url_without_extension_type: FileType = Field(
        "file",
        description="확장자 없는 URL의 기본 타입"
    )
    
    # 대소문자 구분
    case_sensitive: bool = Field(
        False,
        description="확장자 대소문자 구분 여부"
    )
    
    # 커스텀 매핑 (우선순위 최상위)
    custom_mappings: Dict[str, FileType] = Field(
        default_factory=dict,
        description="커스텀 확장자 → 파일 타입 매핑"
    )
    
    def get_file_type(self, extension: str) -> Optional[FileType]:
        """
        확장자에서 파일 타입 추론.
        
        Args:
            extension: 파일 확장자 (예: ".jpg", "jpg")
        
        Returns:
            FileType 또는 None (알 수 없는 경우)
        """
        # 확장자 정규화
        ext = extension if extension.startswith(".") else f".{extension}"
        if not self.case_sensitive:
            ext = ext.lower()
        
        # 1. 커스텀 매핑 우선
        if ext in self.custom_mappings:
            return self.custom_mappings[ext]
        
        # 2. 기본 매핑
        if ext in self.image_extensions:
            return "image"
        if ext in self.video_extensions:
            return "video"
        if ext in self.audio_extensions:
            return "audio"
        if ext in self.document_extensions:
            return "document"
        if ext in self.archive_extensions:
            return "archive"
        
        # 3. 알 수 없음
        return None
    
    def is_url(self, value: str) -> bool:
        """
        문자열이 URL인지 판별.
        
        Args:
            value: 검사할 문자열
        
        Returns:
            URL 여부
        """
        value_lower = value.lower()
        return any(value_lower.startswith(f"{scheme}://") for scheme in self.url_schemes)
    
    def add_custom_mapping(self, extension: str, file_type: FileType) -> None:
        """
        커스텀 확장자 매핑 추가.
        
        Args:
            extension: 확장자 (예: ".custom")
            file_type: 파일 타입
        """
        ext = extension if extension.startswith(".") else f".{extension}"
        if not self.case_sensitive:
            ext = ext.lower()
        self.custom_mappings[ext] = file_type


class DefaultInferencePolicy:
    """기본 정책 제공"""
    
    @staticmethod
    def get_default() -> InferencePolicy:
        """기본 정책 반환"""
        return InferencePolicy()
    
    @staticmethod
    def get_strict() -> InferencePolicy:
        """엄격한 정책 (알 수 없는 타입은 unknown)"""
        return InferencePolicy(
            bytes_default_type="unknown",
            unknown_extension_type="unknown",
            url_without_extension_type="unknown",
        )
    
    @staticmethod
    def get_permissive() -> InferencePolicy:
        """관대한 정책 (모든 알 수 없는 타입은 file)"""
        return InferencePolicy(
            bytes_default_type="file",
            unknown_extension_type="file",
            text_default_type="text",
            url_without_extension_type="file",
        )


__all__ = [
    "InferencePolicy",
    "DefaultInferencePolicy",
]
