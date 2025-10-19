# -*- coding: utf-8 -*-
"""cfg_utils.adapter.config
============================

Config - Core configuration loading logic (SRP-compliant).

책임:
1. 설정 소스 로드 및 KeyPathState 관리
2. env/env_os 처리
3. src 처리 및 state 병합
4. load() API 제공

이 클래스는 ConfigLoader(EntryPoint)와 분리되어 순수한 설정 로드 로직만 담당합니다.
Standalone 사용 + EntryPoint에서 위임 받는 겸용 Adapter입니다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from modules.keypath_utils import KeyPathState, KeyPathDict

if TYPE_CHECKING:
    from modules.logs_utils.core.policy import LogPolicy


class Config:
    """Core configuration service providing load() API.
    
    Standalone 사용 가능 + ConfigLoader에서 위임 받는 Adapter 역할 겸용.
    
    Attributes:
        state: KeyPathState 인스턴스
        source_policy: SourcePolicy 설정
        log: loguru logger 인스턴스
    """
    
    def __init__(
        self,
        *,
        source_policy: Optional[Any] = None,
        env: Optional[Any] = None,
        env_os: Optional[Union[bool, List[str]]] = None,
        log_policy: Optional[LogPolicy] = None,
    ):
        """Initialize Config with policies.
        
        Args:
            source_policy: SourcePolicy 인스턴스
            env: 환경 변수 소스
            env_os: OS 환경 변수 읽기
            log_policy: LogPolicy 인스턴스
        """
        self._state = KeyPathState(name="config")
        self._source_policy = source_policy
        self._log_policy = log_policy
        
        # Logger 초기화
        self._logger = None
        self._logger_initialized = False
        if log_policy is not None:
            self._init_logger()
        
        # env 처리 (가장 먼저!)
        if env is not None or (env_os is not None and env_os is not False):
            from ..services.env_processor import EnvProcessor
            env_processor = EnvProcessor(env=env, env_os=env_os)
            self._state = env_processor.process(self._state)
            
            if self._logger:
                self._logger.debug("Environment variables processed")
        
        # 정책 기본값 설정
        if self._source_policy is None:
            from ..core.policy import SourcePolicy
            self._source_policy = SourcePolicy()
    
    # ==========================================================================
    # Main API
    # ==========================================================================
    
    def load(self, src: Any) -> KeyPathState:
        """설정 소스 로드 및 state 반환.
        
        스크립트 레벨에서 동적으로 소스를 전달받아 처리합니다.
        
        ✅ env 처리: 환경 변수 자동 해석
        ✅ src 처리: YAML/dict/BaseModel 자동 판단
        ✅ List[SourcePolicy] 처리: 각 src별 정책 적용
        ✅ state 병합: KeyPathState로 통합
        ✅ 정규화: resolve_vars 지원
        
        Args:
            src: 소스 데이터
                - path, (path, section), tuple, BaseModel, dict
                - List[SourcePolicy]: 각 src별로 개별 정책 적용
        
        Returns:
            KeyPathState 인스턴스
        
        Example:
            >>> config = Config(source_policy=policy)
            >>> state = config.load(("config.yaml", "image"))
            >>> value = state.get("image__max_width")
            
            >>> # List[SourcePolicy] 처리
            >>> config = Config(source_policy=[policy1, policy2])
            >>> state = config.load([policy1, policy2])
        """
        if src is None:
            if self._logger:
                self._logger.warning("No source provided")
            return self._state
        
        # env section을 context로 추출
        env_context = self._state.to_dict().get("env", {}) if self._state else {}
        
        # List[SourcePolicy] 처리
        if isinstance(src, list) and len(src) > 0 and hasattr(src[0], 'src'):
            # List[SourcePolicy]: 각 SourcePolicy를 순차 처리
            if self._logger:
                self._logger.info(f"[Config] Loading {len(src)} sources with individual policies")
            
            for idx, source_policy in enumerate(src):
                if not hasattr(source_policy, 'src'):
                    continue
                
                if self._logger:
                    self._logger.debug(f"Processing SourcePolicy [{idx}]: {source_policy.src}")
                
                # 각 SourcePolicy의 src와 정책을 사용하여 처리
                self._process_single_source_with_policy(source_policy.src, source_policy, env_context)
        
        # Tuple src인 경우 (list source) 각각 개별 처리
        elif isinstance(src, tuple) and all(not isinstance(item, str) for item in src[:2]):
            # Multiple sources
            if self._logger:
                self._logger.info(f"[Config] Loading source: tuple ({len(src)} items)")
                self._logger.debug(f"Processing multiple sources: {len(src)} items")
            
            for idx, single_src in enumerate(src):
                if self._logger:
                    self._logger.debug(f"Processing source [{idx}]: {single_src}")
                
                self._process_single_source(single_src, env_context)
        else:
            # Single src 처리
            if self._logger:
                self._logger.info(f"[Config] Loading source: {type(src).__name__}")
            
            self._process_single_source(src, env_context)
        
        # 최종 정규화 (resolve_vars)
        # List[SourcePolicy]인 경우 첫 번째 정책 사용
        normalizer_policy = self._source_policy
        if isinstance(self._source_policy, list) and len(self._source_policy) > 0:
            normalizer_policy = self._source_policy[0]
        
        if normalizer_policy and normalizer_policy.yaml_normalizer and normalizer_policy.yaml_normalizer.resolve_vars:
            if self._logger:
                self._logger.debug("Final normalization (resolve_vars)")
            
            final_kpd = KeyPathDict(data=self._state.to_dict())
            resolved = final_kpd.resolve_all()
            self._state = KeyPathState(name="config", store=resolved.data)
        
        if self._logger:
            self._logger.success(f"[Config] Load completed")
        
        return self._state
    
    # ==========================================================================
    # Helper Methods
    # ==========================================================================
    
    def _process_single_source(self, src: Any, env_context: Dict[str, Any]) -> None:
        """단일 소스 처리.
        
        Args:
            src: 소스 데이터 (path, (path, section), BaseModel, dict 등)
            env_context: env 섹션 context
        """
        from ..core.policy import SourcePolicy
        from ..services.source import UnifiedSource
        
        if self._source_policy:
            # 기존 정책 복사 후 src와 context 설정
            source_policy_with_src = SourcePolicy(
                src=src,
                context=env_context,
                base_model_normalizer=self._source_policy.base_model_normalizer,
                base_model_merge=self._source_policy.base_model_merge,
                dict_normalizer=self._source_policy.dict_normalizer,
                dict_merge=self._source_policy.dict_merge,
                yaml_parser=self._source_policy.yaml_parser,
                yaml_normalizer=self._source_policy.yaml_normalizer,
                yaml_merge=self._source_policy.yaml_merge
            )
        else:
            source_policy_with_src = SourcePolicy(src=src, context=env_context)
        
        # UnifiedSource로 처리
        source = UnifiedSource(policy=source_policy_with_src)
        kpd = source.extract()
        
        # KeyPathState에 merge
        self._state.merge(kpd.data, deep=False)
    
    def _process_single_source_with_policy(
        self, 
        src: Any, 
        source_policy: Any, 
        env_context: Dict[str, Any]
    ) -> None:
        """개별 SourcePolicy를 사용하여 단일 소스 처리.
        
        List[SourcePolicy]의 각 item을 처리할 때 사용합니다.
        각 SourcePolicy의 개별 정책(yaml_parser, yaml_normalizer 등)을 적용합니다.
        
        Args:
            src: 소스 데이터 (path, (path, section), BaseModel, dict 등)
            source_policy: 해당 소스에 적용할 SourcePolicy
            env_context: env 섹션 context
        """
        from ..core.policy import SourcePolicy
        from ..services.source import UnifiedSource
        
        # 제공된 정책을 사용하되, src와 context를 업데이트
        source_policy_with_src = SourcePolicy(
            src=src,
            context=env_context,
            base_model_normalizer=source_policy.base_model_normalizer,
            base_model_merge=source_policy.base_model_merge,
            dict_normalizer=source_policy.dict_normalizer,
            dict_merge=source_policy.dict_merge,
            yaml_parser=source_policy.yaml_parser,
            yaml_normalizer=source_policy.yaml_normalizer,
            yaml_merge=source_policy.yaml_merge
        )
        
        # UnifiedSource로 처리
        source = UnifiedSource(policy=source_policy_with_src)
        kpd = source.extract()
        
        # KeyPathState에 merge
        self._state.merge(kpd.data, deep=False)
    
    def _init_logger(self) -> None:
        """로거 초기화 (LogManager 사용)."""
        if self._logger_initialized:
            return
        
        if self._log_policy is None:
            return
        
        try:
            from modules.logs_utils.services.manager import LogManager
            
            # LogPolicy 타입 검증 (duck typing)
            if self._log_policy.__class__.__name__ != "LogPolicy":
                import sys
                print(
                    f"Warning: log_policy must be LogPolicy instance, got {type(self._log_policy).__name__}. "
                    f"Logging disabled.",
                    file=sys.stderr
                )
                return
            
            # LogManager에게 위임
            log_manager = LogManager(
                self._log_policy,
                context={"config_id": id(self)}
            )
            
            self._logger = log_manager.logger
            self._logger_initialized = True
            
            self._logger.info(f"Config initialized with logger: {self._log_policy.name}")
            
        except ImportError as e:
            import sys
            print(
                f"Warning: Failed to initialize logger: {e}. "
                f"logs_utils may not be installed.",
                file=sys.stderr
            )
        except Exception as e:
            import sys
            print(
                f"Error: Failed to initialize logger: {e}",
                file=sys.stderr
            )
    
    # ==========================================================================
    # Property Access
    # ==========================================================================
    
    @property
    def state(self) -> KeyPathState:
        """Get current KeyPathState."""
        return self._state
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get value by KeyPath.
        
        Args:
            path: KeyPath (e.g., "image__max_width")
            default: Default value if not found
        
        Returns:
            Value at path or default
        """
        return self._state.get(path, default)
    
    def to_dict(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Export as dict.
        
        Args:
            section: Section name (None = entire state)
        
        Returns:
            Dict representation
        """
        from ..services.converter import StateConverter
        return StateConverter.to_dict(self._state, section=section)
    
    def to_model(
        self,
        model_class: Type[BaseModel],
        section: Optional[str] = None
    ) -> BaseModel:
        """Export as BaseModel.
        
        Args:
            model_class: BaseModel class
            section: Section name
        
        Returns:
            BaseModel instance
        """
        from ..services.converter import StateConverter
        return StateConverter.to_model(self._state, model_class, section=section)
    
    def __repr__(self) -> str:
        return f"Config(state={self._state.name})"
