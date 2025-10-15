
# -*- coding: utf-8 -*-
"""
data_utils.core.types
---------------------
Type definitions and aliases for data structures used throughout data_utils modules.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, Sequence
from pydantic import BaseModel

# =======================================================
# ✅ 공통 타입 정의 (전 모듈 공통 import 용)
# =======================================================

T = TypeVar("T", bound=BaseModel)

PathLike = Union[str, Path]
"""A path-like type representing either a string or a :class:`pathlib.Path`."""

PathsLike = Sequence[Union[str, Path]]

KeyPath = Union[str, List[str]]
"""A key path used for dictionary navigation.

May be provided as a dotted string (e.g. ``"a.b.c"``) or as a list of keys (e.g. ``["a", "b", "c"]``).
"""

JsonDict = Dict[str, Any]
"""Base type for JSON-like dictionary structures."""

SectionName = Optional[str]
"""Name of a section (e.g. the key of a grouped data block)."""

FieldName = Optional[str]
"""Key for a data item (e.g. a column name or label)."""

# =======================================================
# ✅ 그룹 구조 관련 타입
# =======================================================

GroupedPairDict = Dict[SectionName, List[Tuple[FieldName, Any]]]
"""Type alias for a dictionary mapping section names to lists of ``(key, value)`` tuples.

Example::

    {
        "user": [("name", "Alice"), ("age", 30)],
        "meta": [("source", "API")],
        None: [("note", "unlabeled")]
    }
"""

MultiValueGroupDict = Dict[SectionName, Dict[FieldName, List[Any]]]
"""Type alias for a dictionary mapping section names to dictionaries of keys and lists of values.

Example::

    {
        "user": {
            "name": ["Alice", "Alicia"],
            "age": [30]
        },
        None: {
            "note": ["unlabeled"]
        }
    }
"""