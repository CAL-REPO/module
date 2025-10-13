# -*- coding: utf-8 -*-
# filename: unify_utils/__init__.py
# description: Public package entrypoint — 핵심 클래스 재노출 및 편의 팩토리 제공
from __future__ import annotations

"""unify_utils — 데이터 정규화·표준화 유틸리티 패키지

Public API
----------
- Base & Policy
  - NormalizerBase
  - PolicyBase, RulePolicy, ValuePolicy, ListPolicy

- Rules & Presets
  - NormalizeRule, RuleType, LetterCase, RegexFlag
  - RulePresets

- Normalizers (실행 엔진)
  - RuleBasedNormalizer, ValueNormalizer, ListNormalizer, ReferenceResolver

- Convenience factories
  - rule_normalizer(), value_normalizer(), list_normalizer(), reference_resolver()
"""

__version__ = "0.1.0"

from typing import Sequence
# Base / Policy
from .core.base import NormalizerBase
from .core.policy import NormalizePolicyBase, RuleNormalizePolicy, ValueNormalizePolicy, ListNormalizePolicy


# Rules / Presets (단일 소스)
from .presets.rules import (
    NormalizeRule,
    RuleType,
    LetterCase,
    RegexFlag,
    RulePresets,
)

# Normalizers
from .normalizers.rule_normalizer import RuleBasedNormalizer
from .normalizers.value_normalizer import ValueNormalizer
from .normalizers.list_normalizer import ListNormalizer
from .normalizers.reference_resolver import ReferenceResolver

# ---------------------------------------------------------------------------
# Convenience factories
# ---------------------------------------------------------------------------

def rule_normalizer(
    *,
    rules: Sequence[NormalizeRule] | None = None,
    recursive: bool = False,
    strict: bool = False,
) -> RuleBasedNormalizer:
    from .core.policy import RuleNormalizePolicy
    policy = RuleNormalizePolicy(rules=rules if rules is not None else [], recursive=recursive, strict=strict)
    return RuleBasedNormalizer(policy)


def value_normalizer(
    *,
    date_fmt: str = "%Y-%m-%d",
    bool_strict: bool = False,
    recursive: bool = False,
    strict: bool = False,
) -> ValueNormalizer:
    from .core.policy import ValueNormalizePolicy
    policy = ValueNormalizePolicy(
        date_fmt=date_fmt,
        bool_strict=bool_strict,
        recursive=recursive,
        strict=strict,
    )
    return ValueNormalizer(policy)


def list_normalizer(
    *,
    sep: str | None = None,
    item_cast=None,
    keep_empty: bool = False,
    min_len: int | None = None,
    max_len: int | None = None,
    recursive: bool = False,
    strict: bool = False,
) -> ListNormalizer:
    from .core.policy import ListNormalizePolicy
    policy = ListNormalizePolicy(
        sep=sep,
        item_cast=item_cast,
        keep_empty=keep_empty,
        min_len=min_len,
        max_len=max_len,
        recursive=recursive,
        strict=strict,
    )
    return ListNormalizer(policy)


def reference_resolver(
    data: dict,
    *,
    recursive: bool = True,
    strict: bool = False,
) -> ReferenceResolver:
    """ReferenceResolver 를 간단히 생성하는 팩토리"""
    return ReferenceResolver(data, recursive=recursive, strict=strict)


__all__ = [
    # Base
    "NormalizerBase",

    # Policy
    "NormalizePolicyBase",
    "RuleNormalizePolicy",
    "ValueNormalizePolicy",
    "ListNormalizePolicy",

    # Rules / Presets
    "NormalizeRule",
    "RuleType",
    "LetterCase",
    "RegexFlag",
    "RulePresets",

    # Normalizers
    "RuleBasedNormalizer",
    "ValueNormalizer",
    "ListNormalizer",
    "ReferenceResolver",

    # Factories
    "rule_normalizer",
    "value_normalizer",
    "list_normalizer",
    "reference_resolver",
]
