# -*- coding: utf-8 -*-
"""cfg_utils.services.policy_loader
===================================

ConfigLoader 정책 YAML 로딩 및 파싱 전문 서비스.

책임:
- config_loader.yaml 파일 로딩 (placeholder 처리 제어)
- Dict → ConfigLoaderPolicy 파싱 (list source 병합 포함)
- LogPolicy 추출

SRP 원칙:
- ConfigLoader: State 관리 + Export
- PolicyLoader: 정책 로딩/파싱 (이 파일)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from modules.keypath_utils import KeyPathDict


class PolicyLoader:
    """ConfigLoader 정책 YAML 로딩 및 파싱 전문 서비스.
    
    Static method로 구성되어 재사용 및 테스트가 용이합니다.
    
    Examples:
        >>> # 1. YAML 파일 로드
        >>> policy_dict = PolicyLoader.load_from_yaml("config_loader.yaml")
        
        >>> # 2. ConfigLoaderPolicy 파싱
        >>> loader_policy = PolicyLoader.parse_to_policy(policy_dict)
        
        >>> # 3. LogPolicy만 추출
        >>> log_policy = PolicyLoader.parse_log_policy(policy_dict)
    """
    
    @staticmethod
    def load_from_yaml(
        config_path: Union[str, Path, tuple[Union[str, Path], str]],
        placeholder_enabled: bool = False
    ) -> Dict[str, Any]:
        """ConfigLoader 정책 파일 로드.
        
        Args:
            config_path: ConfigLoader 정책 파일 경로
                - str/Path: YAML 파일 경로 (전체 로드)
                - tuple[str/Path, str]: (파일 경로, section) 튜플
            placeholder_enabled: Placeholder 해석 활성화 여부
                - False: env가 아직 없어서 빈 문자열로 해석되는 것 방지
                - True: env context가 준비된 경우에만 사용
        
        Returns:
            정책 dict
            
        Raises:
            FileNotFoundError: 파일 없음
            
        Examples:
            >>> # 전체 YAML 로드
            >>> policy_dict = PolicyLoader.load_from_yaml("config_loader.yaml")
            
            >>> # Section만 로드
            >>> policy_dict = PolicyLoader.load_from_yaml(
            ...     ("config_loader.yaml", "default")
            ... )
        """
        if config_path is None:
            return {}
        
        # Tuple (파일 경로, section) 처리
        if isinstance(config_path, tuple) and len(config_path) == 2:
            file_path, section = config_path
            file_path = Path(file_path)
        else:
            # str/Path (파일 경로만)
            file_path = Path(config_path)
            section = None
        
        # 파일 존재 확인
        if not file_path.exists():
            raise FileNotFoundError(
                f"ConfigLoader policy file not found: {file_path}"
            )
        
        # YAML 파일 로드
        from ..core.policy import SourcePolicy, NormalizePolicy
        from modules.structured_io.core.policy import BaseParserPolicy
        from .source import YamlFileSource
        
        # Placeholder 해석 제어 (기본적으로 비활성화)
        yaml_policy = SourcePolicy(
            src=file_path,
            yaml_parser=BaseParserPolicy(
                safe_mode=True,
                encoding="utf-8",
                enable_env=False,
                enable_include=True,
                enable_placeholder=placeholder_enabled,
                enable_reference=False
            ),
            yaml_normalizer=NormalizePolicy(
                normalize_keys=True,
                drop_blanks=False,
                resolve_vars=False  # Placeholder와 함께 제어
            )
        )
        source = YamlFileSource(file_path, section=section, policy=yaml_policy)
        kpd = source.extract()
        
        return kpd.data
    
    @staticmethod
    def parse_to_policy(policy_dict: Optional[Dict[str, Any]]):
        """Dict → ConfigLoaderPolicy 파싱.
        
        ConfigLoaderPolicy는 3개 필드를 YAML에서 로드합니다:
        - source: SourcePolicy (단일) 또는 List[SourcePolicy] (다중, 각 src별 정책)
        - keypath: KeyPathStatePolicy
        - log: LogPolicy
        
        YAML 형식:
        1. 단일 SourcePolicy (기존 방식):
           source:
             src: [["config.yaml", "image"]]
             yaml_parser: {...}
        
        2. 다중 SourcePolicy (각 src별 정책):
           source:
             - src: [["image.yaml", "image"]]
               yaml_parser: {...}  # image 전용 정책
             - src: [["overlay.yaml", "overlay"]]
               yaml_parser: {...}  # overlay 전용 정책
        
        Args:
            policy_dict: 정책 dict
        
        Returns:
            ConfigLoaderPolicy 또는 None
            
        Examples:
            >>> policy_dict = {"source": {...}, "keypath": {...}, "log": {...}}
            >>> loader_policy = PolicyLoader.parse_to_policy(policy_dict)
        """
        if policy_dict is None:
            return None
        
        try:
            from ..core.policy import ConfigLoaderPolicy, SourcePolicy
            from modules.keypath_utils.core.policy import KeyPathStatePolicy
            
            # 1. source 파싱 (list 또는 dict 지원)
            source_data = policy_dict.get("source", {})
            
            if isinstance(source_data, list):
                # List[dict]: 각 dict를 개별 SourcePolicy로 변환 (각 src별 정책 유지)
                source_policies = []
                
                for item in source_data:
                    if not isinstance(item, dict):
                        continue
                    
                    # 각 item을 개별 SourcePolicy로 변환
                    try:
                        item_policy = SourcePolicy(**item)
                        source_policies.append(item_policy)
                    except Exception as e:
                        import sys
                        print(
                            f"Warning: Failed to parse SourcePolicy item: {e}. Skipping.",
                            file=sys.stderr
                        )
                        continue
                
                # List[SourcePolicy] 반환 (각 src별 정책 유지)
                source = source_policies if source_policies else SourcePolicy()
                
            elif isinstance(source_data, dict):
                # dict: 단일 SourcePolicy
                source = SourcePolicy(**source_data) if source_data else SourcePolicy()
            else:
                source = SourcePolicy()
            
            # 2. keypath 파싱
            keypath_dict = policy_dict.get("keypath", {})
            keypath = KeyPathStatePolicy(**keypath_dict) if keypath_dict else None
            
            # 3. log 파싱 (별도 메서드 사용)
            log = PolicyLoader.parse_log_policy(policy_dict)
            
            # ConfigLoaderPolicy 생성
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
    
    @staticmethod
    def parse_log_policy(policy_dict: Optional[Dict[str, Any]]):
        """Dict에서 LogPolicy만 추출.
        
        Args:
            policy_dict: 정책 dict
        
        Returns:
            LogPolicy 또는 None
            
        Examples:
            >>> policy_dict = {"log": {"enabled": True, "name": "loader"}}
            >>> log_policy = PolicyLoader.parse_log_policy(policy_dict)
        """
        if policy_dict is None:
            return None
        
        log_policy_dict = policy_dict.get("log", {})
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
