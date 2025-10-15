# structured_io/base/base_policy.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Union, List, Dict, Any
from pathlib import Path


class SourcePathConfig(BaseModel):
    """개별 소스 파일 설정"""
    path: Union[str, Path] = Field(..., description="파일 경로")
    section: Optional[str] = Field(None, description="추출할 섹션 (None이면 전체 사용)")
    
    class Config:
        extra = "ignore"


class BaseParserPolicy(BaseModel):
    # YAML 기능 동등 지원
    source_paths: Optional[Union[
        SourcePathConfig,
        List[SourcePathConfig]
    ]] = Field(
        None, 
        description="소스 파일 경로. 단일 SourcePathConfig 또는 리스트"
    )
    enable_env: bool = Field(True, description="환경 변수(${VAR} 또는 ${VAR:default}) 확장 활성화")
    enable_include: bool = Field(True, description="!include 태그 활성화 여부 (JSON에서는 비활성)")
    enable_placeholder: bool = Field(True, description="{{ var }} 또는 ${VAR} 스타일 치환")
    enable_reference: bool = Field(False, description="${ref:path.to.key} 참조 치환")
    encoding: str = Field("utf-8", description="파일 인코딩")
    on_error: str = Field("raise", description="에러 처리: 'raise' | 'ignore' | 'warn'")
    safe_mode: bool = Field(True, description="YAML: SafeLoader 사용 여부 / JSON: 의미 없음")

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
