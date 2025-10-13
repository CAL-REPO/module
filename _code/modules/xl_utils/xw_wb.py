# -*- coding: utf-8 -*-
# xl_utils/xw_wb.py
# Excel Workbook 단위 제어 (SRP 준수 버전)

from __future__ import annotations
import xlwings as xw
from pathlib import Path
from typing import Optional, Union
from fso_utils import FSOOpsPolicy, ExistencePolicy, FSOOps
from xl_utils.policy import XwWbPolicy
from xl_utils.save_manager import XwSaveManager


class XwWbPathResolver:
    """Workbook 경로 확인 및 생성 전담"""
    
    def __init__(self, path: Path, policy: XwWbPolicy):
        self.path = path
        self.policy = policy
    
    def resolve(self) -> Path:
        """정책 기반 경로 확인 및 생성"""
        fso_policy = FSOOpsPolicy(
            exist=ExistencePolicy(
                must_exist=self.policy.must_exist,
                create_if_missing=self.policy.create_if_missing,
            )
        )
        fso = FSOOps(self.path, policy=fso_policy)
        return fso.path


class XwWb:
    """Workbook 단위 제어 (열기/닫기/저장 전담)"""
    
    def __init__(
        self,
        app: xw.App,
        path: Optional[Union[str, Path]] = None,
        *,
        policy: Optional[XwWbPolicy] = None,
    ):
        self.app = app
        self.path = Path(path).expanduser().resolve() if path else None
        self.policy = policy or XwWbPolicy()
        self.book: Optional[xw.Book] = None
        self.save_manager = XwSaveManager(app)
        self.path_resolver = XwWbPathResolver(self.path, self.policy) if self.path else None
    
    def open(self) -> xw.Book:
        """워크북 열기 (정책 기반 경로 확인)"""
        if self.path and self.path_resolver:
            resolved_path = self.path_resolver.resolve()
            
            if resolved_path.exists():
                self.book = self.app.books.open(str(resolved_path))
            else:
                self.book = self.app.books.add()
                self.book.save(str(resolved_path))
        else:
            self.book = self.app.books.add()
        
        return self.book
    
    def save(self, path: Optional[Path] = None) -> str:
        """워크북 저장"""
        if not self.book:
            raise RuntimeError("Workbook not opened")
        
        self.save_manager.save_workbook(self.book, path)
        return self.book.fullname
    
    def close(self, save: Optional[bool] = None):
        """워크북 닫기 (정책 기반 자동 저장 지원)"""
        if not self.book:
            return
        
        # 저장 여부 결정
        do_save = save if save is not None else self.policy.auto_save
        
        if do_save:
            self.save_manager.save_workbook(self.book)
        
        self.book.close()
        self.book = None
    
    def get_sheet(self, name_or_index: Union[str, int]) -> xw.Sheet:
        """시트 조회"""
        if not self.book:
            raise RuntimeError("Workbook not opened")
        return self.book.sheets[name_or_index]