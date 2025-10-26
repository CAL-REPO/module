# -*- coding: utf-8 -*-
"""Adapters for xl_utils.

비즈니스 로직:
- ExcelLoad: Excel 파일 접근 및 조작 로직

Adapter는 파일/시트 경로를 인자로 받아 처리합니다.
"""

from .excel_load import ExcelLoad

__all__ = [
    "ExcelLoad",
]
