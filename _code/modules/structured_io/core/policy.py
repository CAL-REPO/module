# -*- coding: utf-8 -*-
# structured_io/core/policy.py
# description: structured_io 정책 모델 정의 (Parser, Dumper)

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Union, List, Dict, Any
from pathlib import Path


class BaseParserPolicy(BaseModel):
    """Parser 정책 (YAML, JSON 공통)
    
    Parser의 동작을 제어하는 정책입니다.
    
    Attributes:
        enable_env: 환경 변수(${VAR} 또는 ${VAR:default}) 확장 활성화
        enable_include: !include 태그 활성화 여부 (JSON에서는 비활성)
        enable_placeholder: {{ var }} 또는 ${VAR} 스타일 치환
        enable_reference: ${ref:path.to.key} 참조 치환
        encoding: 파일 인코딩
        on_error: 에러 처리 방식 ('raise' | 'ignore' | 'warn')
        safe_mode: YAML SafeLoader 사용 여부 / JSON에서는 의미 없음
    
    Note:
        - source_paths 필드는 제거됨 (cfg_utils.SourcePathPolicy로 이동)
        - Parser는 파싱만 담당, 소스 관리는 ConfigLoader의 책임
    """
    enable_env: bool = Field(default=True, description="환경 변수(${VAR} 또는 ${VAR:default}) 확장 활성화")
    enable_include: bool = Field(default=True, description="!include 태그 활성화 여부 (JSON에서는 비활성)")
    enable_placeholder: bool = Field(default=True, description="{{ var }} 또는 ${VAR} 스타일 치환")
    enable_reference: bool = Field(default=False, description="${ref:path.to.key} 참조 치환 (기본 비활성화)")
    encoding: str = Field(default="utf-8", description="파일 인코딩")
    on_error: str = Field(default="raise", description="에러 처리: 'raise' | 'ignore' | 'warn'")
    safe_mode: bool = Field(default=True, description="YAML: SafeLoader 사용 여부 / JSON: 의미 없음")

    class Config:
        extra = "ignore"
        validate_assignment = True

    def is_safe_loader(self) -> bool:
        return self.safe_mode

class BaseDumperPolicy(BaseModel):
    file_path: Optional[Union[str, Path]] = Field(None, description="출력 파일 경로")
    encoding: str = Field("utf-8", description="출력 인코딩")
    sort_keys: bool = Field(False, description="Key 정렬 여부")
    indent: int = Field(2, description="들여쓰기 간격")
    default_flow_style: bool = Field(False, description="YAML compact 스타일 여부")
    allow_unicode: bool = Field(True, description="유니코드 허용 여부")
    safe_mode: bool = Field(True, description="YAML: SafeDumper 사용 여부")

    class Config:
        extra = "ignore"
        validate_assignment = True
