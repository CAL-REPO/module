# -*- coding: utf-8 -*-
# data_utils/list_ops.py

from __future__ import annotations

from typing import Any, List, Iterable

class ListOps:
    """리스트 관련 유틸리티 함수 모음"""
    @staticmethod
    def dedupe_keep_order(seq: Iterable[Any]) -> List[Any]:
        seen: set[Any] = set()
        out: List[Any] = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out





