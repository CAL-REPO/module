
# data_utils/__init__.py
# Data utilities for DataFrames, databases, dictionaries, lists, strings, and geometry.

# Structured data operations
from structured_data.core import BaseOperationsPolicy, OperationsPolicy, BaseOperationsMixin
from structured_data.composites import DFPolicy, DataFrameOps, DBPolicy, SQLiteKVStore, TranslationCache

# Legacy utilities
from data_utils.services.dict_ops import DictOps
from data_utils.services.list_ops import ListOps
from data_utils.services.string_ops import StringOps
from data_utils.services.geometry_ops import GeometryOps
from data_utils.core.types import PathLike, KeyPath, JsonDict, SectionName, FieldName, GroupedPairDict, MultiValueGroupDict

__all__ = [
    # Base classes
    "BaseOperationsPolicy", "BaseOperationsMixin",

    # DataFrame operations
    "DFPolicy", "DataFrameOps",

    # Database operations
    "DBPolicy", "SQLiteKVStore", "TranslationCache",

    # Legacy utilities
    "DictOps", "ListOps", "StringOps", "GeometryOps",

    # Types
    "PathLike", "KeyPath", "JsonDict", "SectionName", "FieldName", "GroupedPairDict", "MultiValueGroupDict",
]

