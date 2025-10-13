# -*- coding: utf-8 -*-
# data_utils/string_ops.py

from typing import List

class StringOps:
    """문자열 관련 유틸리티 함수 모음"""
    @staticmethod
    def split_str_path(path: str, sep: str = ".") -> List[str]:
        """구분자를 기준으로 문자열을 분할하고 빈 값은 제거

        예:
        "a.b.c" → ["a", "b", "c"]
        "a//b/c" (sep="/") → ["a", "b", "c"]
        """
        return [p for p in path.split(sep) if p]
