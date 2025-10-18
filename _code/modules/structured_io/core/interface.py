# -*- coding: utf-8 -*-
# structured_io/core/interface.py
# description: structured_io 공통 추상 인터페이스 (Parser, Dumper)

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from pathlib import Path


class BaseParser(ABC):
    """구조화 데이터 파싱을 위한 추상 기반 클래스.
    
    특징:
    - policy: 파싱 정책 (환경 변수, include, placeholder 등)
    - context: 런타임 컨텍스트 변수
    - parse(): 문자열 → 구조화 데이터 변환
    """
    
    def __init__(self, policy, context: dict | None = None):
        self.policy = policy
        self.context = context or {}

    @abstractmethod
    def parse(self, text: str, base_path: Path | None = None) -> Any:
        """텍스트를 파싱하여 구조화 데이터로 변환.
        
        Args:
            text: 파싱할 텍스트
            base_path: 상대 경로 해석을 위한 기준 경로
            
        Returns:
            파싱된 구조화 데이터
        """
        raise NotImplementedError


class BaseDumper(ABC):
    """구조화 데이터 직렬화를 위한 추상 기반 클래스.
    
    특징:
    - policy: 덤프 정책 (들여쓰기, 정렬, 인코딩 등)
    - dump(): 구조화 데이터 → 문자열 변환
    """
    
    def __init__(self, policy):
        self.policy = policy

    @abstractmethod
    def dump(self, data: Any) -> str:
        """구조화 데이터를 문자열로 직렬화.
        
        Args:
            data: 직렬화할 데이터
            
        Returns:
            직렬화된 문자열
        """
        raise NotImplementedError