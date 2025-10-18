# -*- coding: utf-8 -*-
# filename: unify_utils/__init__.py
# description: unify_utils — 데이터 정규화·참조 해석·플레이스홀더 치환 유틸리티 패키지

from __future__ import annotations

"""
unify_utils — 데이터 정규화 및 해석(Resolver) 유틸리티 모듈

Public API
-----------
- Base & Policy
  - Normalizer, Resolver
  - UnifyPolicyBase, VarsResolverPolicy
  - RuleNormalizePolicy, ValueNormalizePolicy, ListNormalizePolicy

- Rules & Presets
  - NormalizeRule, RuleType, LetterCase, RegexFlag, RulePresets

- Normalizers
  - RuleBasedNormalizer, ValueNormalizer, ListNormalizer

- Resolvers
  - VarsResolver (변수 치환 Resolver) ⭐ 권장
  - ReferenceResolver (단순 참조, 레거시)
  - PlaceholderResolver (환경변수, 레거시)

- Factory Helpers
  - rule_normalizer(), value_normalizer(), list_normalizer()
  - vars_resolver() (권장)
"""

# ---------------------------------------------------------------------------
# Base / Policy
# ---------------------------------------------------------------------------
from .core.interface import Normalizer
from .core.interface import Resolver
from .core.policy import (
    UnifyPolicyBase,
    VarsResolverPolicy,
    RuleNormalizePolicy,
    ValueNormalizePolicy,
    ListNormalizePolicy,
)

# Backward compatibility
NormalizePolicyBase = UnifyPolicyBase
ResolverPolicy = VarsResolverPolicy

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
from .normalizers.rule import RuleBasedNormalizer
from .normalizers.value import ValueNormalizer
from .normalizers.list import ListNormalizer

# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------
from .resolver.vars import VarsResolver

# Backward compatibility
UnifiedResolver = VarsResolver

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

def vars_resolver(
    data: dict,
    *,
    enable_env: bool = False,
    enable_context: bool = False,
    context: dict | None = None,
    recursive: bool = True,
    strict: bool = False
) -> VarsResolver:
    """VarsResolver 팩토리 (권장)
    
    ⚠️ KeyPath 중첩 경로는 미지원 (a__b__c)
    중첩 경로 필요 시 keypath_utils.KeyPathVarsResolver 사용
    
    Args:
        data: 참조 소스 데이터
        enable_env: 환경 변수 지원 (${ENV:default})
        enable_context: Context 변수 지원 ({{VAR}})
        context: Context 변수 사전
        recursive: 재귀적 구조 처리
        strict: 오류 시 예외 발생
    
    Examples:
        >>> # 단순 참조
        >>> resolver = vars_resolver({"host": "api.com", "url": "${host}"})
        
        >>> # 환경변수 + Context
        >>> resolver = vars_resolver(
        ...     data,
        ...     enable_env=True,
        ...     enable_context=True,
        ...     context={"HOST": "localhost"}
        ... )
    """
    from .core.policy import VarsResolverPolicy
    policy = VarsResolverPolicy(
        recursive=recursive,
        strict=strict,
        enable_env=enable_env,
        enable_context=enable_context,
        context=context or {}
    )
    return VarsResolver(data, policy)

# Backward compatibility
unified_resolver = vars_resolver

# ---------------------------------------------------------------------------
# 공개 인터페이스
# ---------------------------------------------------------------------------
__all__ = [
    # Base / Policy
    "Normalizer", "Resolver",
    "UnifyPolicyBase", "VarsResolverPolicy",
    "RuleNormalizePolicy", "ValueNormalizePolicy",
    "ListNormalizePolicy",
    "NormalizePolicyBase",  # Backward compatibility
    "ResolverPolicy",  # Backward compatibility

    # Rules
    "NormalizeRule", "RuleType", "LetterCase", "RegexFlag", "RulePresets",

    # Normalizers
    "RuleBasedNormalizer", "ValueNormalizer",
    "ListNormalizer",

    # Resolvers
    "VarsResolver",
    "UnifiedResolver",  # Backward compatibility

    # Factory helpers
    "rule_normalizer", "value_normalizer",
    "list_normalizer",
    "vars_resolver",  # 권장
    "unified_resolver",  # Backward compatibility
]

