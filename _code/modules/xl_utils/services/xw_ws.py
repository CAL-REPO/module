# -*- coding: utf-8 -*-
# xl_utils/xw_ws.py
# Excel Worksheet 단위 제어 (SRP 준수 버전)

from __future__ import annotations
import xlwings as xw
from typing import Any, Optional, Union
import pandas as pd
from xl_utils.core.policy import XwWsPolicy
from xl_utils.services.save_manager import XwSaveManager


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
    """셀 단위 읽기/쓰기 전담 (확장)"""
    
    def __init__(self, sheet: xw.Sheet, save_manager: XwSaveManager, policy: XwWsPolicy):
        self.sheet = sheet
        self.save_manager = save_manager
        self.policy = policy
    
    # ==========================================================================
    # 단일 셀 조작
    # ==========================================================================
    
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
    
    # ==========================================================================
    # 범위 조작
    # ==========================================================================
    
    def read_range(self, range_addr: str) -> Any:
        """범위 읽기 (A1:C10 형식)"""
        return self.sheet.range(range_addr).value
    
    def write_range(
        self,
        range_addr: str,
        values: Any,
        *,
        save: bool = False,
    ) -> xw.Range:
        """범위 쓰기 (2D list, DataFrame, 등)"""
        rng = self.sheet.range(range_addr)
        rng.value = values
        
        if save or self.policy.auto_save_on_write:
            self.save_manager.save_workbook(self.sheet.book)
        
        return rng
    
    def clear_range(self, range_addr: str) -> None:
        """범위 초기화"""
        self.sheet.range(range_addr).clear()
    
    # ==========================================================================
    # 서식 적용
    # ==========================================================================
    
    def apply_format(
        self,
        range_addr: str,
        *,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        font_size: Optional[int] = None,
        font_color: Optional[tuple[int, int, int]] = None,
        bg_color: Optional[tuple[int, int, int]] = None,
        number_format: Optional[str] = None,
        horizontal_alignment: Optional[str] = None,
        vertical_alignment: Optional[str] = None,
    ) -> xw.Range:
        """셀 서식 적용
        
        Args:
            range_addr: 범위 주소 (예: "A1" or "A1:C10")
            bold: 굵게
            italic: 이탤릭
            font_size: 폰트 크기
            font_color: 폰트 색상 RGB (예: (255, 0, 0))
            bg_color: 배경색 RGB
            number_format: 숫자 서식 (예: "#,##0", "yyyy-mm-dd")
            horizontal_alignment: 수평 정렬 ("left", "center", "right")
            vertical_alignment: 수직 정렬 ("top", "center", "bottom")
        """
        rng = self.sheet.range(range_addr)
        
        if bold is not None:
            rng.font.bold = bold
        
        if italic is not None:
            rng.font.italic = italic
        
        if font_size is not None:
            rng.font.size = font_size
        
        if font_color is not None:
            rng.font.color = font_color
        
        if bg_color is not None:
            rng.color = bg_color
        
        if number_format is not None:
            rng.number_format = number_format
        
        if horizontal_alignment is not None:
            alignment_map = {
                "left": -4131,
                "center": -4108,
                "right": -4152,
            }
            rng.api.HorizontalAlignment = alignment_map.get(horizontal_alignment.lower(), -4131)
        
        if vertical_alignment is not None:
            alignment_map = {
                "top": -4160,
                "center": -4108,
                "bottom": -4107,
            }
            rng.api.VerticalAlignment = alignment_map.get(vertical_alignment.lower(), -4160)
        
        return rng
    
    # ==========================================================================
    # 행/열 조작
    # ==========================================================================
    
    def insert_rows(self, row: int, count: int = 1) -> None:
        """행 삽입
        
        Args:
            row: 삽입할 위치 (1-based)
            count: 삽입할 행 개수
        """
        for _ in range(count):
            self.sheet.range(f"{row}:{row}").api.Insert()
    
    def delete_rows(self, row: int, count: int = 1) -> None:
        """행 삭제
        
        Args:
            row: 삭제할 시작 위치 (1-based)
            count: 삭제할 행 개수
        """
        self.sheet.range(f"{row}:{row + count - 1}").api.Delete()
    
    def insert_columns(self, col: Union[int, str], count: int = 1) -> None:
        """열 삽입
        
        Args:
            col: 삽입할 위치 (1-based 숫자 또는 "A", "B" 등)
            count: 삽입할 열 개수
        """
        if isinstance(col, int):
            col_letter = self._col_num_to_letter(col)
        else:
            col_letter = col
        
        for _ in range(count):
            self.sheet.range(f"{col_letter}:{col_letter}").api.Insert()
    
    def delete_columns(self, col: Union[int, str], count: int = 1) -> None:
        """열 삭제
        
        Args:
            col: 삭제할 시작 위치 (1-based 숫자 또는 "A", "B" 등)
            count: 삭제할 열 개수
        """
        if isinstance(col, int):
            start_col = self._col_num_to_letter(col)
            end_col = self._col_num_to_letter(col + count - 1)
        else:
            start_col = col
            end_col = self._col_num_to_letter(self._col_letter_to_num(col) + count - 1)
        
        self.sheet.range(f"{start_col}:{end_col}").api.Delete()
    
    # ==========================================================================
    # Helper Methods
    # ==========================================================================
    
    @staticmethod
    def _col_num_to_letter(col_num: int) -> str:
        """열 번호 → 열 문자 변환 (1 → "A", 27 → "AA")"""
        result = ""
        while col_num > 0:
            col_num -= 1
            result = chr(col_num % 26 + 65) + result
            col_num //= 26
        return result
    
    @staticmethod
    def _col_letter_to_num(col_letter: str) -> int:
        """열 문자 → 열 번호 변환 ("A" → 1, "AA" → 27)"""
        result = 0
        for char in col_letter.upper():
            result = result * 26 + (ord(char) - 64)
        return result


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
        
        self._save_manager = save_manager
        self._context_managed = False
    
    # ------------------------------------------------------------------
    # 셀 조작 (위임)
    # ------------------------------------------------------------------
    def read(self, cell: Union[str, tuple[int, int]]) -> Any:
        """셀 읽기 (별칭)"""
        return self.cell_ops.read(cell)
    
    def read_cell(self, cell: Union[str, tuple[int, int]]) -> Any:
        """셀 읽기"""
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
        """셀 쓰기"""
        return self.cell_ops.write(row, col, value, number_format=number_format, save=save)
    
    def read_range(self, range_addr: str) -> Any:
        """범위 읽기"""
        return self.cell_ops.read_range(range_addr)
    
    def write_range(
        self,
        range_addr: str,
        values: Any,
        *,
        save: bool = False,
    ) -> xw.Range:
        """범위 쓰기"""
        return self.cell_ops.write_range(range_addr, values, save=save)
    
    def clear_range(self, range_addr: str) -> None:
        """범위 초기화"""
        return self.cell_ops.clear_range(range_addr)
    
    def apply_format(
        self,
        range_addr: str,
        *,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        font_size: Optional[int] = None,
        font_color: Optional[tuple[int, int, int]] = None,
        bg_color: Optional[tuple[int, int, int]] = None,
        number_format: Optional[str] = None,
        horizontal_alignment: Optional[str] = None,
        vertical_alignment: Optional[str] = None,
    ) -> xw.Range:
        """서식 적용"""
        return self.cell_ops.apply_format(
            range_addr,
            bold=bold,
            italic=italic,
            font_size=font_size,
            font_color=font_color,
            bg_color=bg_color,
            number_format=number_format,
            horizontal_alignment=horizontal_alignment,
            vertical_alignment=vertical_alignment
        )
    
    def insert_rows(self, row: int, count: int = 1) -> None:
        """행 삽입"""
        return self.cell_ops.insert_rows(row, count)
    
    def delete_rows(self, row: int, count: int = 1) -> None:
        """행 삭제"""
        return self.cell_ops.delete_rows(row, count)
    
    def insert_columns(self, col: Union[int, str], count: int = 1) -> None:
        """열 삽입"""
        return self.cell_ops.insert_columns(col, count)
    
    def delete_columns(self, col: Union[int, str], count: int = 1) -> None:
        """열 삭제"""
        return self.cell_ops.delete_columns(col, count)

    
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
    # ==========================================================================
    # Context Manager Protocol
    # ==========================================================================
    
    def __enter__(self) -> "XwWs":
        """Context manager 진입"""
        self._context_managed = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager 종료 - auto_save_on_write 정책에 따라 저장"""
        if self.policy.auto_save_on_write:
            self._save_manager.save_workbook(self.book)
        return None
