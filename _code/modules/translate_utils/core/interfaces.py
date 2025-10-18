# -*- coding: utf-8 -*-
"""translate_utils.core.interfaces
===================================

Abstract interfaces for translate_utils components.
프로젝트 관례에 따라 core/에 위치합니다.

참고:
- crawl_utils/core/interfaces.py (Protocol 사용)
- unify_utils/core/base_normalizer.py (ABC 사용)
- structured_io/core/base_parser.py (ABC 사용)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional


class CacheInterface(ABC):
    """Translation cache interface.
    
    세그먼트 단위 번역 캐싱을 제공하는 추상 인터페이스입니다.
    구현체는 services/storage.py의 TranslationStorage입니다.
    """
    
    @abstractmethod
    def get(self, src: str, target_lang: str, model: str) -> Optional[str]:
        """Get cached translation.
        
        Args:
            src: Source text (segment).
            target_lang: Target language code (e.g., "KO").
            model: Translation model name.
        
        Returns:
            Cached translation if found, None otherwise.
        """
        pass
    
    @abstractmethod
    def put(self, src: str, tgt: str, target_lang: str, model: str) -> None:
        """Store translation in cache.
        
        Args:
            src: Source text (segment).
            tgt: Translated text.
            target_lang: Target language code.
            model: Translation model name.
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close cache connection and release resources."""
        pass
    
    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Check if cache is enabled."""
        pass


class WriterInterface(ABC):
    """Translation result writer interface.
    
    번역 결과를 파일로 저장하는 추상 인터페이스입니다.
    구현체는 services/storage.py의 TranslationResultWriter입니다.
    """
    
    @abstractmethod
    def write(self, texts: List[str], translations: List[str]) -> Optional[Path]:
        """Write translation results to file.
        
        Args:
            texts: Original texts.
            translations: Translated texts.
        
        Returns:
            Path to written file if successful, None otherwise.
        """
        pass
    
    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Check if writer is enabled."""
        pass
