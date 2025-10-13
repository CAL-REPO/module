# structured_io/base/base_policy.py
from __future__ import annotations
from pydantic import BaseModel, Field

class BaseParserPolicy(BaseModel):
    # YAML 기능 동등 지원
    enable_env: bool = Field(True, description="환경 변수(${VAR} 또는 ${VAR:default}) 확장 활성화")
    enable_include: bool = Field(True, description="!include 태그 활성화 여부 (JSON에서는 비활성)")
    enable_placeholder: bool = Field(True, description="{{ var }} 또는 ${VAR} 스타일 치환")
    enable_reference: bool = Field(False, description="${ref:path.to.key} 참조 치환")
    safe_mode: bool = Field(True, description="YAML: SafeLoader 사용 여부 / JSON: 의미 없음")
    encoding: str = Field("utf-8", description="파일 인코딩")
    on_error: str = Field("raise", description="에러 처리: 'raise' | 'ignore' | 'warn'")

    # 호환 유지(기존 YamlParserPolicy에 있던 출력 관련 필드 보존)
    sort_keys: bool = Field(False, description="dump 시 key 정렬 여부(파서에는 영향 없음)")
    default_flow_style: bool = Field(False, description="dump compact 스타일 여부")
    indent: int = Field(2, description="dump 들여쓰기")

    class Config:
        extra = "ignore"
        validate_assignment = True

    def is_safe_loader(self) -> bool:
        return self.safe_mode


class BaseDumperPolicy(BaseModel):
    encoding: str = Field("utf-8", description="출력 인코딩")
    sort_keys: bool = Field(False, description="Key 정렬 여부")
    indent: int = Field(2, description="들여쓰기 간격")
    default_flow_style: bool = Field(False, description="YAML compact 스타일 여부")
    allow_unicode: bool = Field(True, description="유니코드 허용 여부")
    safe_mode: bool = Field(True, description="YAML: SafeDumper 사용 여부")

    class Config:
        extra = "ignore"
        validate_assignment = True
