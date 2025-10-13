# -*- coding: utf-8 -*-
# xl_utils/xw_app.py
# Excel Application 수명주기 제어 — FSO 기반 정책과 연동

from __future__ import annotations
import xlwings as xw
from pathlib import Path
from typing import Optional, Union
from fso_utils import FSOOpsPolicy, ExistencePolicy, FSOOps
from xl_utils.policy import XwAppPolicy


class XwApp:
    """Excel Application 수명주기 제어 (정책 + FSO 기반)"""

    def __init__(
        self,
        path: Optional[Union[str, Path]] = None,
        *,
        policy: Optional[XwAppPolicy] = None,
    ):
        self.policy = policy or XwAppPolicy()
        self.path = Path(path).expanduser().resolve() if path else None

        self.app: Optional[xw.App] = None
        self.book: Optional[xw.Book] = None
        self._launched_by_self: bool = False  # 직접 실행 여부 추적

    # ------------------------------------------------------------------
    # Excel Application Control
    # ------------------------------------------------------------------
    def start(self) -> xw.App:
        """Excel Application 실행 (필요 시 새로 띄움)"""
        if xw.apps.count > 0:
            self.app = xw.apps.active
            self._launched_by_self = False
        else:
            self.app = xw.App(
                visible=self.policy.visible,
                add_book=self.policy.add_book
            )
            self._launched_by_self = True

        self.app.display_alerts = self.policy.display_alerts
        self.app.screen_updating = self.policy.screen_updating
        return self.app

    def open_book(self, path: Optional[Union[str, Path]] = None) -> xw.Book:
        """워크북 열기 (정책 기반 FSO 확인)"""
        target_path = Path(path or self.path).expanduser().resolve()
        policy = FSOOpsPolicy(exist=ExistencePolicy(must_exist=True))
        fso = FSOOps(target_path, policy)

        if not self.app:
            self.start()

        self.book = self.app.books.open(str(fso.path))
        return self.book

    def quit(self, save_all: bool = True):
        """직접 실행한 경우만 종료 (종료 전 자동 저장 지원)"""
        if not self.app:
            return

        try:
            # 🔸 모든 열린 워크북 저장 (자동 저장 로직)
            if save_all:
                for wb in list(self.app.books):
                    try:
                        wb.save()
                    except Exception as e:
                        print(f"[WARN] Failed to save workbook {wb.name}: {e}")
        finally:
            # 🔸 직접 실행한 경우에만 종료
            if self._launched_by_self:
                try:
                    self.app.quit()
                    print("[INFO] Excel Application closed.")
                except Exception as e:
                    print(f"[ERROR] Excel quit failed: {e}")
            else:
                print("[INFO] Excel left open (attached instance).")

            self.app = None

    # ------------------------------------------------------------------
    # Context Manager
    # ------------------------------------------------------------------
    def __enter__(self) -> "XwApp":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        """Context 종료 시 정책 기반 저장 및 종료"""
        if not self.app:
            return

        # ✅ 항상 Workbook 저장 시도
        for wb in list(self.app.books):
            try:
                wb.save()
            except Exception as e:
                print(f"[WARN] Workbook save failed before exit: {e}")

        # ✅ 직접 띄운 Excel만 종료
        if self.policy.quit_on_exit and self._launched_by_self:
            self.quit(save_all=False)