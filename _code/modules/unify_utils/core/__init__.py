# -*- coding: utf-8 -*-
# unify_utils/core/__init__.py
"""unify_utils.core
==================

공통 인터페이스 및 정책 정의.
"""

from .interface import Normalizer, Resolver
from .policy import (
    NormalizePolicyBase,
    RuleNormalizePolicy,
    ValueNormalizePolicy,
    ListNormalizePolicy,
)

# Backward compatibility
NormalizerBase = Normalizer
ResolverBase = Resolver

__all__ = [
    # Interfaces
    "Normalizer",
    "Resolver",
    "NormalizerBase",  # backward compatibility
    "ResolverBase",    # backward compatibility
    # Policies
    "NormalizePolicyBase",
    "RuleNormalizePolicy",
    "ValueNormalizePolicy",
    "ListNormalizePolicy",
]
