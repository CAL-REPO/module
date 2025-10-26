# -*- coding: utf-8 -*-
"""Translate - Core translation business logic (SRP-compliant).

책임:
1. 텍스트 리스트를 받아 번역 실행
2. Pipeline 오케스트레이션 (세그먼트 분할, 캐싱, bulk 번역)
3. 번역 결과 매핑 반환 (Dict[원본, 번역])

이 클래스는 Translator(EntryPoint)와 분리되어 순수한 번역 로직만 담당합니다.
Standalone 사용 + EntryPoint에서 위임 받는 겸용 Adapter입니다.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Optional, Any, Union

from modules.path_utils.os_paths import OSPath
from modules.logs_utils import LogManager
from modules.keypath_utils import KeyPathDict

from ..core.policy import TranslatePolicy
from ..providers.factory import ProviderFactory
from ..providers.base import Provider
from ..services.pipeline import TranslationPipeline
from ..services.source_loader import SourcePayload
from ..services.preprocessor import TextPreprocessor
from ..services.storage import TranslationStorage, TranslationResultWriter


class Translate:
    """Core translation service providing run() API.
    
    Standalone 사용 가능 + Translator에서 위임 받는 Adapter 역할 겸용.
    
    Attributes:
        policy: TranslatePolicy 설정
        provider: 번역 Provider 인스턴스 (lazy-loaded)
        pipeline: 번역 Pipeline 인스턴스 (lazy-loaded)
        log: loguru logger 인스턴스
    """
    
    def __init__(
        self,
        cfg_like: Union[Path, str, dict, TranslatePolicy, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize Translate with dual logging support.
        
        Logging Strategy:
            1. Primary Logger (Parent): 통합 로그 - 전체 파이프라인 기록
            2. Secondary Logger (Module): 모듈별 로그 - 상세 디버깅용 (선택적)
        
        Args:
            cfg_like: TranslatePolicy, YAML 경로, dict, 또는 None
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
        # Load policy
        self.policy = self._load_config(cfg_like, **overrides)
        
        # ========================================
        # Primary Logger: Parent logger (통합 로그)
        # ========================================
        if log_manager:
            self.log = log_manager.logger
            self._parent_log_manager = log_manager
        elif self.policy.log:
            self._parent_log_manager = LogManager(self.policy.log)
            self.log = self._parent_log_manager.logger
        else:
            self._parent_log_manager = None
            self.log = LogManager({"enabled": False}).logger
        
        # ========================================
        # Secondary Logger: Module logger (모듈별 로그 - 선택적)
        # ========================================
        self._module_log_manager = None
        self._module_logger = None
        
        if self.policy.log and self.policy.log.enabled and log_manager:
            # Parent logger가 있고 policy.log도 enabled면 모듈 전용 LogManager 생성
            self._module_log_manager = LogManager(self.policy.log)
            self._module_logger = self._module_log_manager.logger
        
        # Provider와 Pipeline은 lazy-load
        self._provider: Optional[Provider] = None
        self._pipeline: Optional[TranslationPipeline] = None
        
        self.log.debug("Translate initialized with dual logging")
        if self._module_logger:
            self._module_logger.debug("Module-specific logger enabled for detailed debugging")
    
    # ==========================================================================
    # Config Loading (ConfigLikeLoader pattern)
    # ==========================================================================
    
    def _load_config(self, cfg_like, **overrides) -> TranslatePolicy:
        """Load TranslatePolicy from various sources.
        
        ConfigLikeLoader가 모든 경우를 처리:
        1. Policy 인스턴스 → 그대로 반환
        2. Path/str → ConfigLoader로 YAML 로드
        3. dict → ConfigLoader로 파싱 (Policy.name section 자동 추출)
        4. None → 기본 YAML 또는 Pydantic 기본값
        
        Args:
            cfg_like: TranslatePolicy instance, YAML path, dict, or None
            **overrides: Runtime overrides
        
        Returns:
            TranslatePolicy instance
        """
        from cfg_utils.services import ConfigLikeLoader
        
        return ConfigLikeLoader.load(
            cfg_like=cfg_like,
            policy_class=TranslatePolicy,
            module_file=__file__,
            config_filename="translate.yaml",
            **overrides
        )
    
    def _log_both(self, level: str, message: str, **kwargs):
        """Log to both parent and module loggers.
        
        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            **kwargs: Additional context (e.g., exc_info=True)
        """
        # Primary: Parent logger (항상 기록)
        getattr(self.log, level)(message, **kwargs)
        
        # Secondary: Module logger (있으면 기록)
        if self._module_logger:
            getattr(self._module_logger, level)(message, **kwargs)

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
    
    def run(self, texts: List[str], **overrides) -> Dict[str, str]:
        """Translate texts and return source→translated mapping.
        
        스크립트 레벨에서 동적으로 텍스트 리스트를 전달받아 번역합니다.
        
        ✅ 배치 번역: 캐시 미스된 세그먼트를 한 번에 번역
        ✅ DB 캐싱: pipeline.run()에서 자동 동작
        ✅ 세그먼트 단위 재사용: 재사용률 극대화
        
        Args:
            texts: 번역할 텍스트 리스트
            **overrides: Runtime overrides (KeyPath format, no prefix)
        
        Returns:
            Dict mapping source text to translated text
        
        Example:
            >>> translate = Translate(policy)
            >>> texts = ["Hello", "Thank you", "Goodbye"]
            >>> result = translate.run(texts)
            >>> print(result)
            {"Hello": "안녕하세요", "Thank you": "감사합니다", "Goodbye": "안녕히 가세요"}
            
            >>> # Runtime override
            >>> result = translate.run(texts, target_lang="JP")
        """
        # Runtime override 적용
        if overrides:
            override_dict = KeyPathDict.to_nested_dict(overrides)
            working_policy = self.policy.model_copy(deep=True)
            policy_dict = working_policy.model_dump()
            kp_dict = KeyPathDict(policy_dict)
            kp_dict.merge(override_dict, deep=True, inplace=True)
            working_policy = TranslatePolicy(**kp_dict.data)
        else:
            working_policy = self.policy
        
        if not texts:
            self.log.warning("No texts to translate")
            return {}
        
        self.log.info(f"[Translate] Translating {len(texts)} texts")
        
        # SourcePayload 직접 생성 (policy.source 우회)
        payload = SourcePayload(texts=texts, source_path=None)
        
        # Pipeline 실행 (배치 번역 + 캐싱 자동 동작)
        # Runtime override 시 working_policy 사용, 없으면 self.pipeline 사용
        if overrides:
            # working_policy로 임시 pipeline 생성
            # Provider 생성
            temp_provider = ProviderFactory.create(
                provider_name=working_policy.provider.provider,
                api_key=None,  # Will use env var
                timeout=working_policy.provider.timeout
            )
            
            # Components 생성
            preprocessor = TextPreprocessor(working_policy.zh)
            cache = None
            if working_policy.store.save_db:
                default_dir = OSPath.downloads()
                cache = TranslationStorage(working_policy.store, default_dir=default_dir)
            
            writer = None
            if working_policy.store.save_tr:
                default_dir = OSPath.downloads()
                writer = TranslationResultWriter(working_policy.store, default_dir=default_dir)
            
            # 임시 pipeline 생성
            temp_pipeline = TranslationPipeline(
                policy=working_policy,
                provider=temp_provider,
                preprocessor=preprocessor,
                cache=cache,
                writer=writer,
                log=self.log
            )
            translations = temp_pipeline.run(payload)
            
            # 임시 provider 정리
            if hasattr(temp_provider, 'close'):
                temp_provider.close()
        else:
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
