# -*- coding: utf-8 -*-
"""Translator - Translation service entry point (EntryPoint only).

책임:
1. YAML 파일 기반 번역 실행 (run 메서드)
2. ConfigLoader 통합 (BaseServiceLoader)
3. LogManager 통합

실제 번역 로직은 Translate에 위임합니다 (SRP 준수).
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, Optional, Any, Dict

from pydantic import BaseModel

from cfg_utils import ConfigLoader
from cfg_utils.core.base_service_loader import BaseServiceLoader
from cfg_utils.core.policy import ConfigPolicy
from logs_utils import LogManager

from ..core.policy import TranslatorPolicy
from ..adapter.translate import Translate
from ..services.source_loader import TextSourceLoader


class Translator(BaseServiceLoader[TranslatorPolicy]):
    """번역 EntryPoint - YAML 기반 번역 실행 (ImageTextRecognizer과 완전 대칭).
    
    BaseServiceLoader를 상속하여 ConfigLoader 통합 및 일관된 설정 로딩을 제공합니다.
    실제 번역 로직은 Translate에 위임하여 SRP를 준수합니다.
    
    Attributes:
        policy: TranslatorPolicy 설정 (source, translate, log 포함)
        log: loguru logger 인스턴스
        translate: Translate 인스턴스 (lazy-loaded)
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        *,
        policy: Optional[ConfigPolicy] = None,
        config_loader_path: Optional[Union[str, Path]] = None,
        log: Optional[LogManager] = None,
        **overrides: Any
    ):
        """ConfigLoader와 동일한 인자 패턴으로 초기화 (ImageTextRecognizer과 완전 대칭).
        
        Args:
            cfg_like: BaseModel, YAML 경로, dict, 또는 None
                - BaseModel: TranslatePolicy 인스턴스 직접 전달
                - str/Path: YAML 파일 경로
                - dict: 설정 딕셔너리
                - None: 기본 설정 파일 사용
            policy: ConfigPolicy 인스턴스
            config_loader_path: config_loader_translate.yaml 경로 override (선택)
            log: 외부 LogManager (없으면 policy.log_config로 생성)
            **overrides: 런타임 오버라이드 값 (provider__target_lang, source__text 등)
        
        Example:
            >>> # YAML 파일에서 로드
            >>> translator = Translator("configs/translate.yaml")
            
            >>> # dict로 직접 설정
            >>> translator = Translator({"provider": {"provider": "deepl"}})
            
            >>> # config_loader_path override
            >>> translator = Translator(config_loader_path="./custom_config_loader.yaml")
            
            >>> # 런타임 오버라이드 (KeyPath 형식)
            >>> translator = Translator("config.yaml", provider__target_lang="EN")
        """
        # BaseServiceLoader 초기화 (self.policy 설정)
        super().__init__(cfg_like, policy=policy, config_loader_path=config_loader_path, **overrides)
        
        # Translate 즉시 생성 (self.log 사용을 위해 lazy-loading 제거)
        self._translate: Translate = Translate(cfg_like=self.policy.translate)
        self._source_loader: Optional[TextSourceLoader] = None
    
    
    # ==========================================================================
    # BaseServiceLoader Abstract Methods Implementation
    # ==========================================================================
    
    def _get_policy_model(self) -> type[TranslatorPolicy]:
        """Policy 모델 클래스 반환."""
        return TranslatorPolicy
    
    def _get_config_loader_path(self) -> Path:
        """config_loader_translate.yaml 경로 반환."""
        return Path(__file__).parent.parent / "configs" / "config_loader_translate.yaml"
    
    def _get_default_section(self) -> str:
        """기본 section 이름: 'translate'."""
        return "translate"
    
    def _get_config_path(self) -> Path:
        """마지막 안전 장치용 기본 설정 파일: translate.yaml."""
        return Path(__file__).parent.parent / "configs" / "translate.yaml"
    
    def _get_reference_context(self) -> dict[str, Any]:
        """paths.local.yaml을 reference_context로 제공."""
        from modules.cfg_utils.services.paths_loader import PathsLoader
        try:
            return PathsLoader.load()
        except FileNotFoundError:
            # paths.local.yaml이 없어도 동작 계속 (선택 사항)
            return {}
    
    # ==========================================================================
    # Translate (Immediate Creation)
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
