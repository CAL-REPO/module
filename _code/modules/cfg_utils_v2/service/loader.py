# -*- coding: utf-8 -*-
"""cfg_utils_v2.service.config_loader
======================================

ConfigLoader v3 - KeyPath State 기반 설계.

책임:
- base_sources와 override_sources를 KeyPath State로 변환
- Section별 KeyPath State 관리
- State 기반 Merge 및 Override 처리
- Export: KeyPathState / Dict / BaseModel

핵심 프로세스:
1. base_sources (Policy) → KeyPathState → Merge
2. override_sources (Data) → KeyPathState → Normalize → Override to base
3. Export: to_keypath_state() / to_dict() / to_model()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from modules.keypath_utils import KeyPathState, KeyPathDict
from modules.data_utils.core.types import (
    PathLike,
    ConfigSourceWithSection,
)

from ..core.policy import ConfigLoaderPolicy
from .converter import StateConverter
from .source import (
    BaseModelSource,
    DictSource,
    YamlFileSource,
)


class ConfigLoader:
    """Configuration 로더 v3 - KeyPath State 기반.
    
    KeyPath State를 활용하여 유연한 설정 관리를 제공합니다.
    
    주요 기능:
    - base_sources: Policy 모델들을 base로 사용
    - override_sources: 데이터 소스들로 base를 override
    - Section별 독립적 관리
    - State 기반 동적 변경 가능
    
    Examples:
        >>> # 1. BaseModel policy를 base로 사용
        >>> loader = ConfigLoader(
        ...     base_sources=[
        ...         (ImagePolicy(), "image"),
        ...         (OcrPolicy(), "ocr")
        ...     ]
        ... )
        >>> state = loader.get_state()
        >>> state.get("image__max_width")
        1024  # ImagePolicy 기본값
        
        >>> # 2. Override sources 추가 (Dict, YAML Path 자동 판단)
        >>> loader = ConfigLoader(
        ...     base_sources=[(ImagePolicy(), "image")],
        ...     override_sources=[
        ...         ("config.yaml", "image"),        # YAML Path
        ...         ({"max_width": 2048}, "image")   # Dict
        ...     ]
        ... )
        >>> state = loader.get_state()
        >>> state.get("image__max_width")
        2048  # Override됨
        
        >>> # 3. Export
        >>> data = loader.to_dict()  # 전체 dict
        >>> data = loader.to_dict(section="image")  # section만
        >>> policy = loader.to_model(ImagePolicy, section="image")
    """
    
    def __init__(
        self,
        config_loader_cfg_path: Optional[Union[str, Path, tuple[Union[str, Path], str]]] = None,
        *,
        policy: Optional[ConfigLoaderPolicy] = None,
        base_sources: Optional[ConfigSourceWithSection] = None,
        override_sources: Optional[ConfigSourceWithSection] = None,
        env: Optional[Union[str, List[str], PathLike, List[PathLike]]] = None,
        env_os: Optional[Union[bool, List[str]]] = None,
        log: Optional[Any] = None,  # LogPolicy, 런타임에 타입 검증
    ):
        """ConfigLoader 초기화.
        
        정책 우선순위 (Cascade):
        1. config_loader_cfg_path → config_loader.yaml 로드 (기본 정책)
        2. policy 매개변수 → ConfigLoaderPolicy 인스턴스 (YAML 정책 덮어쓰기)
        3. 개별 매개변수 (base_sources, log 등) → 필드별 덮어쓰기
        
        Args:
            config_loader_cfg_path: ConfigLoader 정책 파일 경로
                - str/Path: YAML 파일 경로 (전체 로드)
                - tuple[str/Path, str]: (파일 경로, section) 튜플
                - None: 기본 정책 사용
            policy: ConfigLoaderPolicy 인스턴스 (YAML 정책 전체 덮어쓰기)
            base_sources: BaseModel 소스 리스트 (정책 필드 덮어쓰기)
            override_sources: Override 소스 리스트 (정책 필드 덮어쓰기)
            env: 환경 변수 소스 (정책 필드 덮어쓰기)
            env_os: OS 환경 변수 읽기 (정책 필드 덮어쓰기)
            log: LogPolicy 인스턴스 (정책 필드 덮어쓰기)
                
        Examples:
            >>> # 1. YAML 정책 파일만
            >>> loader = ConfigLoader(
            ...     config_loader_cfg_path="config_loader.yaml"
            ... )
            
            >>> # 2. YAML + Policy 인스턴스 덮어쓰기
            >>> loader = ConfigLoader(
            ...     config_loader_cfg_path="config_loader.yaml",
            ...     policy=ConfigLoaderPolicy(
            ...         base_sources=[(ImagePolicy(), "image")],
            ...         log=True
            ...     )
            ... )
            
            >>> # 3. YAML + 개별 매개변수 덮어쓰기
            >>> loader = ConfigLoader(
            ...     config_loader_cfg_path="config_loader.yaml",
            ...     base_sources=[(ImagePolicy(), "image")],
            ...     log=LogPolicy(enabled=True, name="my_loader")
            ... )
            
            >>> # 4. Policy 인스턴스만
            >>> loader = ConfigLoader(
            ...     policy=ConfigLoaderPolicy(
            ...         base_sources=[(ImagePolicy(), "image")],
            ...         override_sources=[("config.yaml", "image")]
            ...     )
            ... )
        """
        # 1단계: config_loader_cfg_path로 YAML 정책 로드
        self.config_loader_cfg_path = config_loader_cfg_path
        self._loader_policy_dict: Optional[Dict[str, Any]] = None
        
        if self.config_loader_cfg_path is not None:
            self._loader_policy_dict = self._load_loader_policy()
            self._config_loader_policy = self._parse_loader_policy()
        else:
            self._config_loader_policy = None
        
        # 2단계: policy 매개변수로 정책 덮어쓰기
        if policy is not None:
            self._config_loader_policy = policy
        
        # 3단계: ConfigLoaderPolicy에서 개별 정책 추출
        if self._config_loader_policy is not None:
            self._normalizer_policy = self._config_loader_policy.normalizer
            self._merge_policy = self._config_loader_policy.merge
            self._yaml_parser_policy = self._config_loader_policy.yaml_parser
            self._keypath_policy = self._config_loader_policy.keypath
            yaml_log_policy = self._config_loader_policy.log
        else:
            self._normalizer_policy = None
            self._merge_policy = None
            self._yaml_parser_policy = None
            self._keypath_policy = None
            yaml_log_policy = None
        
        # 4단계: 개별 매개변수로 소스 설정
        # ⚠️ base_sources, override_sources, env, env_os는 Python 코드에서만 전달
        self.base_sources = base_sources or []
        self.override_sources = override_sources or []
        self.env = env
        self.env_os = env_os
        self._log_policy = log if log is not None else yaml_log_policy
        
        # 5단계: 정책 기본값 설정
        if self._normalizer_policy is None:
            from ..core.policy import NormalizePolicy
            self._normalizer_policy = NormalizePolicy(
                normalize_keys=False,
                drop_blanks=False,
                resolve_vars=True
            )
        
        if self._merge_policy is None:
            from ..core.policy import MergePolicy
            self._merge_policy = MergePolicy(
                deep=False,
                overwrite=True
            )
        
        if self._yaml_parser_policy is None:
            from ..core.policy import YamlParserPolicy
            self._yaml_parser_policy = YamlParserPolicy(
                encoding="utf-8",
                safe_mode=True
            )
        
        if self._keypath_policy is None:
            from ..core.policy import KeyPathPolicy
            self._keypath_policy = KeyPathPolicy(
                separator="__",
                override_requires_base=True
            )
        
        # Section 추적 (BaseModel에 정의된 sections)
        self._base_sections: set = set()
        
        # KeyPath State (내부 상태)
        self._state: Optional[KeyPathState] = None
        
        # 로거 초기화
        self._logger = None
        self._logger_initialized = False
        if self._log_policy is not None:
            self._init_logger()
        
        # Load 수행
        self._load()
    
    def _load(self) -> None:
        """Load 프로세스 수행.
        
        프로세스:
        1. base_sources: BaseModel 우선 처리 → Normalize key → Merge → Section 추적
        2. override_sources: 타입 자동 판단 → Section 중복 확인 → 조건별 처리
        3. env + env_os: 환경 변수 통합 처리 → env section 자동 생성 → 무조건 merge
        4. 최종 Resolve_vars
        """
        from modules.keypath_utils import KeyPathMerger, KeyPathMergePolicy
        from .override_processor import OverrideProcessor
        from .env_processor import EnvProcessor
        
        # 로깅 시작
        if self._logger:
            self._logger.info("ConfigLoader._load() started")
        
        # 초기화
        self._state = KeyPathState(name="config")
        self._base_sections = set()
        
        # 1단계: base_sources 처리 (Source에서 이미 정규화됨)
        if self._logger:
            self._logger.debug(f"Processing base_sources: {len(self.base_sources)} items")
        
        for source_item in self.base_sources:
            kpd, section = self._extract_source(source_item, source_type="base")
            
            # Section 추적
            if section:
                self._base_sections.add(section)
                if self._logger:
                    self._logger.debug(f"Base section added: {section}")
            
            # Merge (shallow) - Source에서 이미 정규화되었으므로 그대로 사용
            self._state.merge(kpd.data, deep=False)
        
        # 2단계: override_sources 처리 (Source에서 이미 정규화됨)
        if self._logger:
            self._logger.debug(f"Processing override_sources: {len(self.override_sources)} items")
        
        # override_requires_base 정책 확인 (keypath 정책에서)
        override_requires_base = True
        if self._config_loader_policy is not None and self._config_loader_policy.keypath is not None:
            override_requires_base = self._config_loader_policy.keypath.override_requires_base
        
        override_processor = OverrideProcessor(
            base_sections=self._base_sections,
            require_base=override_requires_base
        )
        for source_item in self.override_sources:
            kpd, section = self._extract_source(source_item, source_type="override")
            # Source에서 이미 정규화되었으므로 그대로 사용
            self._state = override_processor.process(self._state, kpd, section)
        
        # 3단계: env + env_os 통합 처리
        if self.env is not None or (self.env_os is not None and self.env_os is not False):
            if self._logger:
                self._logger.debug("Processing env + env_os")
            
            env_processor = EnvProcessor(env=self.env, env_os=self.env_os)
            self._state = env_processor.process(self._state)
        
        # 4단계: 최종 정규화 (resolve_vars)
        if self._logger:
            self._logger.debug("Final normalization (resolve_vars)")
        
        if self._normalizer_policy and self._normalizer_policy.resolve_vars:
            final_kpd = KeyPathDict(data=self._state.to_dict())
            resolved = final_kpd.resolve_all()
            self._state = KeyPathState(name="config", store=resolved.data)
        
        # 로깅 완료
        if self._logger:
            self._logger.info("ConfigLoader._load() completed")
    
    def _load_loader_policy(self) -> Dict[str, Any]:
        """ConfigLoader 정책 파일 로드.
        
        Returns:
            정책 dict
            
        Raises:
            FileNotFoundError: 파일 없음
            ValueError: 잘못된 형식
        """
        if self.config_loader_cfg_path is None:
            return {}
        
        # Tuple (파일 경로, section) 처리
        if isinstance(self.config_loader_cfg_path, tuple) and len(self.config_loader_cfg_path) == 2:
            file_path, section = self.config_loader_cfg_path
            file_path = Path(file_path)
        else:
            # str/Path (파일 경로만)
            file_path = Path(self.config_loader_cfg_path)
            section = None
        
        # 파일 존재 확인
        if not file_path.exists():
            raise FileNotFoundError(
                f"ConfigLoader policy file not found: {file_path}"
            )
        
        # YAML 파일 로드
        source = YamlFileSource(file_path, section=section)
        kpd = source.extract()
        
        return kpd.data
    
    def _parse_loader_policy(self):
        """ConfigLoader 정책 파싱.
        
        ConfigLoaderPolicy는 5개 필드를 YAML에서 로드합니다:
        - normalizer, merge, yaml_parser, keypath, log
        
        Returns:
            ConfigLoaderPolicy 또는 None
        """
        if self._loader_policy_dict is None:
            return None
        
        try:
            from ..core.policy import (
                ConfigLoaderPolicy,
                NormalizePolicy,
                MergePolicy,
                YamlParserPolicy,
                KeyPathPolicy
            )
            
            # 1. normalizer 파싱
            normalizer_dict = self._loader_policy_dict.get("normalizer", {})
            normalizer = NormalizePolicy(**normalizer_dict) if normalizer_dict else None
            
            # 2. merge 파싱
            merge_dict = self._loader_policy_dict.get("merge", {})
            merge = MergePolicy(**merge_dict) if merge_dict else None
            
            # 3. yaml_parser 파싱
            yaml_parser_dict = self._loader_policy_dict.get("yaml_parser", {})
            yaml_parser = YamlParserPolicy(**yaml_parser_dict) if yaml_parser_dict else None
            
            # 4. keypath 파싱
            keypath_dict = self._loader_policy_dict.get("keypath", {})
            keypath = KeyPathPolicy(**keypath_dict) if keypath_dict else None
            
            # 5. log 파싱 (별도 메서드 사용)
            log = self._parse_log_policy()
            
            # ConfigLoaderPolicy 생성
            return ConfigLoaderPolicy(
                normalizer=normalizer,
                merge=merge,
                yaml_parser=yaml_parser,
                keypath=keypath,
                log=log
            )
        except Exception as e:
            import sys
            print(
                f"Warning: Failed to parse ConfigLoaderPolicy: {e}. Using default policy.",
                file=sys.stderr
            )
            return None
    
    def _parse_log_policy(self):
        """Log 정책 파싱.
        
        Returns:
            LogPolicy 또는 None
        """
        if self._loader_policy_dict is None:
            return None
        
        log_policy_dict = self._loader_policy_dict.get("log", {})
        if not log_policy_dict:
            return None
        
        try:
            from modules.logs_utils.core.policy import LogPolicy
            return LogPolicy(**log_policy_dict)
        except Exception as e:
            import sys
            print(
                f"Warning: Failed to parse LogPolicy: {e}. Logging disabled.",
                file=sys.stderr
            )
            return None
    
    def _init_logger(self) -> None:
        """로거 초기화 (LogManager 사용).
        
        logs_utils.LogManager에게 로거 초기화를 위임합니다.
        - LogPolicy 인스턴스를 LogManager에 전달
        - LogManager가 loguru 설정, context binding, filter 등 처리
        - ConfigLoader는 bind된 logger만 받아서 사용
        
        Note: 기존 150줄 코드 → 10줄로 간소화 (코드 중복 제거)
        """
        if self._logger_initialized:
            return
        
        if self._log_policy is None:
            return
        
        try:
            from modules.logs_utils.services.manager import LogManager
            from modules.logs_utils.core.policy import LogPolicy
            
            # LogPolicy 타입 검증
            if not isinstance(self._log_policy, LogPolicy):
                import sys
                print(
                    f"Warning: log parameter must be LogPolicy instance, got {type(self._log_policy).__name__}. "
                    f"Logging disabled.",
                    file=sys.stderr
                )
                return
            
            # LogManager에게 위임 (context 자동 추가)
            log_manager = LogManager(
                self._log_policy,
                context={
                    "loader_id": id(self),
                    "config_path": str(self.config_loader_cfg_path) if self.config_loader_cfg_path else None,
                }
            )
            
            # Bind된 logger만 받음
            self._logger = log_manager.logger
            self._logger_initialized = True
            
            self._logger.info(f"ConfigLoader initialized with logger: {self._log_policy.name}")
            
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
    

    
    def _extract_source(
        self,
        source_item: Any,
        source_type: str
    ) -> tuple[KeyPathDict, Optional[str]]:
        """소스에서 KeyPathDict 추출 (정책 전달).
        
        정책 전달 방식:
        1. Source가 이미 생성된 경우 (ConfigSource 인스턴스):
           → Source 자체 정책 사용
        2. 개별 정책 지정 (SourcePolicy, data, section):
           → 개별 SourcePolicy 사용
        3. 전역 정책 사용 (data, section):
           → ConfigLoader 전역 정책 사용
        
        Args:
            source_item: 소스 아이템
                - ConfigSource: 이미 생성된 Source 인스턴스
                - (SourcePolicy, data, section): 개별 정책 + 데이터 + section 튜플
                - (data, section): 데이터와 section 튜플 (전역 정책 사용)
                - data: 데이터만 (section 없음, 전역 정책 사용)
            source_type: 소스 타입 힌트 ("base" or "override") - 로깅용
        
        Returns:
            (KeyPathDict, section) 튜플
            
        Raises:
            TypeError: base_sources에 BaseModel이 아닌 타입이 전달된 경우
        
        Examples:
            >>> # 패턴 1: 전역 정책 사용
            >>> base_sources = [(ImagePolicy(), "image")]
            
            >>> # 패턴 2: 개별 정책 사용
            >>> custom_policy = SourcePolicy(normalizer=NormalizePolicy(normalize_keys=True))
            >>> base_sources = [(custom_policy, ImagePolicy(), "image")]
            
            >>> # 패턴 3: YAML 파일 + 개별 정책
            >>> yaml_policy = SourcePolicy(yaml_parser=YamlParserPolicy(safe_mode=False))
            >>> override_sources = [(yaml_policy, "config.yaml", "image")]
        """
        from .source import ConfigSource
        from ..core.policy import SourcePolicy
        
        # None 처리
        if source_item is None:
            return KeyPathDict(data={}), None
        
        # Tuple 처리: 3가지 패턴
        custom_policy = None
        if isinstance(source_item, tuple):
            if len(source_item) == 3:
                # 패턴: (SourcePolicy, data, section)
                first, second, third = source_item
                if isinstance(first, SourcePolicy):
                    custom_policy = first
                    data = second
                    section = third
                else:
                    # 잘못된 형태
                    raise ValueError(
                        f"Invalid source_item format: 3-tuple must be (SourcePolicy, data, section). "
                        f"Got ({type(first).__name__}, {type(second).__name__}, {type(third).__name__})"
                    )
            elif len(source_item) == 2:
                # 패턴: (data, section) - 전역 정책 사용
                data, section = source_item
            else:
                raise ValueError(
                    f"Invalid source_item format: tuple must be (data, section) or (SourcePolicy, data, section). "
                    f"Got {len(source_item)}-tuple"
                )
        else:
            # 패턴: data만 (section 없음)
            data = source_item
            section = None
        
        # 이미 생성된 Source 인스턴스
        if isinstance(data, ConfigSource):
            return data.extract(), section
        
        # 정책 결정: 개별 정책 우선, 없으면 전역 정책
        if custom_policy:
            policy = custom_policy
            if self._logger:
                self._logger.debug(f"[{source_type.upper()}] Using custom SourcePolicy")
        else:
            # 전역 정책으로 SourcePolicy 생성
            from ..core.policy import SourcePolicy
            policy = SourcePolicy(
                normalizer=self._normalizer_policy,
                merge=self._merge_policy,
                yaml_parser=self._yaml_parser_policy
            )
            if self._logger:
                self._logger.debug(f"[{source_type.upper()}] Using global SourcePolicy")
        
        # base_sources 타입 제한 (정책 기반)
        if source_type == "base":
            # base_sources는 BaseModel만 허용
            if not isinstance(data, BaseModel):
                raise TypeError(
                    f"base_sources only accepts BaseModel instances. "
                    f"Got {type(data).__name__}. "
                    f"BaseModel provides default values and type validation. "
                    f"Use override_sources for Dict or YAML files."
                )
            
            # BaseModel 처리
            if isinstance(data, BaseModel):
                source = BaseModelSource(
                    data,
                    section=section,
                    policy=policy
                )
                return source.extract(), section
            
            # any 정책: Dict/YAML도 허용
            if isinstance(data, dict):
                source = DictSource(
                    data,
                    section=section,
                    policy=policy
                )
                return source.extract(), section
            
            if isinstance(data, (str, Path)):
                source = YamlFileSource(
                    data,
                    section=section,
                    policy=policy
                )
                return source.extract(), section
            
            raise TypeError(
                f"Unsupported base_sources type: {type(data)}. "
                f"Expected BaseModel, dict, or str/Path (YAML file)."
            )
        
        # override_sources는 타입 자동 판단 (policy 이미 결정됨)
        
        # 1. BaseModel → KeyPathDict
        if isinstance(data, BaseModel):
            source = BaseModelSource(
                data,
                section=section,
                policy=policy
            )
            return source.extract(), section
        
        # 2. Dict → KeyPathDict
        if isinstance(data, dict):
            source = DictSource(
                data,
                section=section,
                policy=policy
            )
            return source.extract(), section
        
        # 3. Path-like (YAML 파일) → KeyPathDict
        if isinstance(data, (str, Path)):
            source = YamlFileSource(
                data,
                section=section,
                policy=policy
            )
            return source.extract(), section
        
        raise TypeError(
            f"Unsupported source type: {type(data)}. "
            f"Expected BaseModel, dict, or str/Path (YAML file)."
        )
    
    def get_state(self) -> KeyPathState:
        """내부 KeyPathState 반환.
        
        Returns:
            KeyPathState (복사본)
        
        Examples:
            >>> loader = ConfigLoader(...)
            >>> state = loader.get_state()
            >>> state.get("image__max_width")
        """
        if self._state is None:
            raise RuntimeError("ConfigLoader not initialized")
        
        # Copy state to prevent external modification
        return KeyPathState(
            name=self._state.name,
            store=self._state.store,
            policy=self._state.policy
        )
    
    def override(self, path: str, value: Any) -> ConfigLoader:
        """KeyPath로 값 override.
        
        Args:
            path: KeyPath (예: "image.max_width")
            value: 설정할 값
        
        Returns:
            Self for chaining
        
        Examples:
            >>> loader = ConfigLoader(...)
            >>> loader.override("image__max_width", 2048)
            >>> loader.get_state().get("image__max_width")
            2048
        """
        if self._state is None:
            raise RuntimeError("ConfigLoader not initialized")
        
        self._state.set(path, value)
        return self
    
    def to_keypath_state(self) -> KeyPathState:
        """KeyPathState로 export.
        
        Returns:
            KeyPathState
        """
        return self.get_state()
    
    def to_dict(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Dict로 export.
        
        Args:
            section: 추출할 section (없으면 전체)
        
        Returns:
            Dict
        
        Examples:
            >>> loader = ConfigLoader(...)
            >>> loader.to_dict()
            {'image': {'max_width': 1024}, 'ocr': {...}}
            
            >>> loader.to_dict(section="image")
            {'max_width': 1024}
        """
        return StateConverter.to_dict(self.get_state(), section=section)
    
    def to_model(
        self,
        model_class: Type[BaseModel],
        section: Optional[str] = None
    ) -> BaseModel:
        """BaseModel로 export.
        
        Args:
            model_class: BaseModel 클래스
            section: 추출할 section
        
        Returns:
            BaseModel 인스턴스
        
        Examples:
            >>> loader = ConfigLoader(...)
            >>> policy = loader.to_model(ImagePolicy, section="image")
            >>> policy.max_width
            1024
        """
        return StateConverter.to_model(
            self.get_state(),
            model_class,
            section=section
        )
