# -*- coding: utf-8 -*-
"""cfg_utils.services.config_like_loader
========================================

ConfigLike 로더 - 모든 모듈의 공통 설정 로드 패턴.

모든 EntryPoint에서 반복되는 cfg_like 로드 로직을 통합합니다.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, TypeVar, Union

from pydantic import BaseModel

if TYPE_CHECKING:
    from cfg_utils import ConfigLoader

T = TypeVar('T', bound=BaseModel)


class ConfigLikeLoader:
    """ConfigLike 로드 유틸리티.
    
    모든 모듈의 EntryPoint에서 사용하는 공통 패턴:
    1. Policy 인스턴스 직접 전달 → 그대로 반환
    2. str/Path/dict/None → ConfigLoader로 로드
    3. overrides 적용
    4. BaseModel로 변환
    
    Examples:
        >>> # LogManager에서 사용
        >>> from logs_utils.core.policy import LogPolicy
        >>> policy = ConfigLikeLoader.load(
        ...     cfg_like="configs/log.yaml",
        ...     policy_class=LogPolicy,
        ...     default_config_filename="log.yaml"
        ... )
        
        >>> # Translator에서 사용
        >>> from translate_utils.core.policy import TranslatorPolicy
        >>> policy = ConfigLikeLoader.load(
        ...     cfg_like=None,  # 기본 파일 사용
        ...     policy_class=TranslatorPolicy,
        ...     default_config_filename="translator.yaml",
        ...     provider__target_lang="EN"  # override
        ... )
    """
    
    @staticmethod
    def load(
        cfg_like: Union[BaseModel, Path, str, dict, None],
        policy_class: Type[T],
        default_config_filename: Optional[str] = None,
        default_config_path: Optional[Union[str, Path]] = None,
        **overrides: Any
    ) -> T:
        """ConfigLike 소스에서 Policy 로드.
        
        Args:
            cfg_like: 설정 소스
                - BaseModel: Policy 인스턴스 (직접 전달)
                - str/Path: YAML 파일 경로
                - dict: 설정 딕셔너리
                - None: 기본 설정 파일 사용
            policy_class: Policy 클래스 (LogPolicy, TranslatorPolicy 등)
            default_config_filename: 기본 설정 파일 이름 (예: "log.yaml")
            default_config_path: 기본 설정 파일 전체 경로 (우선순위 높음)
            **overrides: 런타임 오버라이드 (KeyPath 형식)
        
        Returns:
            Policy 인스턴스
        
        Raises:
            ImportError: cfg_utils를 import할 수 없을 때
            ValueError: default_config_filename과 default_config_path 모두 None일 때
        """
        # 1. Policy 인스턴스가 직접 전달된 경우
        # Duck typing: 클래스 이름으로 체크 (import 경로 불일치 문제 해결)
        if cfg_like is not None and cfg_like.__class__.__name__ == policy_class.__name__:
            if overrides:
                return cfg_like.model_copy(update=overrides)
            return cfg_like
        
        # 2. ConfigLoader 사용
        from cfg_utils import ConfigLoader
        
        # Section 이름 (Policy 기본값에서 추출)
        section_name = policy_class().name
        
        # cfg_like가 None이면 기본 설정 파일 사용
        if cfg_like is None:
            if default_config_path is not None:
                src = (str(default_config_path), section_name)
            elif default_config_filename is not None:
                # 호출자의 parent.parent/configs/ 경로 사용
                # 하지만 여기서는 경로를 알 수 없으므로 에러
                raise ValueError(
                    "cfg_like=None일 때는 default_config_path를 명시해야 합니다. "
                    "또는 호출자가 직접 경로를 계산하여 cfg_like로 전달하세요."
                )
            else:
                raise ValueError(
                    "cfg_like=None일 때는 default_config_path 또는 "
                    "default_config_filename이 필요합니다."
                )
        else:
            # str/Path/dict 모두 동일하게 처리
            src = (cfg_like, section_name)
        
        # ConfigLoader로 로드
        loader = ConfigLoader(src=src)
        
        # overrides 적용
        if overrides:
            for key, value in overrides.items():
                loader.override(f"{section_name}__{key}", value)
        
        # Policy로 변환
        return loader.to_model(policy_class, section=section_name)  # type: ignore
    
    @staticmethod
    def load_with_caller_path(
        cfg_like: Union[BaseModel, Path, str, dict, None],
        policy_class: Type[T],
        caller_file: str,
        default_config_filename: str,
        **overrides: Any
    ) -> T:
        """호출자의 파일 경로를 기준으로 기본 설정 파일 자동 계산.
        
        이 메서드는 호출자가 __file__을 전달하면 자동으로
        parent.parent/configs/{filename} 경로를 계산합니다.
        
        Args:
            cfg_like: 설정 소스
            policy_class: Policy 클래스
            caller_file: 호출자의 __file__ (예: LogManager의 __file__)
            default_config_filename: 기본 설정 파일 이름 (예: "log.yaml")
            **overrides: 런타임 오버라이드
        
        Returns:
            Policy 인스턴스
        
        Examples:
            >>> # LogManager에서 사용
            >>> policy = ConfigLikeLoader.load_with_caller_path(
            ...     cfg_like=None,
            ...     policy_class=LogPolicy,
            ...     caller_file=__file__,  # manager.py의 __file__
            ...     default_config_filename="log.yaml"
            ... )
            >>> # 자동으로 logs_utils/configs/log.yaml 경로 계산
        """
        # 1. Policy 인스턴스가 직접 전달된 경우
        if cfg_like is not None and cfg_like.__class__.__name__ == policy_class.__name__:
            if overrides:
                return cfg_like.model_copy(update=overrides)
            return cfg_like
        
        # 2. cfg_like가 None이면 기본 경로 자동 계산
        if cfg_like is None:
            default_path = Path(caller_file).parent.parent / "configs" / default_config_filename
            cfg_like = str(default_path)
        
        # 3. ConfigLoader로 로드
        from cfg_utils import ConfigLoader
        
        section_name = policy_class().name
        src = (cfg_like, section_name)
        
        loader = ConfigLoader(src=src)
        
        # overrides 적용
        if overrides:
            for key, value in overrides.items():
                loader.override(f"{section_name}__{key}", value)
        
        # Policy로 변환
        return loader.to_model(policy_class, section=section_name)  # type: ignore


__all__ = ['ConfigLikeLoader']
