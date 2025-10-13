# -*- coding: utf-8 -*-
# xl_utils/xw_ws.py
# Excel Worksheet 단위 제어 — 셀/범위 조작 + 서식 지정 + DataFrame 변환

from __future__ import annotations
import xlwings as xw
from pathlib import Path
from typing import Any, Optional, Union
import pandas as pd


class XwWs:
    """워크시트 단위 제어"""

    def __init__(self, book: xw.Book, sheet: Union[str, int] = "Sheet1", *, create_if_missing: bool = False):
        """워크시트 컨트롤러 초기화"""
        self.book = book
        self.sheet = self._ensure_sheet(book, sheet, create_if_missing)

    # ------------------------------------------------------------------
    # 내부 유틸
    # ------------------------------------------------------------------
    def _ensure_sheet(self, book: xw.Book, sheet: Union[str, int], create_if_missing: bool) -> xw.Sheet:
        """시트 확보 (없으면 생성)"""
        try:
            return book.sheets[sheet]
        except Exception:
            if create_if_missing:
                return book.sheets.add(name=str(sheet))
            raise

    # ------------------------------------------------------------------
    # 셀 조작 메서드
    # ------------------------------------------------------------------
    def read_cell(self, cell: Union[str, tuple[int, int]]) -> Any:
        return self.sheet.range(cell).value

    def write_cell(
        self,
        row: int,
        col: int,
        value: Any,
        *,
        number_format: Optional[str] = None,
        save: bool = False,
    ):
        """행/열 좌표 기반 셀 쓰기 (xw_set_cell_value 대체)"""
        rng = self.sheet.range((row, col))
        rng.value = value
        if number_format:
            rng.number_format = number_format
        if save:
            try:
                self.book.save()
            except Exception:
                pass
        return rng

    # ------------------------------------------------------------------
    # DataFrame 변환 메서드
    # ------------------------------------------------------------------
    def to_dataframe(
        self,
        anchor: str = "A1",
        *,
        header: bool = True,
        index: bool = False,
        expand: str = "table",
        drop_empty: bool = True,
    ) -> pd.DataFrame:
        """시트 데이터를 DataFrame으로 변환"""
        df = self.sheet.range(anchor).options(pd.DataFrame, header=header, index=index, expand=expand).value
        if drop_empty and isinstance(df, pd.DataFrame):
            df = df.dropna(how="all").dropna(axis=1, how="all")
        return df

    def from_dataframe(
        self,
        df: pd.DataFrame,
        anchor: str = "A1",
        *,
        index: bool = False,
        header: bool = True,
        clear: bool = True,
    ):
        """DataFrame을 시트에 기록"""
        if clear:
            self.sheet.clear()
        self.sheet.range(anchor).options(index=index, header=header).value = df
        return True

    # ------------------------------------------------------------------
    # 유틸
    # ------------------------------------------------------------------
    def clear(self, cell: Optional[Union[str, tuple[int, int]]] = None):
        if cell:
            self.sheet.range(cell).clear()
        else:
            self.sheet.clear()

    def autofit(self, axis: str = "both"):
        self.sheet.autofit(axis)

    def used_range(self):
        return self.sheet.used_range
