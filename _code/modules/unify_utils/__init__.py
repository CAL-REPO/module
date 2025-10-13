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
from .core.normalizer_base import NormalizerBase
from .core.resolver_base import ResolverBase
from .core.base import (
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
from .normalizers.rule_normalizer import RuleBasedNormalizer
from .normalizers.value_normalizer import ValueNormalizer
from .normalizers.list_normalizer import ListNormalizer
from .normalizers.keypath_normalizer import KeyPathNormalizer

# ---------------------------------------------------------------------------
# Resolvers (신규 노출)
# ---------------------------------------------------------------------------
from .normalizers.placeholder_resolver import PlaceholderResolver
from .normalizers.reference_resolver import ReferenceResolver

# ---------------------------------------------------------------------------
# Convenience factory helpers
# ---------------------------------------------------------------------------
from typing import Sequence

def rule_normalizer(*, rules: Sequence[NormalizeRule] | None = None,
                    recursive: bool = False, strict: bool = False) -> RuleBasedNormalizer:
    from .core.base import RuleNormalizePolicy
    policy = RuleNormalizePolicy(rules=rules or [], recursive=recursive, strict=strict)
    return RuleBasedNormalizer(policy)

def value_normalizer(*, date_fmt: str = "%Y-%m-%d",
                     bool_strict: bool = False, recursive: bool = False, strict: bool = False) -> ValueNormalizer:
    from .core.base import ValueNormalizePolicy
    policy = ValueNormalizePolicy(date_fmt=date_fmt, bool_strict=bool_strict, recursive=recursive, strict=strict)
    return ValueNormalizer(policy)

def list_normalizer(*, sep: str | None = None,
                    item_cast=None, keep_empty: bool = False,
                    min_len: int | None = None, max_len: int | None = None,
                    recursive: bool = False, strict: bool = False) -> ListNormalizer:
    from .core.base import ListNormalizePolicy
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
