"""
data_utils.core
---------------
Core type definitions and base utilities for data_utils modules.
Exports only intended API.
"""
from .types import PathLike, KeyPath, JsonDict, SectionName, FieldName, GroupedPairDict, MultiValueGroupDict

__all__ = [
    "PathLike",
    "KeyPath",
    "JsonDict",
    "SectionName",
    "FieldName",
    "GroupedPairDict",
    "MultiValueGroupDict",
]
