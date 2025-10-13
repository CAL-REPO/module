# -*- coding: utf-8 -*-
# xl_utils/save_manager.py
# Excel Workbook 저장 로직 전담 클래스 (SRP 준수)

from __future__ import annotations
import xlwings as xw
from typing import Optional, List
from pathlib import Path


class XwSaveManager:
    """Excel Workbook 저장 로직 전담"""
    
    def __init__(self, app: xw.App):
        self.app = app
    
    def save_workbook(self, book: xw.Book, path: Optional[Path] = None) -> bool:
        """단일 워크북 저장"""
        try:
            if path:
                book.save(str(path))
            else:
                book.save()
            return True
        except Exception as e:
            print(f"[WARN] Workbook save failed ({book.name}): {e}")
            return False
    
    def save_all_workbooks(self, exclude: Optional[List[xw.Book]] = None) -> dict[str, bool]:
        """열린 모든 워크북 저장"""
        exclude = exclude or []
        results = {}
        
        for wb in list(self.app.books):
            if wb in exclude:
                continue
            
            wb_name = wb.name
            results[wb_name] = self.save_workbook(wb)
        
        return results
    
    def has_unsaved_changes(self, book: xw.Book) -> bool:
        """저장되지 않은 변경사항 확인"""
        try:
            return book.api.Saved is False
        except Exception:
            return False
    
    def prompt_save_if_needed(self, book: xw.Book) -> bool:
        """변경사항이 있을 때만 저장"""
        if self.has_unsaved_changes(book):
            return self.save_workbook(book)
        return True