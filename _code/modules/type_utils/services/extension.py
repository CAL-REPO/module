# -*- coding: utf-8 -*-
# type_utils/services/extension.py
# 확장자 추출 및 검증

"""
Type Utils - Extension Detector
================================

파일 확장자 추출, 검증, 변환 유틸리티.
"""

from __future__ import annotations

from typing import Optional, List
from pathlib import Path
from urllib.parse import urlparse

from ..core.types import FileType
from ..core.policy import InferencePolicy, DefaultInferencePolicy


class ExtensionDetector:
    """
    파일 확장자 추출 및 검증 유틸리티.
    
    기능:
    - URL/파일경로에서 확장자 추출
    - 다중 확장자 처리 (예: .tar.gz)
    - 확장자 정규화 (소문자 변환, 점 제거)
    - 확장자 검증 (허용 목록)
    
    Examples:
        >>> detector = ExtensionDetector()
        >>> detector.extract("https://example.com/photo.jpg")
        'jpg'
        >>> detector.extract("archive.tar.gz")
        'gz'
        >>> detector.extract_all("archive.tar.gz")
        ['tar', 'gz']
    """
    
    def __init__(self, policy: Optional[InferencePolicy] = None):
        """
        Args:
            policy: 추론 정책. None이면 기본 정책 사용.
        """
        self.policy = policy or DefaultInferencePolicy.get_default()
    
    def extract(
        self,
        value: str,
        *,
        normalize: bool = True,
        include_dot: bool = False
    ) -> Optional[str]:
        """
        값에서 (마지막) 확장자 추출.
        
        Args:
            value: URL, 파일 경로, 파일명
            normalize: 소문자 변환 여부
            include_dot: 점(.) 포함 여부
        
        Returns:
            확장자 또는 None
        
        Examples:
            >>> detector.extract("photo.jpg")
            'jpg'
            >>> detector.extract("photo.jpg", include_dot=True)
            '.jpg'
            >>> detector.extract("archive.tar.gz")
            'gz'
        """
        # URL에서 경로 추출
        if self._is_url(value):
            parsed = urlparse(value)
            value = parsed.path
        
        # Path 객체로 변환
        path = Path(value)
        ext = path.suffix
        
        if not ext:
            return None
        
        # 정규화
        if not include_dot:
            ext = ext.lstrip(".")
        
        if normalize and not self.policy.case_sensitive:
            ext = ext.lower()
        
        return ext if ext else None
    
    def extract_all(
        self,
        value: str,
        *,
        normalize: bool = True,
        include_dot: bool = False
    ) -> List[str]:
        """
        값에서 모든 확장자 추출 (다중 확장자 지원).
        
        Args:
            value: URL, 파일 경로, 파일명
            normalize: 소문자 변환 여부
            include_dot: 점(.) 포함 여부
        
        Returns:
            확장자 리스트
        
        Examples:
            >>> detector.extract_all("archive.tar.gz")
            ['tar', 'gz']
            >>> detector.extract_all("data.backup.zip")
            ['backup', 'zip']
        """
        # URL에서 경로 추출
        if self._is_url(value):
            parsed = urlparse(value)
            value = parsed.path
        
        # Path 객체로 변환
        path = Path(value)
        suffixes = path.suffixes
        
        if not suffixes:
            return []
        
        # 정규화
        extensions = []
        for ext in suffixes:
            if not include_dot:
                ext = ext.lstrip(".")
            
            if normalize and not self.policy.case_sensitive:
                ext = ext.lower()
            
            if ext:
                extensions.append(ext)
        
        return extensions
    
    def normalize(self, extension: str, *, include_dot: bool = False) -> str:
        """
        확장자 정규화.
        
        Args:
            extension: 확장자 (예: "JPG", ".jpg", "jpg")
            include_dot: 점(.) 포함 여부
        
        Returns:
            정규화된 확장자
        
        Examples:
            >>> detector.normalize("JPG")
            'jpg'
            >>> detector.normalize(".JPG", include_dot=True)
            '.jpg'
        """
        # 점 제거
        ext = extension.lstrip(".")
        
        # 소문자 변환
        if not self.policy.case_sensitive:
            ext = ext.lower()
        
        # 점 추가
        if include_dot:
            ext = f".{ext}"
        
        return ext
    
    def is_image_extension(self, extension: str) -> bool:
        """확장자가 이미지 타입인지 검증"""
        ext = self.normalize(extension, include_dot=True)
        return ext in self.policy.image_extensions
    
    def is_video_extension(self, extension: str) -> bool:
        """확장자가 비디오 타입인지 검증"""
        ext = self.normalize(extension, include_dot=True)
        return ext in self.policy.video_extensions
    
    def is_audio_extension(self, extension: str) -> bool:
        """확장자가 오디오 타입인지 검증"""
        ext = self.normalize(extension, include_dot=True)
        return ext in self.policy.audio_extensions
    
    def is_document_extension(self, extension: str) -> bool:
        """확장자가 문서 타입인지 검증"""
        ext = self.normalize(extension, include_dot=True)
        return ext in self.policy.document_extensions
    
    def is_archive_extension(self, extension: str) -> bool:
        """확장자가 압축 파일 타입인지 검증"""
        ext = self.normalize(extension, include_dot=True)
        return ext in self.policy.archive_extensions
    
    def get_file_type(self, extension: str) -> Optional[FileType]:
        """
        확장자에서 파일 타입 추론.
        
        Args:
            extension: 확장자
        
        Returns:
            FileType 또는 None
        
        Examples:
            >>> detector.get_file_type("jpg")
            'image'
            >>> detector.get_file_type(".mp4")
            'video'
        """
        ext = self.normalize(extension, include_dot=True)
        return self.policy.get_file_type(ext)
    
    def replace_extension(
        self,
        filename: str,
        new_extension: str,
        *,
        normalize: bool = True
    ) -> str:
        """
        파일명의 확장자 변경.
        
        Args:
            filename: 원본 파일명
            new_extension: 새 확장자 (점 있어도 됨)
            normalize: 확장자 정규화 여부
        
        Returns:
            변경된 파일명
        
        Examples:
            >>> detector.replace_extension("photo.jpg", "png")
            'photo.png'
            >>> detector.replace_extension("data.tar.gz", ".bz2")
            'data.tar.bz2'
        """
        path = Path(filename)
        stem = path.stem
        
        # 확장자 정규화
        if normalize:
            new_ext = self.normalize(new_extension, include_dot=False)
        else:
            new_ext = new_extension.lstrip(".")
        
        return f"{stem}.{new_ext}"
    
    # ----------------------------------------------------------------
    # Private Methods
    # ----------------------------------------------------------------
    
    def _is_url(self, value: str) -> bool:
        """URL 여부 판별"""
        return self.policy.is_url(value)


# Singleton 인스턴스
_default_detector: Optional[ExtensionDetector] = None


def get_default_detector() -> ExtensionDetector:
    """기본 ExtensionDetector 인스턴스 반환 (싱글톤)"""
    global _default_detector
    if _default_detector is None:
        _default_detector = ExtensionDetector()
    return _default_detector


# 편의 함수
def extract_extension(value: str, normalize: bool = True) -> Optional[str]:
    """확장자 추출 (편의 함수)"""
    return get_default_detector().extract(value, normalize=normalize)


def extract_all_extensions(value: str) -> List[str]:
    """모든 확장자 추출 (편의 함수)"""
    return get_default_detector().extract_all(value)


def normalize_extension(extension: str) -> str:
    """확장자 정규화 (편의 함수)"""
    return get_default_detector().normalize(extension)


__all__ = [
    "ExtensionDetector",
    "get_default_detector",
    "extract_extension",
    "extract_all_extensions",
    "normalize_extension",
]
