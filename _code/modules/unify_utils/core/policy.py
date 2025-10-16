# -*- coding: utf-8 -*-
# filename: unify_utils/core/policy.py
# description: unify_utils.core — Normalizer용 Pydantic Policy 모델 정의
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


class NormalizePolicyBase(BaseModel):
    """모든 Normalizer 정책 클래스의 기반.

    Base Normalizer에서 공통으로 사용하는 설정 항목을 정의하며,
    - recursive: 내부 구조 재귀 적용 여부
    - strict: 예외 발생 시 예외 전파 여부
    """

    recursive: bool = Field(False, description="dict/list 등 내부 구조 재귀 처리 여부")
    strict: bool = Field(False, description="오류 발생 시 예외 전파 여부")


# ---------------------------------------------------------------------------
# Rule Policy
# ---------------------------------------------------------------------------

class RuleNormalizePolicy(NormalizePolicyBase):
    """정규식 기반 정규화 정책.
    - rules: NormalizeRule 목록
    """

    rules: Sequence[NormalizeRule] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Value Policy
# ---------------------------------------------------------------------------

class ValueNormalizePolicy(NormalizePolicyBase):
    """단일 값 정규화 정책.
    - date_fmt: 날짜 포맷 지정
    - bool_strict: 불리언 인식 범위 제한 여부
    """

    date_fmt: str = Field("%Y-%m-%d", description="날짜 문자열 변환 포맷")
    bool_strict: bool = Field(False, description="불리언 처리 시 제한적 모드")


# ---------------------------------------------------------------------------
# List Policy
# ---------------------------------------------------------------------------

class ListNormalizePolicy(NormalizePolicyBase):
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

class KeyPathNormalizePolicy(NormalizePolicyBase):
    """KeyPathNormalizer 전용 정책

    Attributes:
        sep: 구분자 (기본값: ".")
        collapse: 연속 구분자 병합 여부 (빈 세그먼트 제거)
        accept_dot: sep 없을 때 "." fallback 허용 여부
        escape_char: 이스케이프 문자 (구분자를 리터럴로 처리)
        enable_list_index: [0], [1] 형태 배열 인덱스 지원 (향후 확장용)
    """
    sep: str = Field(default=".", description="경로 구분자")
    collapse: bool = Field(default=True, description="빈 세그먼트 제거 여부")
    accept_dot: bool = Field(default=True, description="구분자 실패 시 '.' fallback 허용")
    escape_char: Optional[str] = Field(default="\\", description="이스케이프 문자")
    enable_list_index: bool = Field(default=False, description="배열 인덱스 지원 [0], [1]")