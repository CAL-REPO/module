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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from modules.keypath_utils import KeyPathState, KeyPathDict
from modules.data_utils.core.types import PathLike

from ..core.policy import ConfigLoaderPolicy
from .converter import StateConverter
from .source import UnifiedSource, YamlFileSource

if TYPE_CHECKING:
    from modules.logs_utils.core.policy import LogPolicy


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
        src: Optional[Any] = None,
        env: Optional[Union[str, List[str], PathLike, List[PathLike]]] = None,
        env_os: Optional[Union[bool, List[str]]] = None,
        log: Optional[LogPolicy] = None,
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
            log: logs_utils.LogPolicy 인스턴스 (정책 필드 덮어쓰기)
                - LogPolicy(enabled=True, name="loader", level="INFO")
                - None: 로깅 비활성화
                
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
        # 🔥 1단계: 환경 변수 우선 설정 (가장 먼저!)
        self.env = env
        self.env_os = env_os
        
        # 2단계: env 처리 (state 생성)
        self._state = KeyPathState(name="config")
        
        if self.env is not None or (self.env_os is not None and self.env_os is not False):
            from .env_processor import EnvProcessor
            env_processor = EnvProcessor(env=self.env, env_os=self.env_os)
            self._state = env_processor.process(self._state)
        
        # 3단계: config_loader_cfg_path로 YAML 정책 로드 (env context 사용 가능)
        self.config_loader_cfg_path = config_loader_cfg_path
        self._loader_policy_dict: Optional[Dict[str, Any]] = None
        
        if self.config_loader_cfg_path is not None:
            self._loader_policy_dict = self._load_loader_policy()
            self._config_loader_policy = self._parse_loader_policy()
        else:
            self._config_loader_policy = None
        
        # 4단계: policy 매개변수로 정책 덮어쓰기
        if policy is not None:
            self._config_loader_policy = policy
        
        # 5단계: ConfigLoaderPolicy에서 개별 정책 추출
        if self._config_loader_policy is not None:
            self._source_policy = self._config_loader_policy.source
            self._keypath_policy = self._config_loader_policy.keypath
            yaml_log_policy = self._config_loader_policy.log
        else:
            self._source_policy = None
            self._keypath_policy = None
            yaml_log_policy = None
        
        # 6단계: src 파라미터 처리
        # 우선순위: src 파라미터 > ConfigLoaderPolicy.source.src > None
        if src is not None:
            # src 파라미터가 명시적으로 전달됨
            self._final_src = src
        elif self._source_policy is not None and self._source_policy.src is not None:
            # config_loader_cfg_path에서 source.src 추출
            yaml_src = self._source_policy.src
            
            # src가 단일 소스를 담은 튜플인 경우: ((path, section),) → (path, section)
            if isinstance(yaml_src, tuple) and len(yaml_src) == 1:
                self._final_src = yaml_src[0]
            else:
                self._final_src = yaml_src
        else:
            self._final_src = None
        
        # 7단계: 로그 정책
        self._log_policy = log if log is not None else yaml_log_policy
        
        # 6단계: 정책 기본값 설정
        if self._source_policy is None:
            from ..core.policy import SourcePolicy
            self._source_policy = SourcePolicy()

        # Section 추적
        self._base_sections: set = set()
        
        # KeyPath State는 이미 Line 147에서 초기화됨!
        # self._state: Optional[KeyPathState] = None  ← 삭제!
        
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
        1. src 처리: UnifiedSource로 통합 처리
        2. env + env_os: 환경 변수 통합 처리
        3. 최종 정규화
        """
        from .source import UnifiedSource
        from .env_processor import EnvProcessor
        
        # 로깅 시작
        if self._logger:
            self._logger.info("ConfigLoader._load() started")
        
        # NOTE: env + env_os는 이미 __init__에서 처리됨 (self._state 생성됨)
        
        # 1단계: src 처리 (env placeholder 이미 resolved)
        if self._final_src is not None:
            if self._logger:
                self._logger.debug(f"Processing src: {type(self._final_src).__name__}")
            
            # SourcePolicy에 src 주입 및 처리
            from ..core.policy import SourcePolicy
            
            # env section을 context로 추출
            env_context = self._state.to_dict().get("env", {}) if self._state else {}
            
            # Tuple src인 경우 (list source의 경우) 각각 개별 처리
            if isinstance(self._final_src, tuple):
                if self._logger:
                    self._logger.debug(f"Processing multiple sources: {len(self._final_src)} items")
                
                for idx, single_src in enumerate(self._final_src):
                    if self._logger:
                        self._logger.debug(f"Processing source [{idx}]: {single_src}")
                    
                    self._process_single_source(single_src, env_context)
            else:
                # Single src 처리
                self._process_single_source(self._final_src, env_context)
        
        # 3단계: 최종 정규화 (resolve_vars)
        if self._logger:
            self._logger.debug("Final normalization (resolve_vars)")
        
        if self._source_policy and self._source_policy.yaml_normalizer and self._source_policy.yaml_normalizer.resolve_vars:
            final_kpd = KeyPathDict(data=self._state.to_dict())
            resolved = final_kpd.resolve_all()
            self._state = KeyPathState(name="config", store=resolved.data)
        
        # 로깅 완료
        if self._logger:
            self._logger.info("ConfigLoader._load() completed")
    
    def _process_single_source(self, src: Any, env_context: Dict[str, Any]) -> None:
        """단일 소스 처리 (중복 제거용 헬퍼 메서드).
        
        Args:
            src: 소스 데이터 (path, (path, section), BaseModel, dict 등)
            env_context: env 섹션 context
        """
        from ..core.policy import SourcePolicy
        from .source import UnifiedSource
        
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
        
        # YAML 파일 로드 (placeholder 해석 비활성화 - env 없음)
        from ..core.policy import SourcePolicy
        from modules.structured_io.core.policy import BaseParserPolicy
        
        # Placeholder 해석 비활성화 (env가 아직 없어서 빈 문자열로 해석됨)
        from ..core.policy import NormalizePolicy
        
        yaml_policy = SourcePolicy(
            src=file_path,
            yaml_parser=BaseParserPolicy(
                safe_mode=True,
                encoding="utf-8",
                enable_env=False,
                enable_include=True,
                enable_placeholder=False,  # ← 비활성화!
                enable_reference=False
            ),
            yaml_normalizer=NormalizePolicy(
                normalize_keys=True,
                drop_blanks=False,
                resolve_vars=False  # ← 비활성화!
            )
        )
        source = YamlFileSource(file_path, section=section, policy=yaml_policy)
        kpd = source.extract()
        
        return kpd.data
    
    def _parse_loader_policy(self):
        """ConfigLoader 정책 파싱.
        
        ConfigLoaderPolicy는 3개 필드를 YAML에서 로드합니다:
        - source: SourcePolicy (단일) 또는 List[SourcePolicy] (다중 src 지원)
        - keypath: KeyPathStatePolicy
        - log: LogPolicy
        
        Returns:
            ConfigLoaderPolicy 또는 None
        """
        if self._loader_policy_dict is None:
            return None
        
        try:
            from ..core.policy import ConfigLoaderPolicy, SourcePolicy
            from modules.keypath_utils.core.policy import KeyPathStatePolicy
            
            # 1. source 파싱 (list 또는 dict 지원)
            source_data = self._loader_policy_dict.get("source", {})
            
            if isinstance(source_data, list):
                # List[dict]: 각 dict를 SourcePolicy로 변환 후 src 추출하여 병합
                all_srcs = []
                base_source_policy = None
                
                for item in source_data:
                    if not isinstance(item, dict):
                        continue
                    
                    # 각 item을 SourcePolicy로 변환
                    item_policy = SourcePolicy(**item)
                    
                    # src 추출
                    if item_policy.src is not None:
                        all_srcs.append(item_policy.src)
                    
                    # 첫 번째 item의 정책을 base로 사용
                    if base_source_policy is None:
                        base_source_policy = item_policy
                
                # 모든 src를 병합하여 하나의 SourcePolicy로
                if base_source_policy and all_srcs:
                    # src를 tuple로 병합
                    merged_src = tuple(all_srcs) if len(all_srcs) > 1 else all_srcs[0]
                    source = SourcePolicy(
                        src=merged_src,
                        base_model_normalizer=base_source_policy.base_model_normalizer,
                        base_model_merge=base_source_policy.base_model_merge,
                        dict_normalizer=base_source_policy.dict_normalizer,
                        dict_merge=base_source_policy.dict_merge,
                        yaml_parser=base_source_policy.yaml_parser,
                        yaml_normalizer=base_source_policy.yaml_normalizer,
                        yaml_merge=base_source_policy.yaml_merge
                    )
                else:
                    source = None
            elif isinstance(source_data, dict):
                # dict: 단일 SourcePolicy
                source = SourcePolicy(**source_data) if source_data else None
            else:
                source = None
            
            # 2. keypath 파싱
            keypath_dict = self._loader_policy_dict.get("keypath", {})
            keypath = KeyPathStatePolicy(**keypath_dict) if keypath_dict else None
            
            # 3. log 파싱 (별도 메서드 사용)
            log = self._parse_log_policy()
            
            # ConfigLoaderPolicy 생성
            if source is None:
                source = SourcePolicy()  # 기본 정책 사용
            
            return ConfigLoaderPolicy(
                source=source,
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
            
            # LogPolicy 타입 검증 (duck typing - 클래스 이름으로 체크)
            if self._log_policy.__class__.__name__ != "LogPolicy":
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
    
    def get_state(self, name: Optional[str] = None) -> Union[KeyPathState, Any]:
        """내부 KeyPathState 또는 section 데이터 반환.
        
        Args:
            name: section 이름 (None이면 전체 KeyPathState 반환)
        
        Returns:
            name이 None: KeyPathState 전체
            name이 지정됨: 해당 section의 데이터 (dict 또는 BaseModel)
        
        Examples:
            >>> loader = ConfigLoader(...)
            >>> state = loader.get_state()  # 전체
            >>> log_policy = loader.get_state(name="default")  # section만
        """
        if self._state is None:
            raise RuntimeError("ConfigLoader not initialized")
        
        if name is None:
            # 전체 KeyPathState 반환
            return KeyPathState(
                name=self._state.name,
                store=self._state.store,
                policy=self._state.policy
            )
        else:
            # section 데이터만 반환
            section_data = self._state.to_dict().get(name)
            if section_data is None:
                raise KeyError(f"Section '{name}' not found in state")
            return section_data
    
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
