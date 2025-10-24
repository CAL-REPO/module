# -*- coding: utf-8 -*-
"""Adapters for xl_utils.

비즈니스 로직 (target 없음):
- ExcelLoad: 순수 Excel 로드 및 조작 로직

Adapter는 target을 받지 않고 데이터를 인자로 받아 처리합니다.
EntryPoint가 target에서 데이터를 로드하여 Adapter에 전달합니다.
"""

from .excel_load import ExcelLoad

__all__ = [
    "ExcelLoad",
]
