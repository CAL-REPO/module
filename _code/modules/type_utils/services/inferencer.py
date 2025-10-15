# -*- coding: utf-8 -*-
# type_utils/services/inferencer.py
# 타입 추론 핵심 로직

"""
Type Utils - Type Inferencer
=============================

값(URL, bytes, 문자열)을 분석하여 파일 타입을 자동으로 추론.
"""

from __future__ import annotations

from typing import Any, Optional
from pathlib import Path
from urllib.parse import urlparse

from ..core.types import FileType, ValueType
from ..core.policy import InferencePolicy, DefaultInferencePolicy


class TypeInferencer:
    """
    값의 타입을 자동으로 추론하는 클래스.
    
    추론 규칙:
    1. 명시적 hint 우선
    2. bytes/bytearray → policy에 따라 처리
    3. URL (http/https/ftp) → 확장자 분석
    4. 파일 경로 (Path) → 확장자 분석
    5. 일반 문자열 → text
    
    Examples:
        >>> inferencer = TypeInferencer()
        >>> inferencer.infer("https://example.com/photo.jpg")
        'image'
        >>> inferencer.infer("Hello World")
        'text'
        >>> inferencer.infer(b"binary data")
        'file'
    """
    
    def __init__(self, policy: Optional[InferencePolicy] = None):
        """
        Args:
            policy: 타입 추론 정책. None이면 기본 정책 사용.
        """
        self.policy = policy or DefaultInferencePolicy.get_default()
    
    def infer(
        self,
        value: Any,
        *,
        hint: Optional[str] = None,
        fallback: FileType = "file"
    ) -> FileType:
        """
        값의 타입을 자동 추론.
        
        Args:
            value: 추론할 값 (str, bytes, Path 등)
            hint: 명시적 타입 힌트 (우선순위 최상위)
            fallback: 추론 실패 시 기본값
        
        Returns:
            추론된 FileType
        
        Examples:
            >>> inferencer.infer("https://img.com/photo.jpg")
            'image'
            >>> inferencer.infer("Product Title")
            'text'
            >>> inferencer.infer(b"\\x89PNG", hint="image")
            'image'
        """
        # 1. 명시적 힌트 우선
        if hint and self._is_valid_file_type(hint):
            return hint  # type: ignore
        
        # 2. bytes/bytearray 타입
        if isinstance(value, (bytes, bytearray)):
            return self.policy.bytes_default_type
        
        # 3. Path 타입
        if isinstance(value, Path):
            return self._infer_from_path(value)
        
        # 4. 문자열 분석
        if isinstance(value, str):
            return self._infer_from_string(value)
        
        # 5. 기타 (dict, list 등)
        return fallback
    
    def infer_extension(
        self,
        value: Any,
        kind: Optional[FileType] = None
    ) -> Optional[str]:
        """
        값에서 파일 확장자 추론.
        
        Args:
            value: 추론할 값
            kind: 파일 타입 (알려진 경우). None이면 자동 추론.
        
        Returns:
            확장자 (점 없이, 예: "jpg") 또는 None
        
        Examples:
            >>> inferencer.infer_extension("https://img.com/photo.jpg")
            'jpg'
            >>> inferencer.infer_extension("data.tar.gz")
            'gz'
        """
        # 1. URL에서 확장자 추출
        if isinstance(value, str) and self.policy.is_url(value):
            parsed = urlparse(value)
            path = Path(parsed.path)
            ext = path.suffix.lstrip(".")
            if ext:
                return ext.lower() if not self.policy.case_sensitive else ext
        
        # 2. Path에서 확장자 추출
        if isinstance(value, (Path, str)):
            path = Path(value) if isinstance(value, str) else value
            ext = path.suffix.lstrip(".")
            if ext:
                return ext.lower() if not self.policy.case_sensitive else ext
        
        # 3. 타입 기반 기본 확장자
        if kind:
            return self._default_extension_for_type(kind)
        
        return None
    
    def is_url(self, value: Any) -> bool:
        """
        값이 URL인지 판별.
        
        Args:
            value: 검사할 값
        
        Returns:
            URL 여부
        """
        if not isinstance(value, str):
            return False
        return self.policy.is_url(value)
    
    def is_image(self, value: Any) -> bool:
        """값이 이미지 타입인지 판별"""
        return self.infer(value) == "image"
    
    def is_video(self, value: Any) -> bool:
        """값이 비디오 타입인지 판별"""
        return self.infer(value) == "video"
    
    def is_audio(self, value: Any) -> bool:
        """값이 오디오 타입인지 판별"""
        return self.infer(value) == "audio"
    
    def is_document(self, value: Any) -> bool:
        """값이 문서 타입인지 판별"""
        return self.infer(value) == "document"
    
    def is_archive(self, value: Any) -> bool:
        """값이 압축 파일 타입인지 판별"""
        return self.infer(value) == "archive"
    
    def is_text(self, value: Any) -> bool:
        """값이 텍스트 타입인지 판별"""
        return self.infer(value) == "text"
    
    # ----------------------------------------------------------------
    # Private Methods
    # ----------------------------------------------------------------
    
    def _infer_from_string(self, value: str) -> FileType:
        """문자열에서 타입 추론"""
        # URL 체크
        if self.policy.is_url(value):
            return self._infer_from_url(value)
        
        # 파일 경로처럼 보이는 경우
        if "/" in value or "\\" in value or "." in value:
            path = Path(value)
            ext = path.suffix
            if ext:
                file_type = self.policy.get_file_type(ext)
                if file_type:
                    return file_type
                return self.policy.unknown_extension_type
        
        # 일반 텍스트
        return self.policy.text_default_type
    
    def _infer_from_url(self, url: str) -> FileType:
        """URL에서 타입 추론"""
        parsed = urlparse(url)
        path = Path(parsed.path)
        ext = path.suffix
        
        if not ext:
            return self.policy.url_without_extension_type
        
        file_type = self.policy.get_file_type(ext)
        if file_type:
            return file_type
        
        return self.policy.unknown_extension_type
    
    def _infer_from_path(self, path: Path) -> FileType:
        """Path 객체에서 타입 추론"""
        ext = path.suffix
        
        if not ext:
            return self.policy.unknown_extension_type
        
        file_type = self.policy.get_file_type(ext)
        if file_type:
            return file_type
        
        return self.policy.unknown_extension_type
    
    def _is_valid_file_type(self, hint: str) -> bool:
        """hint가 유효한 FileType인지 검증"""
        valid_types = {
            "image", "text", "file", "video", "audio",
            "document", "archive", "unknown"
        }
        return hint in valid_types
    
    def _default_extension_for_type(self, file_type: FileType) -> str:
        """파일 타입의 기본 확장자 반환"""
        defaults = {
            "image": "jpg",
            "video": "mp4",
            "audio": "mp3",
            "text": "txt",
            "document": "pdf",
            "archive": "zip",
            "file": "bin",
            "unknown": "bin",
        }
        return defaults.get(file_type, "bin")


# Singleton 인스턴스 (기본 정책)
_default_inferencer: Optional[TypeInferencer] = None


def get_default_inferencer() -> TypeInferencer:
    """기본 TypeInferencer 인스턴스 반환 (싱글톤)"""
    global _default_inferencer
    if _default_inferencer is None:
        _default_inferencer = TypeInferencer()
    return _default_inferencer


# 편의 함수 (클래스 인스턴스 없이 사용 가능)
def infer_type(value: Any, *, hint: Optional[str] = None) -> FileType:
    """값의 타입 추론 (편의 함수)"""
    return get_default_inferencer().infer(value, hint=hint)


def infer_extension(value: Any, kind: Optional[FileType] = None) -> Optional[str]:
    """확장자 추론 (편의 함수)"""
    return get_default_inferencer().infer_extension(value, kind=kind)


def is_url(value: Any) -> bool:
    """URL 여부 판별 (편의 함수)"""
    return get_default_inferencer().is_url(value)


__all__ = [
    "TypeInferencer",
    "get_default_inferencer",
    "infer_type",
    "infer_extension",
    "is_url",
]
