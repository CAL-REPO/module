# -*- coding: utf-8 -*-
"""Image File Manager Service.

이미지 파일 탐색 및 관리 로직 분리.

책임:
1. Original 폴더 이미지 스캔
2. Translated 폴더 비교 (처리 여부 확인)
3. 미처리 이미지 리스트 반환
4. 경로 생성 및 관리
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from path_utils import resolve


class ImageFileManager:
    """이미지 파일 관리 서비스.
    
    Original/Translated 폴더 간 이미지 비교 및 미처리 파일 탐색.
    
    Attributes:
        public_img_dir: 이미지 루트 디렉토리
        origin_dirname: Original 폴더명
        translated_dirname: Translated 폴더명
        image_extensions: 지원하는 이미지 확장자 리스트
    
    Example:
        >>> manager = ImageFileManager(
        ...     public_img_dir="${public_dir}/01.IMAGE",
        ...     origin_dirname="original",
        ...     translated_dirname="translated"
        ... )
        >>> missing = manager.get_missing_images("CAPFB-001")
    """
    
    # 지원하는 이미지 확장자
    IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
    
    def __init__(
        self,
        public_img_dir: str,
        origin_dirname: str = "original",
        translated_dirname: str = "translated"
    ):
        """Initialize ImageFileManager.
        
        Args:
            public_img_dir: 이미지 루트 디렉토리 (환경변수 resolving 지원)
            origin_dirname: Original 폴더명
            translated_dirname: Translated 폴더명
        """
        self.public_img_dir = Path(resolve(public_img_dir))
        self.origin_dirname = origin_dirname
        self.translated_dirname = translated_dirname
    
    def get_missing_images(self, cas_no: str) -> List[Path]:
        """Translated 폴더에 없는 original 이미지 반환.
        
        Args:
            cas_no: CAS No (예: "CAPFB-001")
        
        Returns:
            미처리 이미지 경로 리스트
        """
        origin_dir = self._get_origin_dir(cas_no)
        translated_dir = self._get_translated_dir(cas_no)
        
        if not origin_dir.exists():
            return []
        
        # Original 폴더의 모든 이미지
        origin_images = self._scan_images(origin_dir)
        
        # Translated 폴더에 없는 파일만 필터링
        missing_images = []
        for img_path in origin_images:
            if not self._is_translated(img_path, translated_dir):
                missing_images.append(img_path)
        
        return missing_images
    
    def _scan_images(self, directory: Path) -> List[Path]:
        """디렉토리에서 모든 이미지 파일 스캔.
        
        Args:
            directory: 스캔할 디렉토리
        
        Returns:
            이미지 파일 경로 리스트 (중복 제거됨)
        
        Note:
            Windows에서 glob은 대소문자 구분하지 않으므로 set으로 중복 제거
        """
        images = []
        for ext in self.IMAGE_EXTENSIONS:
            images.extend(list(directory.glob(f"*{ext}")))
        
        # 중복 제거 (Windows에서 .jpg와 .JPG가 같은 파일 매칭)
        return list(set(images))
    
    def _is_translated(self, origin_path: Path, translated_dir: Path) -> bool:
        """이미지가 번역되었는지 확인.
        
        Translated 폴더에 같은 이름(확장자 무관)의 파일이 있는지 확인.
        
        Args:
            origin_path: Original 이미지 경로
            translated_dir: Translated 폴더 경로
        
        Returns:
            True if translated, False otherwise
        """
        if not translated_dir.exists():
            return False
        
        base_name = origin_path.stem
        
        # 모든 확장자로 검색
        for ext in self.IMAGE_EXTENSIONS:
            if (translated_dir / f"{base_name}{ext}").exists():
                return True
        
        return False
    
    def _get_origin_dir(self, cas_no: str) -> Path:
        """Original 폴더 경로 반환.
        
        Args:
            cas_no: CAS No
        
        Returns:
            Original 폴더 경로
        """
        return self.public_img_dir / cas_no / self.origin_dirname
    
    def _get_translated_dir(self, cas_no: str) -> Path:
        """Translated 폴더 경로 반환.
        
        Args:
            cas_no: CAS No
        
        Returns:
            Translated 폴더 경로
        """
        return self.public_img_dir / cas_no / self.translated_dirname
    
    def get_translated_dir(self, cas_no: str) -> Path:
        """Public API: Translated 폴더 경로 반환.
        
        Args:
            cas_no: CAS No
        
        Returns:
            Translated 폴더 경로
        """
        return self._get_translated_dir(cas_no)
    
    def get_cas_list(self) -> List[str]:
        """이미지 루트 디렉토리의 모든 CAS No 반환.
        
        Returns:
            CAS No 리스트
        """
        if not self.public_img_dir.exists():
            return []
        
        cas_list = []
        for item in self.public_img_dir.iterdir():
            if item.is_dir():
                cas_list.append(item.name)
        
        return sorted(cas_list)
    
    def get_image_count(self, cas_no: str) -> dict:
        """CAS No별 이미지 개수 반환 (디버깅용).
        
        Args:
            cas_no: CAS No
        
        Returns:
            {
                "origin": int,
                "translated": int,
                "missing": int
            }
        """
        origin_dir = self._get_origin_dir(cas_no)
        translated_dir = self._get_translated_dir(cas_no)
        
        origin_count = len(self._scan_images(origin_dir)) if origin_dir.exists() else 0
        translated_count = len(self._scan_images(translated_dir)) if translated_dir.exists() else 0
        missing_count = len(self.get_missing_images(cas_no))
        
        return {
            "origin": origin_count,
            "translated": translated_count,
            "missing": missing_count
        }


__all__ = ["ImageFileManager"]
