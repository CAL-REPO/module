# -*- coding: utf-8 -*-
"""Translate - Core translation business logic (SRP-compliant + BaseServiceLoader).

책임:
1. 텍스트 리스트를 받아 번역 실행
2. Pipeline 오케스트레이션 (세그먼트 분할, 캐싱, bulk 번역)
3. 번역 결과 매핑 반환 (Dict[원본, 번역])
4. BaseServiceLoader 통합으로 config_loader 지원

이 클래스는 Translator(EntryPoint)와 분리되어 순수한 번역 로직만 담당합니다.
Standalone 사용 + EntryPoint에서 위임 받는 겸용 Adapter입니다.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Optional, Any, Union

from pydantic import BaseModel

from path_utils.os_paths import OSPath
from logs_utils import LogManager
from cfg_utils.core.base_service_loader import BaseServiceLoader
from cfg_utils.core.policy import ConfigPolicy

from ..core.policy import TranslatePolicy
from ..providers.factory import ProviderFactory
from ..providers.base import Provider
from ..services.pipeline import TranslationPipeline
from ..services.source_loader import SourcePayload
from ..services.preprocessor import TextPreprocessor
from ..services.storage import TranslationStorage, TranslationResultWriter


class Translate(BaseServiceLoader[TranslatePolicy]):
    """Core translation service providing run() API.
    
    BaseServiceLoader를 상속하여 ConfigLoader 통합 및 일관된 설정 로딩을 제공합니다.
    Standalone 사용 가능 + Translator에서 위임 받는 Adapter 역할 겸용.
    
    Attributes:
        policy: TranslatePolicy 설정
        provider: 번역 Provider 인스턴스 (lazy-loaded)
        pipeline: 번역 Pipeline 인스턴스 (lazy-loaded)
        log: loguru logger 인스턴스
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        *,
        policy: Optional[ConfigPolicy] = None,
        config_loader_path: Optional[Union[str, Path]] = None,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize Translate with policy.
        
        Args:
            cfg_like: BaseModel, YAML 경로, dict, 또는 None
            policy: ConfigPolicy 인스턴스
            config_loader_path: translate_cfg_loader.yaml 경로 override
            log_manager: 외부 LogManager (선택사항)
            **overrides: 런타임 오버라이드
        
        Example:
            >>> # YAML에서 로드
            >>> translate = Translate("configs/translate.yaml")
            
            >>> # dict로 직접 설정
            >>> translate = Translate({"provider": {"provider": "deepl"}})
            
            >>> # Policy 인스턴스로
            >>> policy = TranslatePolicy(...)
            >>> translate = Translate(policy)
            
            >>> # 런타임 오버라이드
            >>> translate = Translate("config.yaml", provider__target_lang="EN")
        """
        # BaseServiceLoader 초기화 (self.policy 설정)
        super().__init__(cfg_like, policy=policy, config_loader_path=config_loader_path, **overrides)
        
        # LogManager 생성 (우선순위: 외부 log_manager > policy.log > 기본)
        if log_manager:
            self.log = log_manager.logger
        elif self.policy.log:
            # ✅ LogPolicy.enabled에 따라 LogManager가 handler 등록 여부 결정
            self.log = LogManager(self.policy.log).logger
        else:
            # policy.log가 None이면 enabled=False LogManager 생성
            self.log = LogManager({"enabled": False}).logger
        
        # Provider와 Pipeline은 lazy-load
        self._provider: Optional[Provider] = None
        self._pipeline: Optional[TranslationPipeline] = None
    
    # ==========================================================================
    # BaseServiceLoader Abstract Methods (필수 구현)
    # ==========================================================================
    
    def _get_policy_model(self) -> type[TranslatePolicy]:
        """Policy 모델 클래스 반환 (BaseServiceLoader 요구사항)."""
        return TranslatePolicy
    
    def _get_config_loader_path(self) -> Path:
        """translate_cfg_loader.yaml 경로 반환."""
        return Path(__file__).parent.parent / "configs" / "translate_cfg_loader.yaml"
    
    def _get_default_section(self) -> str:
        """기본 section 이름: 'translate'."""
        return "translate"
    
    def _get_config_path(self) -> Path:
        """마지막 안전 장치용 기본 설정 파일: translate.yaml."""
        return Path(__file__).parent.parent / "configs" / "translate.yaml"
    
    def _get_reference_context(self) -> dict[str, Any]:
        """paths.local.yaml을 reference_context로 제공."""
        from cfg_utils.services.paths_loader import PathsLoader
        try:
            return PathsLoader.load()
        except FileNotFoundError:
            return {}
    
    # ==========================================================================
    # Provider & Pipeline (Lazy Creation)
    # ==========================================================================
    
    @property
    def provider(self) -> Provider:
        """Lazy provider creation using ProviderFactory.
        
        Returns:
            Provider instance
        """
        if self._provider is None:
            self.log.debug(f"Creating provider: {self.policy.provider.provider}")
            self._provider = ProviderFactory.create(
                provider_name=self.policy.provider.provider,
                api_key=None,  # Will use env var
                timeout=self.policy.provider.timeout
            )
        return self._provider
    
    @property
    def pipeline(self) -> TranslationPipeline:
        """Lazy pipeline creation.
        
        Returns:
            TranslationPipeline instance
        """
        if self._pipeline is None:
            self.log.debug("Creating translation pipeline")
            
            # Create components
            preprocessor = TextPreprocessor(self.policy.zh)
            
            # Cache (optional)
            cache = None
            if self.policy.store.save_db:
                default_dir = OSPath.downloads()
                cache = TranslationStorage(self.policy.store, default_dir=default_dir)
            
            # Writer (optional)
            writer = None
            if self.policy.store.save_tr:
                default_dir = OSPath.downloads()
                writer = TranslationResultWriter(self.policy.store, default_dir=default_dir)
            
            # Create pipeline
            self._pipeline = TranslationPipeline(
                policy=self.policy,
                provider=self.provider,
                preprocessor=preprocessor,
                cache=cache,
                writer=writer,
                log=self.log
            )
        
        return self._pipeline
    
    # ==========================================================================
    # Main API
    # ==========================================================================
    
    def run(self, texts: List[str]) -> Dict[str, str]:
        """Translate texts and return source→translated mapping.
        
        스크립트 레벨에서 동적으로 텍스트 리스트를 전달받아 번역합니다.
        
        ✅ 배치 번역: 캐시 미스된 세그먼트를 한 번에 번역
        ✅ DB 캐싱: pipeline.run()에서 자동 동작
        ✅ 세그먼트 단위 재사용: 재사용률 극대화
        
        Args:
            texts: 번역할 텍스트 리스트
        
        Returns:
            Dict mapping source text to translated text
        
        Example:
            >>> translate = Translate(policy)
            >>> texts = ["Hello", "Thank you", "Goodbye"]
            >>> result = translate.run(texts)
            >>> print(result)
            {"Hello": "안녕하세요", "Thank you": "감사합니다", "Goodbye": "안녕히 가세요"}
        """
        if not texts:
            self.log.warning("No texts to translate")
            return {}
        
        self.log.info(f"[Translate] Translating {len(texts)} texts")
        
        # SourcePayload 직접 생성 (policy.source 우회)
        payload = SourcePayload(texts=texts, source_path=None)
        
        # Pipeline 실행 (배치 번역 + 캐싱 자동 동작)
        translations = self.pipeline.run(payload)
        
        # Mapping 생성
        mapping: Dict[str, str] = {}
        for idx, src in enumerate(texts):
            translated = translations[idx] if idx < len(translations) else ""
            mapping[src] = translated
        
        self.log.success(f"[Translate] Completed: {len(mapping)} translations")
        
        return mapping
    
    # ==========================================================================
    # Resource Cleanup
    # ==========================================================================
    
    def close(self):
        """Provider 종료 및 리소스 정리."""
        if self._provider:
            try:
                self._provider.close()
                self.log.debug("Provider closed")
            except Exception as e:
                self.log.warning(f"Error closing provider: {e}")
            finally:
                self._provider = None
    
    def __del__(self):
        """Destructor - cleanup resources."""
        try:
            if self._provider:
                self.close()
        except Exception:
            pass
