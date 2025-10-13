# -*- coding: utf-8 -*-
# data_utils/__init__.py

# Primary exports
from .format_ops import FormatOps
from .structure_ops import StructureOps

# DataFrame operations
from .df_ops import DataFrameOps  # unified mixin-based entry point
from .df_ops.base import DataFramePolicy  # unified policy class

# Core utilities
from .dict_ops import DictOps
from .list_ops import ListOps
from .string_ops import StringOps

# Deprecated aliases for backward compatibility
from .format_ops import FormatOps as Convert  # alias to maintain import compatibility
from .structure_ops import StructureOps as TransOps  # alias to maintain import compatibility

# Type aliases
from .types import (
    PathLike,
    KeyPath,
    JsonDict,
    SectionName,
    FieldName,
    GroupedPairDict,
    MultiValueGroupDict,
)

__all__ = [
    "FormatOps",
    "StructureOps",
    "DataFramePolicy",
    "DataFrameOps",
    "DictOps",
    "ListOps",
    "StringOps",
    # types
    "PathLike",
    "KeyPath",
    "JsonDict",
    "SectionName",
    "FieldName",
    "GroupedPairDict",
    "MultiValueGroupDict",
]
