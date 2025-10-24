# -*- coding: utf-8 -*-
# xl_utils/xw_wb.py
# Excel Workbook 단위 제어 (SRP 준수 버전)

from __future__ import annotations
import xlwings as xw
from pathlib import Path
from typing import Optional, Union
from fso_utils import FSOOps
from xl_utils.core.policy import PathValidationPolicy, SavePolicy
from xl_utils.core.save_helper import SavePolicyHelper
from xl_utils.services.save_manager import XwSaveManager


class XwWbPathResolver:
    """Workbook 경로 확인 및 생성 전담 (PathValidationPolicy 사용)"""
    
    def __init__(
        self,
        path: Path,
        path_validation: Optional[PathValidationPolicy] = None
    ):
        self.path = path
        self.path_validation = path_validation
    
    def resolve(self) -> Path:
        """PathValidationPolicy 기반 경로 확인 및 생성"""
        if self.path_validation:
            fso = FSOOps(self.path, policy=self.path_validation.fso)
            return fso.path
        else:
            # 정책 없으면 단순 resolve
            return self.path.resolve()


class XwWb:
    """Workbook 단위 제어 (열기/닫기/저장 전담)"""
    
    def __init__(
        self,
        app: xw.App,
        path: Optional[Union[str, Path]] = None,
        *,
        path_validation: Optional[PathValidationPolicy] = None,
        save_policy: Optional[SavePolicy] = None,
    ):
        self.app = app
        self.path = Path(path).expanduser().resolve() if path else None
        self.path_validation = path_validation
        self.save_policy = save_policy
        self.book: Optional[xw.Book] = None
        self.save_manager = XwSaveManager(app)
        
        # PathResolver 생성
        if self.path:
            self.path_resolver = XwWbPathResolver(
                self.path,
                path_validation=self.path_validation
            )
        else:
            self.path_resolver = None
        
        self._context_managed = False
    
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
        """워크북 닫기 (SavePolicy 기반 저장)
        
        우선순위:
        1. 명시적 save 인자
        2. SavePolicy
        """
        if not self.book:
            return
        
        # SavePolicyHelper로 저장 결정
        do_save = SavePolicyHelper.should_save("close", self.save_policy, save)
        
        if do_save:
            self.save_manager.save_workbook(self.book)
        
        self.book.close()
        self.book = None
    
    def get_sheet(self, name_or_index: Union[str, int]) -> xw.Sheet:
        """시트 조회"""
        if not self.book:
            raise RuntimeError("Workbook not opened")
        return self.book.sheets[name_or_index]
    
    # ==========================================================================
    # Context Manager Protocol
    # ==========================================================================
    
    def __enter__(self) -> "XwWb":
        """Context manager 진입 - Workbook 열기"""
        self._context_managed = True
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager 종료 - SavePolicy에 따라 저장 후 닫기"""
        if self.book:
            # SavePolicyHelper로 저장 결정
            do_save = SavePolicyHelper.should_save("close", self.save_policy)
            self.close(save=do_save)
        return None
