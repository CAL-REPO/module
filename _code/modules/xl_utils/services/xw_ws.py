# -*- coding: utf-8 -*-
# xl_utils/xw_ws.py
# Excel Worksheet 단위 제어 (SRP 준수 버전)

from __future__ import annotations
import xlwings as xw
from typing import Any, Optional, Union
import pandas as pd
from xl_utils.core.policy import XwWsPolicy
from xl_utils.save_manager import XwSaveManager


class XwWsSheetResolver:
    """Worksheet 확보 및 생성 전담"""
    
    def __init__(self, book: xw.Book, policy: XwWsPolicy):
        self.book = book
        self.policy = policy
    
    def resolve(self, sheet: Union[str, int]) -> xw.Sheet:
        """시트 확보 (없으면 정책에 따라 생성)"""
        try:
            return self.book.sheets[sheet]
        except Exception:
            if self.policy.create_if_missing:
                return self.book.sheets.add(name=str(sheet))
            raise


class XwWsCellOps:
    """셀 단위 읽기/쓰기 전담"""
    
    def __init__(self, sheet: xw.Sheet, save_manager: XwSaveManager, policy: XwWsPolicy):
        self.sheet = sheet
        self.save_manager = save_manager
        self.policy = policy
    
    def read(self, cell: Union[str, tuple[int, int]]) -> Any:
        """셀 읽기"""
        return self.sheet.range(cell).value
    
    def write(
        self,
        row: int,
        col: int,
        value: Any,
        *,
        number_format: Optional[str] = None,
        save: bool = False,
    ) -> xw.Range:
        """셀 쓰기"""
        rng = self.sheet.range((row, col))
        rng.value = value
        
        if number_format:
            rng.number_format = number_format
        
        if save or self.policy.auto_save_on_write:
            self.save_manager.save_workbook(self.sheet.book)
        
        return rng


class XwWsDataFrameOps:
    """DataFrame 변환 전담"""
    
    def __init__(self, sheet: xw.Sheet, policy: XwWsPolicy):
        self.sheet = sheet
        self.policy = policy
    
    def to_dataframe(
        self,
        anchor: str = "A1",
        *,
        header: bool = True,
        index: bool = False,
        expand: str = "table",
    ) -> pd.DataFrame:
        """시트 데이터를 DataFrame으로 변환"""
        df = self.sheet.range(anchor).options(
            pd.DataFrame,
            header=header,
            index=index,
            expand=expand
        ).value
        
        if self.policy.drop_empty_rows and isinstance(df, pd.DataFrame):
            df = df.dropna(how="all").dropna(axis=1, how="all")
        
        return df
    
    def from_dataframe(
        self,
        df: pd.DataFrame,
        anchor: str = "A1",
        *,
        index: bool = False,
        header: bool = True,
        clear: bool = None,
    ) -> bool:
        """DataFrame을 시트에 기록"""
        should_clear = clear if clear is not None else self.policy.clear_before_dataframe
        
        if should_clear:
            self.sheet.clear()
        
        self.sheet.range(anchor).options(index=index, header=header).value = df
        return True


class XwWs:
    """Worksheet 통합 제어 (조합 패턴)"""
    
    def __init__(
        self,
        book: xw.Book,
        sheet: Union[str, int] = "Sheet1",
        *,
        policy: Optional[XwWsPolicy] = None,
    ):
        self.book = book
        self.policy = policy or XwWsPolicy()
        
        # 컴포넌트 초기화
        sheet_resolver = XwWsSheetResolver(book, self.policy)
        self.sheet = sheet_resolver.resolve(sheet)
        
        save_manager = XwSaveManager(book.app)
        self.cell_ops = XwWsCellOps(self.sheet, save_manager, self.policy)
        self.df_ops = XwWsDataFrameOps(self.sheet, self.policy)
    
    # ------------------------------------------------------------------
    # 셀 조작 (위임)
    # ------------------------------------------------------------------
    def read_cell(self, cell: Union[str, tuple[int, int]]) -> Any:
        return self.cell_ops.read(cell)
    
    def write_cell(
        self,
        row: int,
        col: int,
        value: Any,
        *,
        number_format: Optional[str] = None,
        save: bool = False,
    ) -> xw.Range:
        return self.cell_ops.write(row, col, value, number_format=number_format, save=save)
    
    # ------------------------------------------------------------------
    # DataFrame 변환 (위임)
    # ------------------------------------------------------------------
    def to_dataframe(
        self,
        anchor: str = "A1",
        *,
        header: bool = True,
        index: bool = False,
        expand: str = "table",
    ) -> pd.DataFrame:
        return self.df_ops.to_dataframe(anchor, header=header, index=index, expand=expand)
    
    def from_dataframe(
        self,
        df: pd.DataFrame,
        anchor: str = "A1",
        *,
        index: bool = False,
        header: bool = True,
        clear: bool = None,
    ) -> bool:
        return self.df_ops.from_dataframe(df, anchor, index=index, header=header, clear=clear)
    
    # ------------------------------------------------------------------
    # 유틸리티
    # ------------------------------------------------------------------
    def clear(self, cell: Optional[Union[str, tuple[int, int]]] = None):
        """시트 또는 특정 셀 초기화"""
        if cell:
            self.sheet.range(cell).clear()
        else:
            self.sheet.clear()
    
    def autofit(self, axis: str = "both"):
        """열/행 자동 맞춤"""
        self.sheet.autofit(axis)
    
    def used_range(self) -> xw.Range:
        """사용된 범위 반환"""
        return self.sheet.used_range