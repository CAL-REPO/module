# -*- coding: utf-8 -*-
# keypath_utils/services/__init__.py
"""keypath_utils.services
=========================

KeyPath 관련 서비스 모듈.
"""

from .resolver import KeyPathVarsResolver
from .state import KeyPathState
from .dict import KeyPathDict
from .normalizer import KeyPathNormalizer
from .merger import KeyPathMerger, KeyPathMergePolicy

# Backward compatibility
KeyPathModel = KeyPathDict
KeyPathReferenceResolver = KeyPathVarsResolver

__all__ = [
    "KeyPathVarsResolver",
    "KeyPathState",
    "KeyPathDict",
    "KeyPathNormalizer",
    "KeyPathMerger",
    "KeyPathMergePolicy",
    
    # Backward compatibility
    "KeyPathModel",
    "KeyPathReferenceResolver",
]
