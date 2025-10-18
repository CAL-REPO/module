# -*- coding: utf-8 -*-
"""cfg_utils_v2.adapter - High-level Adapters.

High-level adapters for specific use cases.
"""

from .cfg_loader import CfgLoader
from .cfg_loader_policy import CfgLoaderPolicy

__all__ = ['CfgLoader', 'CfgLoaderPolicy']
