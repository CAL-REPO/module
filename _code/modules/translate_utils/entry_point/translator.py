# -*- coding: utf-8 -*-
"""Translator - Translation service entry point (EntryPoint only).

책임:
1. YAML 파일 기반 번역 실행 (run 메서드)
2. LogManager 통합

실제 번역 로직은 Translate에 위임합니다 (SRP 준수).
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, Optional, Any, Dict

from logs_utils import LogManager

from ..core.policy import TranslatorPolicy
from ..adapter.translate import Translate
from ..services.source_loader import TextSourceLoader


class Translator:
    """번역 EntryPoint - YAML 기반 번역 실행.
    
    실제 번역 로직은 Translate에 위임하여 SRP를 준수합니다.
    
    Attributes:
        policy: TranslatorPolicy 설정 (source, translate, log 포함)
        translate: Translate 인스턴스 (즉시 생성)
    """
    
    def __init__(
        self,
        cfg_like: Union[Path, str, dict, TranslatorPolicy, None] = None,
        *,
        log: Optional[LogManager] = None,
        **overrides: Any
    ):
        """ConfigLoader와 동일한 인자 패턴으로 초기화.
        
        Args:
            cfg_like: TranslatorPolicy 인스턴스, YAML 경로, dict, 또는 None
            log: 외부 LogManager (없으면 policy.log_config로 생성)
            **overrides: 런타임 오버라이드 값 (provider__target_lang, source__text 등)
        
        Example:
            >>> # YAML 파일에서 로드
            >>> translator = Translator("configs/translate.yaml")
            
            >>> # dict로 직접 설정
            >>> translator = Translator({"provider": {"provider": "deepl"}})
            
            >>> # 런타임 오버라이드 (KeyPath 형식)
            >>> translator = Translator("config.yaml", provider__target_lang="EN")
        """
        # Load policy
        self.policy = self._load_config(cfg_like, **overrides)
        
        # Translate 즉시 생성 (self.log 사용을 위해 lazy-loading 제거)
        self._translate: Translate = Translate(cfg_like=self.policy.translate)
        self._source_loader: Optional[TextSourceLoader] = None
    
    # ==========================================================================
    # Config Loading (ConfigLikeLoader pattern)
    # ==========================================================================
    
    def _load_config(self, cfg_like, **overrides) -> TranslatorPolicy:
        """Load TranslatorPolicy from various sources.
        
        Args:
            cfg_like: TranslatorPolicy instance, YAML path, dict, or None
            **overrides: Runtime overrides
        
        Returns:
            TranslatorPolicy instance
        """
        from cfg_utils.services import ConfigLikeLoader
        
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=TranslatorPolicy,
            caller_file=__file__,
            default_config_filename="translator.yaml",
            **overrides
        )
    
    # ==========================================================================
    # Translate & Log Properties
    # ==========================================================================
    
    @property
    def translate(self) -> Translate:
        """Translate instance (already created in __init__).
        
        Returns:
            Translate instance
        """
        return self._translate
    
    @property
    def log(self):
        """Translate의 logger를 사용 (중복 제거)."""
        return self.translate.log
    
    # ==========================================================================
    # Main Execution
    # ==========================================================================
    
    def run(self) -> Dict[str, str]:
        """Execute translation and return source→translated mapping.
        
        Returns:
            Dict mapping source text to translated text
        
        Example:
            >>> translator = Translator("config.yaml")
            >>> result = translator.run()
            >>> print(result)
            {"Hello": "안녕하세요", "Thank you": "감사합니다"}
        """
        self.log.info("=" * 70)
        self.log.info("[Translator] Starting translation")
        self.log.info(f"  Provider: {self.policy.translate.provider.provider}")
        self.log.info(f"  {self.policy.translate.provider.source_lang} → {self.policy.translate.provider.target_lang}")
        
        # Load source texts
        source_loader = TextSourceLoader(self.policy.source)
        payload = source_loader.load()
        sources = payload.texts
        
        if not sources:
            self.log.warning("No texts to translate")
            return {}
        
        self.log.info(f"  Texts: {len(sources)}")
        
        # Delegate to Translate
        mapping = self.translate.run(sources)
        
        self.log.success(f"[Translator] Completed: {len(mapping)} translations")
        self.log.info("=" * 70)
        
        return mapping
    
    # ==========================================================================
    # Resource Cleanup
    # ==========================================================================
    
    def close(self):
        """Translate 종료 및 리소스 정리."""
        try:
            self._translate.close()
            self.log.debug("Translate closed")
        except Exception as e:
            self.log.warning(f"Error closing translate: {e}")
    
    def __del__(self):
        """Destructor - cleanup resources."""
        try:
            self.close()
        except Exception:
            pass
