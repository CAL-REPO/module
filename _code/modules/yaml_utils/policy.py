# -*- coding: utf-8 -*-
# yaml_utils/policy.py
from __future__ import annotations
from pydantic import BaseModel, Field

class YamlParserPolicy(BaseModel):
    enable_env: bool = Field(True, description="환경 변수(${VAR}) 확장 활성화 여부")
    enable_include: bool = Field(True, description="!include 태그 활성화 여부")
    enable_placeholder: bool = Field(True, description="PlaceholderResolver 해석 활성화 여부")
    safe_mode: bool = Field(True, description="PyYAML SafeLoader 사용 여부")
    encoding: str = Field("utf-8", description="파일 인코딩")
    on_error: str = Field("raise", description="에러 발생 시 처리 방식: 'raise' | 'ignore' | 'warn'")
    sort_keys: bool = Field(False, description="dump 시 key를 정렬할지 여부")
    default_flow_style: bool = Field(False, description="dump 시 compact 스타일 사용 여부")
    indent: int = Field(2, description="YAML indent 간격 설정")

    class Config:
        extra = "ignore"
        validate_assignment = True

    def is_safe_loader(self) -> bool:
        return self.safe_mode

    @classmethod
    def default(cls) -> YamlParserPolicy:
        return cls()  # type: ignore