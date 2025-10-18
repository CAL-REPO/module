# -*- coding: utf-8 -*-
"""keypath_utils - KeyPath 기반 dict 접근 및 상태 관리
====================================================

KeyPath 표기법으로 nested dict를 간편하게 접근하고 관리합니다.
구분자: `__` (프로젝트 표준)

✅ 프로젝트 특정 기능:
- KeyPath 중첩 경로 (a__b__c)
- "__" 구분자 (copilot-instructions.md 규칙)
- unify_utils의 공통 기능 확장
"""

from .core import KeyPathAccessor, KeyPathStatePolicy, KeyPathResolverPolicy
from .services import KeyPathDict, KeyPathState, KeyPathNormalizer, KeyPathVarsResolver, KeyPathMerger, KeyPathMergePolicy

# Backward compatibility
KeyPathModel = KeyPathDict
KeyPathReferenceResolver = KeyPathVarsResolver

__all__ = [
    # Core
    "KeyPathAccessor",
    "KeyPathStatePolicy",
    "KeyPathResolverPolicy",
    
    # Services
    "KeyPathDict",
    "KeyPathState",
    "KeyPathNormalizer",
    "KeyPathVarsResolver",
    "KeyPathMerger",
    "KeyPathMergePolicy",
    
    # Backward compatibility
    "KeyPathModel",
    "KeyPathReferenceResolver",
]
