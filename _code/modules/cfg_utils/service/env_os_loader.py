# -*- coding: utf-8 -*-
# cfg_utils_v2/service/env_os_loader.py

"""EnvOSLoader: OS 환경 변수 로더 (YAML 파일 지원).

SRP 준수:
- OS 환경 변수 읽기
- YAML 파일 경로 감지 및 파싱
- env section에 merge할 dict 반환

특징:
- True: 모든 OS 환경 변수
- List[str]: 지정된 키만
- YAML 파일 경로 자동 감지 (.yaml/.yml)
- 값이 파일 경로면 YAML 파싱 후 merge
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from modules.structured_io.formats.yaml_io import YamlParser
from modules.structured_io.core.policy import BaseParserPolicy


class EnvOSLoader:
    """OS 환경 변수 로더.
    
    사용 예시::
    
        # 모든 OS 환경 변수
        env_data = EnvOSLoader.load(env_os=True)
        
        # 특정 키만
        env_data = EnvOSLoader.load(env_os=["PATH", "HOME", "DEBUG"])
        
        # ConfigLoader에서 사용
        loader = ConfigLoader(
            base_sources=[(ImagePolicy(), "image")],
            env_os=["DEBUG", "LOG_LEVEL"]
        )
    """
    
    @classmethod
    def load(
        cls,
        env_os: Union[bool, List[str]],
        *,
        parse_yaml: bool = True,
    ) -> Dict[str, Any]:
        """OS 환경 변수 로드.
        
        처리 순서:
        1. env_os에 따라 OS 환경 변수 수집
        2. 값이 YAML 파일 경로면 파싱
        3. 그 외는 문자열 그대로 반환
        
        Args:
            env_os: 
                - True: 모든 OS 환경 변수
                - List[str]: 지정된 키만
            parse_yaml: True이면 YAML 파일 경로 감지 및 파싱
            
        Returns:
            OS 환경 변수 dict
            
        Raises:
            TypeError: 잘못된 env_os 타입
            FileNotFoundError: YAML 파일 없음
            RuntimeError: YAML 파싱 실패
            
        Example::
        
            # 모든 OS 환경 변수
            env_data = EnvOSLoader.load(env_os=True)
            # {'PATH': '...', 'HOME': '...', 'DEBUG': 'true', ...}
            
            # 특정 키만
            env_data = EnvOSLoader.load(env_os=["DEBUG", "CONFIG_PATH"])
            # {'DEBUG': 'true', 'CONFIG_PATH': 'config.yaml'}
            
            # YAML 파일 경로가 값이면 파싱
            os.environ['MY_CONFIG'] = 'config.yaml'
            env_data = EnvOSLoader.load(env_os=["MY_CONFIG"])
            # {'MY_CONFIG': {'key': 'value', ...}}  # ← YAML 파싱됨
        """
        # 1️⃣ OS 환경 변수 수집
        if env_os is True:
            # 모든 OS 환경 변수
            env_os_data = dict(os.environ)
        elif isinstance(env_os, list):
            # 지정된 키만
            env_os_data = {}
            for key in env_os:
                if key in os.environ:
                    env_os_data[key] = os.environ[key]
        else:
            raise TypeError(
                f"Unsupported env_os type: {type(env_os)}. "
                f"Expected True or List[str]."
            )
        
        # 2️⃣ YAML 파일 경로 감지 및 파싱
        if parse_yaml:
            env_os_data = cls._parse_yaml_values(env_os_data)
        
        return env_os_data
    
    @classmethod
    def _parse_yaml_values(cls, env_data: Dict[str, str]) -> Dict[str, Any]:
        """환경 변수 값 중 YAML 파일 경로 감지 및 파싱.
        
        Args:
            env_data: OS 환경 변수 dict
            
        Returns:
            YAML 파싱된 dict (파일이 아니면 문자열 그대로)
            
        Raises:
            FileNotFoundError: YAML 파일 없음
            RuntimeError: YAML 파싱 실패
        """
        result = {}
        
        for key, value in env_data.items():
            # YAML 파일 경로 확인
            if cls._is_yaml_path(value):
                path = Path(value)
                
                if not path.exists():
                    raise FileNotFoundError(
                        f"OS 환경 변수 '{key}'의 YAML 파일을 찾을 수 없습니다: {path}"
                    )
                
                # YAML 파싱
                try:
                    parser_policy = BaseParserPolicy(
                        enable_placeholder=True,
                        enable_env=True,
                        enable_reference=False,
                        encoding="utf-8",
                        on_error="raise"
                    )
                    parser = YamlParser(parser_policy, context={})
                    parsed_data = parser.parse(path.read_text(encoding="utf-8"))
                    result[key] = parsed_data
                except Exception as e:
                    raise RuntimeError(
                        f"OS 환경 변수 '{key}'의 YAML 파싱 실패: {path}\n"
                        f"원인: {e}"
                    ) from e
            else:
                # YAML 파일이 아니면 문자열 그대로
                result[key] = value
        
        return result
    
    @classmethod
    def _is_yaml_path(cls, value: str) -> bool:
        """값이 YAML 파일 경로인지 확인.
        
        Args:
            value: 환경 변수 값
            
        Returns:
            True이면 YAML 파일 경로
        """
        if not isinstance(value, str):
            return False
        
        # YAML 확장자 확인
        path = Path(value)
        return path.suffix.lower() in [".yaml", ".yml"]
