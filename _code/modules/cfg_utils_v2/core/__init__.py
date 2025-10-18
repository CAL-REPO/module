# -*- coding: utf-8 -*-
"""cfg_utils_v2.core - Core Configuration Components.

Low-level core components for configuration management.
"""

from .interface import ConfigSource
from .policy import ConfigLoaderPolicy, NormalizePolicy

__all__ = [
    # Interface
    "ConfigSource",
    # Policy
    "ConfigLoaderPolicy",
    "NormalizePolicy",
]
