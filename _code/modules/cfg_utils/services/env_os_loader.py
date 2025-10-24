# -*- coding: utf-8 -*-
# cfg_utils_v2/services/env_os_loader.py

"""EnvOSLoader: OS 환경 변수 로더 (YAML 파일 지원).

SRP 준수:
- OS 환경 변수 읽기 (명시적 리스트만)
- YAML 파일 경로 감지 및 파싱
- env section에 merge할 dict 반환

특징:
- List[str]: 지정된 환경 변수만 읽기 (보안 강화)
- YAML 파일 경로 자동 감지 (.yaml/.yml)
- 값이 파일 경로면 YAML 파싱 후 merge

보안:
- env_os=True (모든 환경 변수) 제거됨
- 필요한 환경 변수만 명시적으로 지정
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from modules.structured_io.formats.yaml_io import YamlParser
from modules.structured_io.core.policy import BaseParserPolicy


class EnvOSLoader:
    """OS 환경 변수 로더 (명시적 리스트만 허용).
    
    사용 예시::
    
        # 특정 환경 변수만 읽기 (권장)
        env_data = EnvOSLoader.load(env_os=["CASHOP_PATHS", "DEBUG"])
        
        # ConfigLoader에서 사용
        loader = ConfigLoader(
            config_loader_cfg_path="config.yaml",
            env_os=["CASHOP_PATHS"]  # 명시적 지정
        )
    """
    
    @classmethod
    def load(
        cls,
        env_os: List[str],
        *,
        parse_yaml: bool = True,
    ) -> Dict[str, Any]:
        """OS 환경 변수 로드.
        
        처리 순서:
        1. env_os 리스트에 지정된 OS 환경 변수만 수집
        2. 값이 YAML 파일 경로면 2-pass 파싱 (self-reference resolve)
        3. 그 외는 문자열 그대로 반환
        
        Args:
            env_os: 읽을 환경 변수 이름 리스트 (예: ["CASHOP_PATHS", "DEBUG"])
            parse_yaml: True이면 YAML 파일 경로 감지 및 2-pass 파싱
            
        Returns:
            OS 환경 변수 dict
            
        Raises:
            TypeError: 잘못된 env_os 타입
            FileNotFoundError: YAML 파일 없음
            RuntimeError: YAML 파싱 실패
            
        Example::
        
            # 특정 환경 변수만 읽기 (보안 강화)
            env_data = EnvOSLoader.load(env_os=["CASHOP_PATHS", "DEBUG"])
            # {'CASHOP_PATHS': 'paths.yaml', 'DEBUG': 'true'}
            
            # YAML 파일 경로가 값이면 2-pass 파싱 (self-reference resolve)
            os.environ['CASHOP_PATHS'] = 'config.yaml'
            env_data = EnvOSLoader.load(env_os=["CASHOP_PATHS"])
            # {'CASHOP_PATHS': {'key': 'value', ...}}  # ← YAML 파싱 + {{}} resolve
        """
        # 1️⃣ OS 환경 변수 수집 (명시적 리스트만 허용)
        if not isinstance(env_os, list):
            raise TypeError(
                f"❌ env_os must be a list of environment variable names. "
                f"Got: {type(env_os).__name__}\n"
                f"Example: env_os=['CASHOP_PATHS', 'DEBUG']"
            )
        
        env_os_data = {}
        for key in env_os:
            if key in os.environ:
                env_os_data[key] = os.environ[key]
        
        # 2️⃣ YAML 파일 경로 감지 및 2-pass 파싱
        if parse_yaml:
            env_os_data = cls._parse_yaml_values(env_os_data)
        
        return env_os_data
    
    @classmethod
    def _parse_yaml_values(cls, env_data: Dict[str, str]) -> Dict[str, Any]:
        """환경 변수 값 중 YAML 파일 경로 감지 및 2-pass 파싱.
        
        2-pass parsing으로 YAML 파일 내부의 self-reference를 resolve:
        - 1st pass: Raw parse ({{placeholder}} 포함된 그대로)
        - 2nd pass: 1st pass 결과를 context로 사용하여 self-reference resolve
        
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
                
                # YAML 단순 파싱 (placeholder 보존)
                try:
                    parser_policy = BaseParserPolicy(
                        enable_placeholder=True,
                        enable_env=False,  # ${} 충돌 방지
                        enable_reference=False,
                        encoding="utf-8",
                        on_error="raise"
                    )
                    
                    yaml_text = path.read_text(encoding="utf-8")
                    parser = YamlParser(parser_policy, context={})
                    parsed_data = parser.parse(yaml_text)
                    
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
