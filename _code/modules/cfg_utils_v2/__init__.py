# -*- coding: utf-8 -*-
"""cfg_utils_v2 - Configuration Management v2.

3-Tier Architecture:
- core/: Low-level components (Source, Merger, Normalizer)
- service/: Mid-level services (ConfigLoader)
- adapter/: High-level adapters (CfgLoader)

Usage:
    >>> # Import ConfigLoader for direct use
    >>> from cfg_utils_v2.service import ConfigLoader
    >>> policy = ConfigLoader.load(cfg_like="config__yaml", model=MyPolicy)
    
    >>> # Import CfgLoader for policy files
    >>> from cfg_utils_v2.adapter import CfgLoader
    >>> cfg_loader = CfgLoader("cfg_loader__yaml")
    >>> data = cfg_loader.extract("section")
"""

# Core components
from .core import (
    SourceBase,
    SourcePolicy,
    NormalizePolicy,
    MergePolicy,
)

# Service layer
from .service import ConfigLoader, UnifiedSource

__all__ = [
    # Core
    'SourceBase',
    'SourcePolicy',
    'NormalizePolicy',
    'MergePolicy',
    # Service
    'ConfigLoader',
    'UnifiedSource',
]

__version__ = '2.0.0'
