# -*- coding: utf-8 -*-
"""cfg_utils.entry_point.loader
================================

ConfigLoader - YAML 기반 설정 로드 EntryPoint.
Config adapter에 위임하여 실제 로드를 수행합니다.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from modules.keypath_utils import KeyPathState
from modules.data_utils.core.types import PathLike

from ..core.policy import ConfigLoaderPolicy
from ..adapter.config import Config

if TYPE_CHECKING:
    from modules.logs_utils.core.policy import LogPolicy


class ConfigLoader:
    """Configuration 로더 v3 - Config adapter 위임 패턴.
    
    YAML 기반 정책을 로드하고 Config adapter에 위임하여 설정을 처리합니다.
    
    주요 기능:
    - config_loader_cfg_path: YAML 정책 파일 로드
    - src: 소스 데이터 로드
    - env/env_os: 환경 변수 처리
    - Config adapter에 위임
    
    Examples:
        >>> # 1. YAML 정책 파일 사용
        >>> loader = ConfigLoader(
        ...     config_loader_cfg_path="config_loader.yaml"
        ... )
        >>> state = loader.get_state()
        
        >>> # 2. src 직접 지정
        >>> loader = ConfigLoader(
        ...     src=("config.yaml", "image")
        ... )
        >>> data = loader.to_dict(section="image")
        
        >>> # 3. Export
        >>> data = loader.to_dict()
        >>> policy = loader.to_model(ImagePolicy, section="image")
    """
    
    def __init__(
        self,
        config_loader_cfg_path: Optional[Union[str, Path, tuple[Union[str, Path], str]]] = None,
        *,
        policy: Optional[ConfigLoaderPolicy] = None,
        src: Optional[Any] = None,
        env: Optional[Union[str, List[str], PathLike, List[PathLike]]] = None,
        env_os: Optional[List[str]] = None,
        log: Optional[LogPolicy] = None,
    ):
        """ConfigLoader 초기화.
        
        정책 우선순위 (Cascade):
        1. config_loader_cfg_path: config_loader.yaml 로드
        2. policy 매개변수: ConfigLoaderPolicy 인스턴스
        3. 개별 매개변수 (src, log 등): 필드별 덮어쓰기
        
        Args:
            config_loader_cfg_path: ConfigLoader 정책 파일 경로
            policy: ConfigLoaderPolicy 인스턴스
            src: 소스 데이터
            env: 환경 변수 소스
            env_os: OS 환경 변수 읽기
            log: LogPolicy 인스턴스
        """
        # 0. env_os 먼저 처리 (log 정책의 placeholder 해석을 위해)
        self._env_context = {}
        if env_os is not None and env_os is not False:
            from ..services.env_os_loader import EnvOSLoader
            env_os_data = EnvOSLoader.load(env_os)
            # CASHOP_PATHS의 값(dict)을 flatten
            for key, value in env_os_data.items():
                if isinstance(value, dict):
                    self._env_context.update(value)
        
        # 1. YAML 정책 로드
        self.config_loader_cfg_path = config_loader_cfg_path
        self._loader_policy_dict: Optional[Dict[str, Any]] = None
        
        if self.config_loader_cfg_path is not None:
            from ..services.policy_loader import PolicyLoader
            # env_context를 전달하여 placeholder 해석
            self._loader_policy_dict = PolicyLoader.load_from_yaml(
                self.config_loader_cfg_path,
                placeholder_enabled=True if self._env_context else False,
                env_context=self._env_context
            )
            self._config_loader_policy = PolicyLoader.parse_to_policy(self._loader_policy_dict)
        else:
            self._config_loader_policy = None
        
        # 2. policy 매개변수로 덮어쓰기
        if policy is not None:
            self._config_loader_policy = policy
        
        # 3. 개별 정책 추출
        if self._config_loader_policy is not None:
            self._source_policy = self._config_loader_policy.source
            yaml_log_policy = self._config_loader_policy.log
        else:
            self._source_policy = None
            yaml_log_policy = None
        
        # 4. src 처리
        if src is not None:
            # 명시적으로 src가 주어진 경우 (우선순위 높음)
            self._final_src = src
        elif self._source_policy is not None:
            # YAML에서 로드된 SourcePolicy 사용
            if isinstance(self._source_policy, list):
                # List[SourcePolicy]: 각 policy의 src를 추출하여 list로 유지
                # Config adapter가 각각 처리할 수 있도록
                self._final_src = self._source_policy  # List[SourcePolicy] 그대로 전달
            elif isinstance(self._source_policy, BaseModel) and hasattr(self._source_policy, 'src'):
                # 단일 SourcePolicy: src 추출
                yaml_src = self._source_policy.src
                if isinstance(yaml_src, tuple) and len(yaml_src) == 1:
                    self._final_src = yaml_src[0]
                else:
                    self._final_src = yaml_src
            else:
                self._final_src = None
        else:
            self._final_src = None
        
        # 5. 로그 정책
        self._log_policy = log if log is not None else yaml_log_policy
        
        # 6. 기본값 설정
        if self._source_policy is None:
            from ..core.policy import SourcePolicy
            self._source_policy = SourcePolicy()
        
        # 7. Config adapter 생성
        self.config = Config(
            source_policy=self._source_policy,
            env=env,
            env_os=env_os,
            log_policy=self._log_policy
        )
        
        # 8. src 로드
        if self._final_src is not None:
            self.config.load(self._final_src)
    
    def get_state(self, name: Optional[str] = None) -> Union[KeyPathState, Any]:
        """KeyPathState 또는 section 데이터 반환.
        
        Args:
            name: section 이름 (None이면 전체 KeyPathState 반환)
        
        Returns:
            name이 None: KeyPathState 전체
            name이 지정됨: 해당 section의 데이터
        """
        if name is None:
            return self.config.state
        else:
            section_data = self.config.state.to_dict().get(name)
            if section_data is None:
                raise KeyError(f"Section '{name}' not found in state")
            return section_data
    
    def override(self, path: str, value: Any) -> ConfigLoader:
        """KeyPath로 값 override.
        
        Args:
            path: KeyPath (예: "image__max_width")
            value: 설정할 값
        
        Returns:
            Self for chaining
        """
        self.config.state.set(path, value)
        return self
    
    def to_keypath_state(self) -> KeyPathState:
        """KeyPathState로 export."""
        return self.config.state
    
    def to_dict(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Dict로 export."""
        return self.config.to_dict(section=section)
    
    def to_model(
        self,
        model_class: Type[BaseModel],
        section: Optional[str] = None
    ) -> BaseModel:
        """BaseModel로 export."""
        return self.config.to_model(model_class, section=section)

__all__ = ['ConfigLoader']
