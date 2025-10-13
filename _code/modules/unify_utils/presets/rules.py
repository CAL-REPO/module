# -*- coding: utf-8 -*-
# filename: unify_utils/presets/rules.py
# description: unify_utils.presets — NormalizeRule, Enum, RulePresets 정의
from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RuleType(str, Enum):
    """정규화 룰의 적용 방식"""
    REGEX = "regex"  # 정규표현식 기반 치환
    CLEAN = "clean"  # strip, 대소문자 변환 등


class LetterCase(str, Enum):
    """문자열 대소문자 처리 방식"""
    LOWER = "lower"
    UPPER = "upper"


class RegexFlag(str, Enum):
    """정규표현식 플래그 옵션"""
    IGNORECASE = "i"


# ---------------------------------------------------------------------------
# NormalizeRule Model
# ---------------------------------------------------------------------------

class NormalizeRule(BaseModel):
    """입력 문자열에 적용할 정규화 규칙 정의.

    - rule_type: 적용 방식 (regex 또는 clean)
    - pattern, replace, flags: regex 치환용 옵션
    - strip, lettercase: 문자열 정제용 옵션
    """

    rule_type: RuleType = RuleType.REGEX
    pattern: Optional[str] = None
    replace: Optional[str] = None
    flags: Optional[List[RegexFlag]] = None
    strip: bool = False
    lettercase: Optional[LetterCase] = None

    @model_validator(mode="before")
    def validate_fields(cls, values):
        if values.get("rule_type") == RuleType.REGEX and not values.get("pattern"):
            raise ValueError("pattern must be provided for regex rules")
        return values


# ---------------------------------------------------------------------------
# RulePresets
# ---------------------------------------------------------------------------

class RulePresets:
    """자주 사용하는 NormalizeRule 프리셋 모음"""

    BASIC_CLEAN: List[NormalizeRule] = [
        NormalizeRule(rule_type=RuleType.CLEAN, strip=True, lettercase=LetterCase.LOWER),
    ]

    FILENAME_SAFE: List[NormalizeRule] = [
        NormalizeRule(rule_type=RuleType.REGEX, pattern=r"[\\/:*?\"<>|]+", replace="_"),
        NormalizeRule(rule_type=RuleType.REGEX, pattern=r"\s+", replace=" "),
        NormalizeRule(rule_type=RuleType.CLEAN, strip=True),
    ]