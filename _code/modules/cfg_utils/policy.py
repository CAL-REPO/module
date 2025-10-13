# -*- coding: utf-8 -*-
# cfg_utils/policy.py
# ConfigLoader 및 하위 YAML 파서 정책 통합 모델 정의

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
from yaml_utils.policy import YamlParserPolicy


class ConfigPolicy(BaseModel):
    """
    ConfigLoader 정책 정의
    - YAML 파서 정책(YamlParserPolicy) 내장
    - 병합/정제 동작을 일원화
    """

    # ----------------------------------------
    # YAML 관련 정책 (하위 위임)
    # ----------------------------------------
    yaml_policy: YamlParserPolicy = Field(
        default_factory=YamlParserPolicy.default,
        description="YAML 파싱 관련 하위 정책 객체"
    )

    # ----------------------------------------
    # Loader / Normalizer 정책
    # ----------------------------------------
    drop_blanks: bool = Field(
        default=True,
        description="빈 값(None, '', 'None') 제거 여부"
    )
    resolve_reference: bool = Field(
        default=True,
        description="${key.path:default} 형태의 내부 참조 해석 여부"
    )

    # ----------------------------------------
    # 병합 정책
    # ----------------------------------------
    merge_order: Literal["base→yaml→arg"] = Field(
        default="base→yaml→arg",
        description="BaseModel, YAML, Arg 병합 순서 지정"
    )
    merge_mode: Literal["deep", "shallow"] = Field(
        default="deep",
        description="딕셔너리 병합 방식 지정 (deep/shallow)"
    )

    class Config:
        validate_assignment = True
