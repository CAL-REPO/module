"""ENV-based configuration initialization helper.

메인스크립트가 ENV 변수와 상호작용하는 표준 패턴을 제공합니다.

주요 기능:
1. ENV에서 paths.local.yaml 경로 읽기
2. paths.local.yaml 로드
3. ConfigLoader 초기화 헬퍼

사용 예시::

    from modules.script_utils import EnvBasedConfigInitializer
    
    # OTO 스크립트
    class OTO:
        def __init__(self):
            # 3줄로 초기화 완료
            self.paths_dict = EnvBasedConfigInitializer.load_paths_from_env()
            self.loader = EnvBasedConfigInitializer.create_config_loader(
                "configs_loader_file_oto", self.paths_dict
            )
            self.config = self.loader.load()
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional


class EnvBasedConfigInitializer:
    """ENV 기반 Config 초기화 헬퍼.
    
    메인스크립트에서 반복적으로 사용되는 패턴을 캡슐화:
    - ENV 읽기 → paths.local.yaml 로드 → ConfigLoader 생성
    
    이 클래스는 순수한 헬퍼 역할만 수행하며, 라이브러리(cfg_utils)의 순수성을 훼손하지 않습니다.
    """
    
    @staticmethod
    def load_paths_from_env(env_key: str = "CASHOP_PATHS") -> Dict[str, Any]:
        """ENV → paths.local.yaml 로드.
        
        Args:
            env_key: ENV 변수명 (기본값: "CASHOP_PATHS")
        
        Returns:
            paths.local.yaml 내용 (dict)
        
        Raises:
            ValueError: ENV 변수가 설정되지 않은 경우
            FileNotFoundError: ENV 경로의 파일이 없는 경우
        
        Examples:
            >>> paths_dict = EnvBasedConfigInitializer.load_paths_from_env()
            >>> print(paths_dict["base_path"])
            M:/CALife/CAShop - 구매대행/_code
        """
        env_value = os.getenv(env_key)
        if not env_value:
            raise ValueError(
                f"ENV variable '{env_key}' not set. "
                f"Please set it to the path of paths.local.yaml.\n"
                f"Example: conda env config vars set {env_key}=M:/path/to/paths.local.yaml"
            )
        
        env_path = Path(env_value)
        if not env_path.exists():
            raise FileNotFoundError(
                f"ENV variable '{env_key}' points to non-existent file: {env_path}"
            )
        
        # ReferenceResolver를 직접 사용하여 ${key} 형식 치환
        # ConfigLoader를 사용하지 않아 순환 의존성 제거
        import yaml
        from unify_utils.resolver.reference import ReferenceResolver
        
        # 1. Raw YAML 파싱 (placeholder 해석 없이)
        text = env_path.read_text(encoding="utf-8")
        raw = yaml.safe_load(text)
        
        if not isinstance(raw, dict):
            raise TypeError(
                f"paths.local.yaml must be a dict, got {type(raw)}"
            )
        
        # 2. ReferenceResolver로 ${key} 형식 치환
        # nested reference를 완전히 해석하기 위해 여러 번 적용
        resolved = raw
        max_iterations = 10  # 무한 루프 방지
        
        for _ in range(max_iterations):
            resolver = ReferenceResolver(resolved, recursive=True)
            new_resolved = resolver.apply(resolved)
            
            # 더 이상 변화가 없으면 종료
            if new_resolved == resolved:
                break
            
            resolved = new_resolved
        
        if not isinstance(resolved, dict):
            raise TypeError(
                f"Resolved paths.local.yaml must be a dict, got {type(resolved)}"
            )
        
        return resolved
    
    @staticmethod
    def create_config_loader(
        loader_file_key: str,
        paths_dict: Dict[str, Any],
        policy_overrides: Optional[Dict[str, Any]] = None
    ) -> "ConfigLoader":
        """paths_dict에서 loader 파일 경로 추출 후 ConfigLoader 생성.
        
        Args:
            loader_file_key: paths_dict에서 찾을 키 (예: "configs_loader_file_oto")
            paths_dict: load_paths_from_env()로 로드한 dict
            policy_overrides: ConfigPolicy 추가 오버라이드
        
        Returns:
            ConfigLoader 인스턴스
        
        Raises:
            KeyError: loader_file_key가 paths_dict에 없는 경우
        
        Examples:
            >>> paths_dict = EnvBasedConfigInitializer.load_paths_from_env()
            >>> loader = EnvBasedConfigInitializer.create_config_loader(
            ...     "configs_loader_file_oto", paths_dict
            ... )
            >>> config = loader.as_dict()
        """
        from modules.cfg_utils.services.config_loader import ConfigLoader
        from modules.cfg_utils.core.policy import ConfigPolicy
        
        loader_file = paths_dict.get(loader_file_key)
        if not loader_file:
            raise KeyError(
                f"'{loader_file_key}' not found in paths_dict.\n"
                f"Available keys: {list(paths_dict.keys())}"
            )
        
        # loader_file이 이미 치환된 경로인지 확인
        # paths_dict의 값은 이미 ReferenceResolver로 치환됨
        
        # ConfigPolicy 생성 (reference_context에 paths_dict 포함)
        policy_dict = policy_overrides or {}
        
        # reference_context를 paths_dict로 설정 (추가 reference 치환용)
        if "reference_context" not in policy_dict:
            policy_dict["reference_context"] = paths_dict
        
        # ConfigPolicy 생성
        policy = ConfigPolicy(**policy_dict)
        
        # ConfigLoader 생성 (cfg_like는 loader_file에서 자동 로드)
        return ConfigLoader(
            cfg_like=loader_file,  # 이미 치환된 경로 (예: "M:/.../_code/configs/loader/config_loader_oto.yaml")
            policy=policy
        )
