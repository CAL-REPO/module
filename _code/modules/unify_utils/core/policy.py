# -*- coding: utf-8 -*-
# filename: unify_utils/core/policy.py
# description: unify_utils.core — Normalizer/Resolver Pydantic Policy 모델 정의
from __future__ import annotations

from typing import Any, Callable, Optional, Sequence
from pydantic import BaseModel, Field

# ✅ 규칙/프리셋 관련 타입은 presets.rules에서 단일 소스로 관리합니다.
from ..presets.rules import (
    NormalizeRule,
    RuleType,
    LetterCase,
    RegexFlag,
)

# ---------------------------------------------------------------------------
# Base Policy (공통 모듈 기반)
# ---------------------------------------------------------------------------

class UnifyPolicyBase(BaseModel):
    """unify_utils 모든 정책 클래스의 기반.
    
    공통 모듈에서 사용하는 기본 설정 항목:
    - recursive: 내부 구조 재귀 적용 여부
    - strict: 예외 발생 시 예외 전파 여부
    
    Note:
        프로젝트 특정 기능(예: KeyPath)은 별도 모듈에서 확장
    """

    recursive: bool = Field(False, description="dict/list 등 내부 구조 재귀 처리 여부")
    strict: bool = Field(False, description="오류 발생 시 예외 전파 여부")

# Backward compatibility
NormalizePolicyBase = UnifyPolicyBase

# ---------------------------------------------------------------------------
# Normalizer Policies
# ---------------------------------------------------------------------------

class RuleNormalizePolicy(UnifyPolicyBase):
    """정규식 기반 정규화 정책.
    - rules: NormalizeRule 목록
    """

    rules: Sequence[NormalizeRule] = Field(default_factory=list)

# ---------------------------------------------------------------------------
# Value Policy
# ---------------------------------------------------------------------------

class ValueNormalizePolicy(UnifyPolicyBase):
    """단일 값 정규화 정책.
    - date_fmt: 날짜 포맷 지정
    - bool_strict: 불리언 인식 범위 제한 여부
    """

    date_fmt: str = Field("%Y-%m-%d", description="날짜 문자열 변환 포맷")
    bool_strict: bool = Field(False, description="불리언 처리 시 제한적 모드")

# ---------------------------------------------------------------------------
# List Policy
# ---------------------------------------------------------------------------

class ListNormalizePolicy(UnifyPolicyBase):
    """리스트 및 시퀀스 정규화 정책.
    - sep: 구분자
    - item_cast: 항목 타입 캐스팅 함수
    - keep_empty: 빈 항목 유지 여부
    - min_len / max_len: 결과 길이 제약
    """

    sep: Optional[str] = Field(None, description="문자열 분리 구분자")
    item_cast: Optional[Callable[[Any], Any]] = Field(None, description="항목 캐스팅 함수")
    keep_empty: bool = Field(False, description="빈 항목 유지 여부")
    min_len: Optional[int] = Field(None, description="최소 길이")
    max_len: Optional[int] = Field(None, description="최대 길이")

# ---------------------------------------------------------------------------
# Resolver Policy (변수 치환 전용)
# ---------------------------------------------------------------------------

class VarsResolverPolicy(UnifyPolicyBase):
    """변수 치환 Resolver 정책 (공통 모듈)
    
    ✅ 공통 기능만 포함:
    - 환경 변수: ${ENV:default}
    - Context 변수: {{VAR}}
    - 단순 참조: ${key:default}
    
    ⚠️ 프로젝트 특정 기능 제외:
    - KeyPath 중첩 경로 (a__b__c) → keypath_utils.KeyPathResolverPolicy
    
    Examples:
        >>> # 환경 변수 + Context
        >>> policy = VarsResolverPolicy(
        ...     enable_env=True,
        ...     enable_context=True,
        ...     context={"HOST": "localhost"}
        ... )
        
        >>> # 단순 참조만
        >>> policy = VarsResolverPolicy()
    """
    
    # Placeholder 지원
    enable_env: bool = Field(False, description="환경 변수 지원 (${ENV:default})")
    enable_context: bool = Field(False, description="Context 변수 지원 ({{VAR}})")
    context: dict[str, Any] = Field(default_factory=dict, description="Context 변수 사전")

# Backward compatibility
ResolverPolicy = VarsResolverPolicy