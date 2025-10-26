# -*- coding: utf-8 -*-
# xl_utils/xw_app.py
# Excel Application 수명주기 제어 (SRP 준수 버전)

from __future__ import annotations
import xlwings as xw
from pathlib import Path
from typing import Optional, Union
from xl_utils.core.policy import XwAppPolicy, PerformancePolicy


class XwAppLifecycle:
    """Excel Application 수명주기 전담 (시작/종료)"""
    
    def __init__(
        self,
        policy: Optional[XwAppPolicy] = None,
        performance: Optional[PerformancePolicy] = None
    ):
        self.policy = policy or XwAppPolicy()
        self.performance = performance or PerformancePolicy()
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
        
        self._apply_settings()
        return self.app
    
    def _apply_settings(self):
        """Apply performance and UI settings"""
        # ✅ Calculation 설정 (None이면 skip)
        if self.performance.calculation is not None:
            try:
                calc_map = {
                    "automatic": -4105,
                    "manual": -4135,
                    "semiautomatic": 2
                }
                self.app.api.Calculation = calc_map.get(self.performance.calculation, -4105)
            except Exception as e:
                # Excel 보호 모드 등에서 설정 실패 시 무시
                import logging
                logging.debug(f"Unable to set Calculation property: {e}")
        
        # EnableEvents 설정
        try:
            self.app.api.EnableEvents = self.performance.enable_events
        except Exception:
            pass
        
        # Interactive 설정
        try:
            self.app.api.Interactive = self.performance.interactive
        except Exception:
            pass
        
        # EnableCancelKey 설정
        try:
            self.app.api.EnableCancelKey = self.performance.enable_cancel_key
        except Exception:
            pass
    
    def quit(self):
        """직접 실행한 Excel만 종료"""
        if not self.app or not self.launched_by_self:
            return
        
        try:
            # Performance 정책: 종료 시 클립보드 비우기
            if self.performance.clear_clipboard and hasattr(self.app.api, 'CutCopyMode'):
                self.app.api.CutCopyMode = False
            
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
        performance_policy: Optional[PerformancePolicy] = None,
    ):
        self.path = Path(path).expanduser().resolve() if path else None
        self.lifecycle = XwAppLifecycle(app_policy, performance_policy)
        self.performance_policy = performance_policy or PerformancePolicy()  # type: ignore
    
    @property
    def app(self) -> Optional[xw.App]:
        """현재 Excel Application 반환"""
        return self.lifecycle.app
    
    def start(self) -> xw.App:
        """Excel Application 시작"""
        app = self.lifecycle.start()
        return app
    
    def quit(self):
        """Excel Application 종료"""
        self.lifecycle.quit()
    
    # ------------------------------------------------------------------
    # Context Manager
    # ------------------------------------------------------------------
    def __enter__(self) -> "XwApp":
        self.start()
        return self
    
    def __exit__(self, exc_type, exc, tb):
        """Context 종료 시 기본 종료 (정책 기반 저장/종료는 ExcelLoad에서 처리)"""
        # Note: SavePolicy 기반 저장은 XwWb/XwWs에서 처리
        # 여기서는 단순히 quit만 실행
        self.quit()