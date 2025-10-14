# -*- coding: utf-8 -*-
# filename: unify_utils/__init__.py
# description: unify_utils — 데이터 정규화·참조 해석·플레이스홀더 치환 유틸리티 패키지

from __future__ import annotations

"""
unify_utils — 데이터 정규화 및 해석(Resolver) 유틸리티 모듈

Public API
-----------
- Base & Policy
  - NormalizerBase
  - NormalizePolicyBase
  - RuleNormalizePolicy, ValueNormalizePolicy, ListNormalizePolicy, KeyPathNormalizePolicy

- Rules & Presets
  - NormalizeRule, RuleType, LetterCase, RegexFlag, RulePresets

- Normalizers
  - RuleBasedNormalizer, ValueNormalizer, ListNormalizer, KeyPathNormalizer

- Resolvers
  - PlaceholderResolver, ReferenceResolver

- Factory Helpers
  - rule_normalizer(), value_normalizer(), list_normalizer(), reference_resolver(), placeholder_resolver()
"""

# ---------------------------------------------------------------------------
# Base / Policy
# ---------------------------------------------------------------------------
from .core.base_normalizer import NormalizerBase
from .core.base_resolver import ResolverBase
from .core.policy import (
    NormalizePolicyBase,
    RuleNormalizePolicy,
    ValueNormalizePolicy,
    ListNormalizePolicy,
    KeyPathNormalizePolicy,
)

# ---------------------------------------------------------------------------
# Rules / Presets
# ---------------------------------------------------------------------------
from .presets.rules import (
    NormalizeRule,
    RuleType,
    LetterCase,
    RegexFlag,
    RulePresets,
)

# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------
from .normalizers.normalizer_rule import RuleBasedNormalizer
from .normalizers.normalizer_value import ValueNormalizer
from .normalizers.normalizer_list import ListNormalizer
from .normalizers.normalizer_keypath import KeyPathNormalizer

# ---------------------------------------------------------------------------
# Resolvers (신규 노출)
# ---------------------------------------------------------------------------
from .normalizers.resolver_placeholder import PlaceholderResolver
from .normalizers.resolver_reference import ReferenceResolver

# ---------------------------------------------------------------------------
# Convenience factory helpers
# ---------------------------------------------------------------------------
from typing import Sequence

def rule_normalizer(*, rules: Sequence[NormalizeRule] | None = None,
                    recursive: bool = False, strict: bool = False) -> RuleBasedNormalizer:
    from .core.policy import RuleNormalizePolicy
    policy = RuleNormalizePolicy(rules=rules or [], recursive=recursive, strict=strict)
    return RuleBasedNormalizer(policy)

def value_normalizer(*, date_fmt: str = "%Y-%m-%d",
                     bool_strict: bool = False, recursive: bool = False, strict: bool = False) -> ValueNormalizer:
    from .core.policy import ValueNormalizePolicy
    policy = ValueNormalizePolicy(date_fmt=date_fmt, bool_strict=bool_strict, recursive=recursive, strict=strict)
    return ValueNormalizer(policy)

def list_normalizer(*, sep: str | None = None,
                    item_cast=None, keep_empty: bool = False,
                    min_len: int | None = None, max_len: int | None = None,
                    recursive: bool = False, strict: bool = False) -> ListNormalizer:
    from .core.policy import ListNormalizePolicy
    policy = ListNormalizePolicy(
        sep=sep, item_cast=item_cast, keep_empty=keep_empty,
        min_len=min_len, max_len=max_len, recursive=recursive, strict=strict)
    return ListNormalizer(policy)

def reference_resolver(data: dict, *, recursive: bool = True, strict: bool = False) -> ReferenceResolver:
    """ReferenceResolver 팩토리"""
    return ReferenceResolver(data, recursive=recursive, strict=strict)

def placeholder_resolver(context: dict | None = None, *, recursive: bool = False, strict: bool = False) -> PlaceholderResolver:
    """PlaceholderResolver 팩토리"""
    return PlaceholderResolver(context or {}, recursive=recursive, strict=strict)

# ---------------------------------------------------------------------------
# 공개 인터페이스
# ---------------------------------------------------------------------------
__all__ = [
    # Base / Policy
    "NormalizerBase", "ResolverBase",
    "NormalizePolicyBase",
    "RuleNormalizePolicy", "ValueNormalizePolicy",
    "ListNormalizePolicy", "KeyPathNormalizePolicy",

    # Rules
    "NormalizeRule", "RuleType", "LetterCase", "RegexFlag", "RulePresets",

    # Normalizers
    "RuleBasedNormalizer", "ValueNormalizer",
    "ListNormalizer", "KeyPathNormalizer",

    # Resolvers
    "PlaceholderResolver", "ReferenceResolver",

    # Factory helpers
    "rule_normalizer", "value_normalizer",
    "list_normalizer", "reference_resolver",
    "placeholder_resolver",
]
