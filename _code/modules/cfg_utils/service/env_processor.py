# -*- coding: utf-8 -*-
# cfg_utils_v2/service/env_processor.py

"""EnvProcessor: 환경 변수 통합 처리 (env + env_os).

SRP 준수:
- env 소스 처리 (문자열, YAML 파일)
- env_os 소스 처리 (OS 환경 변수)
- env section에 Deep Merge

특징:
- env와 env_os를 통합 처리
- 처리 순서: env → env_os (env_os가 override)
- env section 자동 생성
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from modules.keypath_utils import KeyPathState, KeyPathMerger, KeyPathMergePolicy
from modules.data_utils.core.types import PathLike

from .source import YamlFileSource
from .env_os_loader import EnvOSLoader


class EnvProcessor:
    """환경 변수 통합 처리기.
    
    사용 예시::
    
        # env만
        processor = EnvProcessor(env=["DEBUG=true", "env.yaml"])
        state = processor.process(state)
        
        # env_os만
        processor = EnvProcessor(env_os=["PATH", "HOME"])
        state = processor.process(state)
        
        # env + env_os 함께
        processor = EnvProcessor(
            env=["DEBUG=from_env"],
            env_os=["DEBUG"]  # env_os가 override
        )
        state = processor.process(state)
    """
    
    def __init__(
        self,
        env: Optional[Union[str, List[str], PathLike, List[PathLike]]] = None,
        env_os: Optional[Union[bool, List[str]]] = None,
    ):
        """초기화.
        
        Args:
            env: 환경 변수 소스
                - str: "KEY=VALUE" 형식 문자열
                - List[str]: 여러 개의 "KEY=VALUE"
                - YAML Path: YAML 파일 파싱 후 merge
                - List[YAML Path]: 여러 YAML 파일 순차 merge
            env_os: OS 환경 변수 읽기
                - True: 모든 OS 환경 변수
                - List[str]: 지정된 키만
                - None/False: 사용 안 함
        """
        self.env = env
        self.env_os = env_os
    
    def process(self, state: KeyPathState) -> KeyPathState:
        """환경 변수 처리.
        
        처리 순서:
        1. env section 확인 및 생성
        2. env 소스 처리 → merge
        3. env_os 소스 처리 → merge (override)
        
        Args:
            state: 현재 KeyPathState
            
        Returns:
            처리된 KeyPathState
            
        Raises:
            ValueError: 잘못된 env 형식
            FileNotFoundError: YAML 파일 없음
        """
        current_data = state.to_dict()
        
        # env section 확인 및 생성
        if "env" not in current_data:
            current_data["env"] = {}
        
        # 1️⃣ env 처리
        if self.env is not None:
            current_data["env"] = self._process_env(current_data["env"])
        
        # 2️⃣ env_os 처리 (env override)
        if self.env_os is not None and self.env_os is not False:
            current_data["env"] = self._process_env_os(current_data["env"])
        
        return KeyPathState(name=state.name, store=current_data)
    
    def _process_env(self, env_data: Dict[str, Any]) -> Dict[str, Any]:
        """env 소스 처리.
        
        Args:
            env_data: 현재 env section 데이터
            
        Returns:
            처리된 env section 데이터
        """
        if self.env is None:
            return env_data
        
        # env를 리스트로 정규화
        env_list = self.env if isinstance(self.env, list) else [self.env]
        
        merger = KeyPathMerger(policy=KeyPathMergePolicy())
        
        # 각 env 항목 처리
        for env_item in env_list:
            parsed_data = self._parse_env_item(env_item)
            env_data = merger.merge(env_data, parsed_data)
        
        return env_data
    
    def _process_env_os(self, env_data: Dict[str, Any]) -> Dict[str, Any]:
        """env_os 소스 처리.
        
        Args:
            env_data: 현재 env section 데이터
            
        Returns:
            처리된 env section 데이터
        """
        if self.env_os is None or self.env_os is False:
            return env_data
        
        # OS 환경 변수 로드 (YAML 파일 자동 파싱)
        env_os_data = EnvOSLoader.load(self.env_os, parse_yaml=True)
        
        # Deep merge
        merger = KeyPathMerger(policy=KeyPathMergePolicy())
        return merger.merge(env_data, env_os_data)
    
    def _parse_env_item(self, env_item: Union[str, PathLike]) -> dict:
        """env 항목 파싱.
        
        Args:
            env_item: env 항목 (str "KEY=VALUE" or YAML Path)
        
        Returns:
            dict: 파싱된 env 데이터
        
        Raises:
            ValueError: 잘못된 env 형식
        """
        # str인 경우: "KEY=VALUE" 형식
        if isinstance(env_item, str):
            # YAML 파일 경로 확인
            path = Path(env_item)
            if path.exists() and path.suffix in [".yaml", ".yml"]:
                # YAML 파일 파싱
                source = YamlFileSource(path, section=None)
                kpd = source.extract()
                return kpd.data
            
            # "KEY=VALUE" 형식 파싱
            if "=" in env_item:
                key, value = env_item.split("=", 1)
                return {key.strip(): value.strip()}
            
            raise ValueError(
                f"Invalid env format: '{env_item}'. "
                f"Expected 'KEY=VALUE' or YAML file path."
            )
        
        # Path 객체인 경우
        if isinstance(env_item, Path):
            if not env_item.exists():
                raise FileNotFoundError(f"Env file not found: {env_item}")
            
            source = YamlFileSource(env_item, section=None)
            kpd = source.extract()
            return kpd.data
        
        raise TypeError(
            f"Unsupported env type: {type(env_item)}. "
            f"Expected str or Path."
        )
