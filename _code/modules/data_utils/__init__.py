# -*- coding: utf-8 -*-
# data_utils/__init__.py
"""Data utilities for various data structures.

This module provides utilities for working with different data types:
- DataFrames (via structured_data.composites.DataFrameOps)
- Databases (via structured_data.composites.SQLiteKVStore)
- Dictionaries (via DictOps)
- Lists (via ListOps)
- Strings (via StringOps)
- Geometric data (via GeometryOps)
"""

# Structured data operations (NEW: role-based mixin architecture)
from modules.structured_data.core import (
    BaseOperationsPolicy,
    BaseOperationsMixin,
)
from modules.structured_data.composites import (
    DFPolicy,
    DataFrameOps,
    DBPolicy,
    SQLiteKVStore,
    TranslationCache,
)

# Legacy utilities (kept for backward compatibility)
from .dict_ops import DictOps
from .list_ops import ListOps
from .string_ops import StringOps
from .geometry_ops import GeometryOps
from .types import PathLike, KeyPath, JsonDict, SectionName, FieldName, GroupedPairDict, MultiValueGroupDict

__all__ = [
    # Base classes (shared foundation)
    "BaseOperationsPolicy",
    "BaseOperationsMixin",
    
    # DataFrame operations
    "DFPolicy",
    "DataFrameOps",
    
    # Database operations
    "DBPolicy",
    "SQLiteKVStore",
    "TranslationCache",
    
    # Legacy utilities
    "DictOps",
    "ListOps",
    "StringOps",
    "GeometryOps",
    
    # Types
    "PathLike",
    "KeyPath",
    "JsonDict",
    "SectionName",
    "FieldName",
    "GroupedPairDict",
    "MultiValueGroupDict",
]

