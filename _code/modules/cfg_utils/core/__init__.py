# -*- coding: utf-8 -*-
"""cfg_utils_v2.core - Core Configuration Components.

Low-level core components for configuration management.
"""

from .interface import SourceBase
from .policy import (
    # 기본 정책
    MergePolicy,
    NormalizePolicy,
    # 통합 소스 정책 (단일 진입점)
    SourcePolicy,
    # ConfigLoader 정책
    ConfigLoaderPolicy,
)

__all__ = [
    # Interface
    "SourceBase",
    # 기본 정책
    "MergePolicy",
    "NormalizePolicy",
    # 통합 소스 정책
    "SourcePolicy",
    # ConfigLoader 정책
    "ConfigLoaderPolicy",
]
