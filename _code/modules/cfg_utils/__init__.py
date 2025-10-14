
# -*- coding: utf-8 -*-
# cfg_utils/__init__.py
# Unified configuration loading and normalization utilities.
# Provides ConfigLoader, ConfigNormalizer, ConfigPolicy for YAML/dict/model merging and normalization.

from __future__ import annotations

# Core API
from cfg_utils.core.policy import ConfigPolicy
from cfg_utils.services.normalizer import ConfigNormalizer
from cfg_utils.loader import ConfigLoader

# External dependencies
from unify_utils import ReferenceResolver

# __all__ grouped by role
# Core API
__all__ = [
    "ConfigLoader",
    "ConfigNormalizer",
    "ConfigPolicy",

    # External dependencies
    "ReferenceResolver",
]
