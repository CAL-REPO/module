# -*- coding: utf-8 -*-
# data_utils/types.py

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# =======================================================
# ✅ 공통 타입 정의 (전 모듈 공통 import 용)
# =======================================================

PathLike = Union[str, Path]
"""파일 경로로 사용 가능한 str 또는 pathlib.Path 객체"""

KeyPath = Union[str, List[str]]
"""딕셔너리 탐색에 사용되는 키 경로: "a.b.c" 또는 ["a", "b", "c"] 형태"""

JsonDict = Dict[str, Any]
"""JSON 구조(dict) 표현용 기본 타입"""

SectionName = Optional[str]
"""섹션 이름 (예: 그룹화된 데이터 블록의 키)"""

FieldName = Optional[str]
"""데이터 항목의 키 (예: 컬럼 이름, 라벨 등)"""

# =======================================================
# ✅ 그룹 구조 관련 타입
# =======================================================

GroupedPairDict = Dict[SectionName, List[Tuple[FieldName, Any]]]
"""
section → (key, value) 목록

예시:
{
    "user": [("name", "Alice"), ("age", 30)],
    "meta": [("source", "API")],
    None: [("note", "unlabeled")]
}
"""

MultiValueGroupDict = Dict[SectionName, Dict[FieldName, List[Any]]]
"""
section → key → [value1, value2, ...]

예시:
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