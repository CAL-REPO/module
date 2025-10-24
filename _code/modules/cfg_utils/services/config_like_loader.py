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
    
    모든 모듈의 EntryPoint/Adapter에서 사용하는 공통 패턴:
    1. Policy 인스턴스 직접 전달 → 그대로 반환
    2. str/Path/dict → ConfigLoader로 로드
    3. None → YAML 파일 있으면 로드, 없으면 Pydantic 기본값 사용
    4. overrides 적용
    5. BaseModel로 변환
    
    Examples:
        >>> # LogManager에서 사용
        >>> from logs_utils.core.policy import LogPolicy
        >>> policy = ConfigLikeLoader.load(
        ...     cfg_like=None,  # YAML 없으면 Pydantic 기본값
        ...     policy_class=LogPolicy,
        ...     module_file=__file__,
        ...     config_filename="log.yaml"
        ... )
        
        >>> # Translator에서 사용 (overrides 포함)
        >>> from translate_utils.core.policy import TranslatorPolicy
        >>> policy = ConfigLikeLoader.load(
        ...     cfg_like=None,
        ...     policy_class=TranslatorPolicy,
        ...     module_file=__file__,
        ...     config_filename="translator.yaml",
        ...     provider__target_lang="EN"  # override
        ... )
    """
    
    @staticmethod
    def load(
        cfg_like: Union[BaseModel, Path, str, dict, None],
        policy_class: Type[T],
        module_file: str,
        config_filename: str,
        **overrides: Any
    ) -> T:
        """Load Policy from cfg_like or use Pydantic default values.
        
        cfg_like=None일 때:
        1. 기본 경로 계산: Path(module_file).parent.parent / "configs" / config_filename
        2. 파일 존재 → YAML에서 로드
        3. 파일 없음 → Pydantic 기본값 사용
        
        Args:
            cfg_like: 설정 소스
                - BaseModel: Policy 인스턴스 (직접 전달)
                - str/Path: YAML 파일 경로
                - dict: 설정 딕셔너리
                - None: 기본 파일 또는 Pydantic 기본값 사용
            policy_class: Policy 클래스 (LogPolicy, ImageLoadPolicy 등)
            module_file: 호출 모듈의 __file__ (경로 계산용)
            config_filename: 기본 설정 파일 이름 (예: "log.yaml")
            **overrides: 런타임 오버라이드 (KeyPath 형식)
        
        Returns:
            Policy 인스턴스
        
        Examples:
            >>> # YAML 파일 사용
            >>> policy = ConfigLikeLoader.load(
            ...     cfg_like="custom_log.yaml",
            ...     policy_class=LogPolicy,
            ...     module_file=__file__,
            ...     config_filename="log.yaml"
            ... )
            
            >>> # YAML 없으면 Pydantic 기본값 + overrides
            >>> policy = ConfigLikeLoader.load(
            ...     cfg_like=None,
            ...     policy_class=ImageLoadPolicy,
            ...     module_file=__file__,
            ...     config_filename="image.yaml",
            ...     save__quality=90
            ... )
        """
        # 1. Policy 인스턴스가 직접 전달된 경우
        # Duck typing: 클래스 이름으로 체크 (import 경로 불일치 문제 해결)
        if cfg_like is not None and cfg_like.__class__.__name__ == policy_class.__name__:
            if overrides:
                return cfg_like.model_copy(update=overrides)
            return cfg_like
        
        # 2. Section 이름 추출 (Policy.name 필드)
        section_name = policy_class().name
        
        # 3. cfg_like가 None이면 기본 경로 자동 계산
        if cfg_like is None:
            default_config_path = Path(module_file).parent.parent / "configs" / config_filename
            
            # 파일 존재 여부 확인
            if not default_config_path.exists():
                # 🔥 파일 없음 → Pydantic 기본값 생성
                policy = policy_class()
                
                if not overrides:
                    return policy
                
                # overrides 있으면 KeyPath → dict 변환
                from keypath_utils import KeyPathDict
                override_dict = KeyPathDict.to_nested_dict(overrides)
                
                # 기본값 + overrides 병합
                return policy.model_copy(update=override_dict)
            
            # 파일 존재 → ConfigLoader 사용
            cfg_like = str(default_config_path)
        
        # 4. ConfigLoader로 로드 (파일 존재하는 경우)
        from cfg_utils import ConfigLoader
        import yaml
        
        # YAML 파일의 실제 섹션 이름 확인
        if isinstance(cfg_like, (str, Path)):
            yaml_path = Path(cfg_like)
            if yaml_path.exists() and yaml_path.suffix in ['.yaml', '.yml']:
                try:
                    with open(yaml_path, 'r', encoding='utf-8') as f:
                        yaml_content = yaml.safe_load(f)
                        if yaml_content and isinstance(yaml_content, dict):
                            # 기본 섹션 이름으로 시작하는 키 찾기
                            # 예: "webdriver", "webdriver_china", "webdriver_global"
                            base_section_prefix = section_name.split('_')[0]
                            matching_section_keys = [
                                k for k in yaml_content.keys() 
                                if k.startswith(base_section_prefix)
                            ]
                            if matching_section_keys:
                                section_name = matching_section_keys[0]
                except Exception:
                    pass  # YAML 파싱 실패 시 기본 section_name 유지
        
        src = (cfg_like, section_name)
        loader = ConfigLoader(src=src)
        
        # overrides 적용
        if overrides:
            for key, value in overrides.items():
                loader.override(f"{section_name}__{key}", value)
        
        # Policy로 변환
        return loader.to_model(policy_class, section=section_name)  # type: ignore


__all__ = ['ConfigLikeLoader']
