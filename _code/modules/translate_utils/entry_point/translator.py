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
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """ConfigLoader와 동일한 인자 패턴으로 초기화.
        
        Args:
            cfg_like: TranslatorPolicy 인스턴스, YAML 경로, dict, 또는 None
            log_manager: 외부 LogManager (없으면 policy.log_config로 생성)
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
        
        # Translate 생성 시 log_manager 전달
        self._translate: Translate = Translate(
            cfg_like=self.policy.translate,
            log_manager=log_manager
        )
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
        
        return ConfigLikeLoader.load(
            cfg_like=cfg_like,
            policy_class=TranslatorPolicy,
            module_file=__file__,
            config_filename="translator.yaml",
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
    
    def run(
        self,
        texts: Optional[list[str]] = None
    ) -> Dict[str, str]:
        """Execute translation and return source→translated mapping.
        
        Args:
            texts: 번역할 텍스트 리스트 (제공되면 source 무시)
        
        Returns:
            Dict mapping source text to translated text
        
        Raises:
            ValueError: texts와 policy.source 둘 다 없을 때
        
        Example:
            >>> # source에서 로드
            >>> translator = Translator("config.yaml")
            >>> result = translator.run()
            
            >>> # texts 직접 전달 (OTO 파이프라인)
            >>> result = translator.run(texts=["Hello", "Thank you"])
        """
        self.log.info("=" * 70)
        self.log.info("[Translator] Starting translation")
        self.log.info(f"  Provider: {self.policy.translate.provider.provider}")
        self.log.info(f"  {self.policy.translate.provider.source_lang} → {self.policy.translate.provider.target_lang}")
        
        # 1. 텍스트 결정: texts 파라미터 > source
        if texts is not None:
            sources = texts
            self.log.info(f"  Using provided texts: {len(sources)}")
        else:
            # Load source texts
            if not hasattr(self.policy, 'source') or self.policy.source is None:
                raise ValueError("Either 'texts' parameter or 'policy.source' must be provided")
            
            source_loader = TextSourceLoader(self.policy.source)
            payload = source_loader.load()
            sources = payload.texts
            self.log.info(f"  Loaded from source: {len(sources)}")
        
        if not sources:
            self.log.warning("No texts to translate")
            return {}
        
        # 2. Delegate to Translate
        mapping = self.translate.run(sources)
        
        self.log.success(f"[Translator] Completed: {len(mapping)} translations")
        self.log.info("=" * 70)
        
        return mapping
    
    # ==========================================================================
    # Private Methods: Save
    # ==========================================================================
    
    def _save_result(self, mapping: Dict[str, str]) -> Path:
        """번역 결과를 JSON으로 저장."""
        import json
        from path_utils import downloads
        from datetime import datetime
        
        # 저장 디렉토리
        save_dir = downloads() / "translations"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = save_dir / f"translation_{timestamp}.json"
        
        # JSON 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
        
        return output_path
    
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
