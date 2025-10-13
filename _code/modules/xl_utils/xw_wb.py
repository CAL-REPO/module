# -*- coding: utf-8 -*-
# xl_utils/xw_wb.py
# Excel Workbook 단위 제어 — FSO 기반 정책과 연동

from __future__ import annotations
import xlwings as xw
from pathlib import Path
from typing import Optional, Union
from fso_utils import FSOOpsPolicy, ExistencePolicy, FSOOps
from .policy import XwWbPolicy


class XwWb:
    """워크북 단위 제어"""

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

    def open(self) -> xw.Book:
        """워크북 열기 (정책 기반 경로 확인)"""
        if self.path:
            policy = FSOOpsPolicy(
                exist=ExistencePolicy(
                    must_exist=self.policy.must_exist,
                    create_if_missing=self.policy.create_if_missing,
                )
            )
            # 수정 후
            fso = FSOOps(self.path, policy=policy)

            if fso.path.exists():
                self.book = self.app.books.open(str(fso.path))
            else:
                self.book = self.app.books.add()
                self.book.save(str(fso.path))
        else:
            self.book = self.app.books.add()
        return self.book

    def save(self):
        if not self.book:
            raise RuntimeError("Workbook not opened")
        self.book.save()
        return self.book.fullname

    def close(self, save: Optional[bool] = None):
        """워크북 닫기 (정책 기반 자동 저장 지원)"""
        if self.book:
            do_save = save if save is not None else self.policy.auto_save
            if do_save:
                try:
                    self.book.save()
                except Exception:
                    pass
            self.book.close()
            self.book = None

    def sheet(self, name_or_index: Union[str, int]) -> xw.Sheet:
        if not self.book:
            raise RuntimeError("Workbook not opened")
        return self.book.sheets[name_or_index]
