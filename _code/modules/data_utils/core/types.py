
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
from enum import Flag, auto

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
# ✅ Blank 값 타입 정의 (Flag 기반)
# =======================================================

class BlankType(Flag):
    """Blank 값 타입 정의 (비트 플래그)
    
    DictOps.process_blanks()에서 사용하는 blank 값 타입.
    비트 플래그로 여러 타입을 조합 가능.
    
    Examples:
        >>> # 단일 타입
        >>> BlankType.NONE
        >>> BlankType.EMPTY_STR
        
        >>> # 조합
        >>> BlankType.NONE | BlankType.EMPTY_STR
        >>> BlankType.EMPTY_STRINGS  # EMPTY_STR | WHITESPACE
        
        >>> # 프리셋 사용
        >>> BlankType.STANDARD  # None + 모든 빈 문자열
        >>> BlankType.ALL       # 모든 blank 타입
    """
    
    # 기본 타입
    NONE = auto()           # None
    EMPTY_STR = auto()      # "" (빈 문자열)
    WHITESPACE = auto()     # "  " (공백만 있는 문자열)
    EMPTY_LIST = auto()     # []
    EMPTY_DICT = auto()     # {}
    EMPTY_TUPLE = auto()    # ()
    EMPTY_SET = auto()      # set()
    
    # 조합 상수
    EMPTY_STRINGS = EMPTY_STR | WHITESPACE
    """빈 문자열 + 공백 문자열"""
    
    EMPTY_CONTAINERS = EMPTY_LIST | EMPTY_DICT | EMPTY_TUPLE | EMPTY_SET
    """빈 컨테이너 (list, dict, tuple, set)"""
    
    # 프리셋
    MINIMAL = NONE
    """최소: None만"""
    
    BASIC = NONE | EMPTY_STR
    """기본: None + 빈 문자열 (공백 제외)"""
    
    STANDARD = NONE | EMPTY_STRINGS
    """표준: None + 모든 빈 문자열 (공백 포함)"""
    
    ALL = NONE | EMPTY_STRINGS | EMPTY_CONTAINERS
    """전체: 모든 blank 타입"""

# =======================================================
# ✅ Config 소스 관련 타입
# =======================================================

BaseModelWithSection = Tuple[BaseModel, SectionName]
"""A tuple of (BaseModel instance, section name).

Example::

    (TranslatePolicy(...), "translate")
"""

DictWithSection = Tuple[Dict[str, Any], SectionName]
"""A tuple of (dict, section name).

Example::

    ({"provider": "deepl"}, "translate")
"""

ConfigSourceWithSection = List[Union[BaseModelWithSection, DictWithSection, PathLike, PathsLike, None]]
"""Union type for config sources with explicit section.

Example::

    sources: List[ConfigSourceWithSection] = [
        (TranslatePolicy(...), "translate"),
        ({"zh": {"mode": "off"}}, "translate")
    ]
"""

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