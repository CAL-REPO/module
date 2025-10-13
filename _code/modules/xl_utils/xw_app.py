# -*- coding: utf-8 -*-
# xl_utils/xw_app.py
# Excel Application 수명주기 제어 (SRP 준수 버전)

from __future__ import annotations
import xlwings as xw
from pathlib import Path
from typing import Optional, Union
from xl_utils.policy import XwAppPolicy, XwLifecyclePolicy
from xl_utils.save_manager import XwSaveManager


class XwAppLifecycle:
    """Excel Application 수명주기 전담 (시작/종료)"""
    
    def __init__(self, policy: Optional[XwAppPolicy] = None):
        self.policy = policy or XwAppPolicy()
        self.app: Optional[xw.App] = None
        self.launched_by_self = False
    
    def start(self) -> xw.App:
        """Excel Application 실행"""
        if xw.apps.count > 0:
            self.app = xw.apps.active
            self.launched_by_self = False
        else:
            self.app = xw.App(
                visible=self.policy.visible,
                add_book=self.policy.add_book
            )
            self.launched_by_self = True
        
        self._apply_display_settings()
        return self.app
    
    def _apply_display_settings(self):
        """Display 관련 설정 적용"""
        if self.app:
            self.app.display_alerts = self.policy.display_alerts
            self.app.screen_updating = self.policy.screen_updating
    
    def quit(self):
        """직접 실행한 Excel만 종료"""
        if not self.app or not self.launched_by_self:
            return
        
        try:
            self.app.quit()
            print("[INFO] Excel Application closed.")
        except Exception as e:
            print(f"[ERROR] Excel quit failed: {e}")
        finally:
            self.app = None
    
    def is_attached_instance(self) -> bool:
        """기존 Excel 인스턴스에 연결된 상태인지 확인"""
        return not self.launched_by_self


class XwApp:
    """Excel Application 통합 제어"""
    
    def __init__(
        self,
        path: Optional[Union[str, Path]] = None,
        *,
        app_policy: Optional[XwAppPolicy] = None,
        lifecycle_policy: Optional[XwLifecyclePolicy] = None,
    ):
        self.path = Path(path).expanduser().resolve() if path else None
        self.lifecycle = XwAppLifecycle(app_policy)
        self.lifecycle_policy = lifecycle_policy or XwLifecyclePolicy()
        self.save_manager: Optional[XwSaveManager] = None
    
    @property
    def app(self) -> Optional[xw.App]:
        """현재 Excel Application 반환"""
        return self.lifecycle.app
    
    def start(self) -> xw.App:
        """Excel Application 시작"""
        app = self.lifecycle.start()
        self.save_manager = XwSaveManager(app)
        return app
    
    def quit(self):
        """Excel Application 종료"""
        self.lifecycle.quit()
        self.save_manager = None
    
    # ------------------------------------------------------------------
    # Context Manager
    # ------------------------------------------------------------------
    def __enter__(self) -> "XwApp":
        self.start()
        return self
    
    def __exit__(self, exc_type, exc, tb):
        """Context 종료 시 정책 기반 저장 및 종료"""
        if not self.app or not self.save_manager:
            return
        
        # 저장 정책 적용
        if self.lifecycle_policy.save_on_exit:
            if self.lifecycle_policy.save_attached_instance or self.lifecycle.launched_by_self:
                results = self.save_manager.save_all_workbooks()
                failed = [k for k, v in results.items() if not v]
                if failed:
                    print(f"[WARN] Failed to save: {failed}")
        
        # 종료 정책 적용
        if self.lifecycle_policy.quit_on_exit:
            self.quit()