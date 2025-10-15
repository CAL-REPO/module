# -*- coding: utf-8 -*-
"""
xl_utils/services/workflow.py
Excel 워크플로우 통합 서비스

Excel App → Workbook → Worksheet 생명주기 관리
비즈니스 로직은 사용자 단에서 처리, xl_utils는 Excel 접근만 제공
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Union
import pandas as pd
import xlwings as xw

from xl_utils.core.policy import XlPolicyManager, XwAppPolicy, XwLifecyclePolicy, XwWbPolicy, XwWsPolicy
from xl_utils.services.xw_app import XwApp
from xl_utils.services.xw_wb import XwWb
from xl_utils.services.xw_ws import XwWs


class XlWorkflow:
    """Excel 전체 워크플로우 통합 클래스
    
    Excel App → Workbook → Worksheet 생명주기 관리
    xlwings 기반 셀 조작 인터페이스 제공
    
    비즈니스 로직 (DataFrame 처리 등)은 사용자 단에서 수행
    xl_utils는 Excel 파일 접근 및 셀 조작만 담당
    
    Example:
        >>> with XlWorkflow(
        ...     excel_path="data.xlsx",
        ...     sheet_name="Sheet1",
        ...     policy_mgr=policy_mgr
        ... ) as wf:
        ...     # Worksheet 접근
        ...     ws = wf.get_worksheet()
        ...     
        ...     # xlwings 기반 셀 조작
        ...     ws.write_cell(1, 1, "제목")
        ...     ws.write_range("A2:C10", data_list)
        ...     ws.apply_format("A1", bold=True, font_size=14)
        ...     
        ...     # DataFrame 변환 (필요시)
        ...     df = ws.to_dataframe(anchor="A1")
        ...     # ... 비즈니스 로직 (외부에서 처리) ...
        ...     ws.from_dataframe(processed_df, anchor="A10")
    """
    
    def __init__(
        self,
        excel_path: Union[str, Path],
        sheet_name: Union[str, int] = "Sheet1",
        *,
        policy_mgr: Optional[XlPolicyManager] = None,
        app_policy: Optional[XwAppPolicy] = None,
        lifecycle_policy: Optional[XwLifecyclePolicy] = None,
        wb_policy: Optional[XwWbPolicy] = None,
        ws_policy: Optional[XwWsPolicy] = None,
    ):
        """XlWorkflow 초기화
        
        Args:
            excel_path: Excel 파일 경로
            sheet_name: 작업할 시트 이름 또는 인덱스
            policy_mgr: 통합 정책 관리자 (우선순위 높음)
            app_policy: Excel App 정책
            lifecycle_policy: 생명주기 정책
            wb_policy: Workbook 정책
            ws_policy: Worksheet 정책
        """
        self.excel_path = Path(excel_path).resolve()
        self.sheet_name = sheet_name
        
        # 정책 설정 (policy_mgr 우선, 없으면 개별 정책 사용)
        if policy_mgr:
            self.policy_mgr = policy_mgr
        else:
            self.policy_mgr = XlPolicyManager(
                app=app_policy or XwAppPolicy(),
                lifecycle=lifecycle_policy or XwLifecyclePolicy(),
                wb=wb_policy or XwWbPolicy(),
                ws=ws_policy or XwWsPolicy()
            )
        
        # 컴포넌트 (나중에 초기화)
        self.app_ctrl: Optional[XwApp] = None
        self.wb_ctrl: Optional[XwWb] = None
        self.ws_ctrl: Optional[XwWs] = None
        
        self._context_managed = False
        self._initialized = False
    
    # ==========================================================================
    # Lifecycle Management
    # ==========================================================================
    
    def _initialize(self) -> None:
        """Excel 컴포넌트 초기화 (App → Wb → Ws)"""
        if self._initialized:
            return
        
        # App 시작
        self.app_ctrl = XwApp(
            path=self.excel_path,
            app_policy=self.policy_mgr.app,
            lifecycle_policy=self.policy_mgr.lifecycle
        )
        self.app_ctrl.__enter__()
        
        # Workbook 열기
        self.wb_ctrl = XwWb(
            self.app_ctrl.app,
            path=self.excel_path,
            policy=self.policy_mgr.wb
        )
        self.wb_ctrl.__enter__()
        
        # Worksheet 설정
        self.ws_ctrl = XwWs(
            self.wb_ctrl.book,
            sheet=self.sheet_name,
            policy=self.policy_mgr.ws
        )
        self.ws_ctrl.__enter__()
        
        self._initialized = True
    
    def _cleanup(self) -> None:
        """Excel 컴포넌트 정리 (역순: Ws → Wb → App)"""
        if not self._initialized:
            return
        
        # 역순 종료
        if self.ws_ctrl:
            self.ws_ctrl.__exit__(None, None, None)
        
        if self.wb_ctrl:
            self.wb_ctrl.__exit__(None, None, None)
        
        if self.app_ctrl:
            self.app_ctrl.__exit__(None, None, None)
        
        self._initialized = False
    
    # ==========================================================================
    # Worksheet Access
    # ==========================================================================
    
    def get_worksheet(self) -> XwWs:
        """Worksheet 제어 객체 반환
        
        사용자는 이 객체를 통해 xlwings 기반 셀 조작 수행
        
        Returns:
            XwWs instance (worksheet controller)
        
        Example:
            >>> ws = workflow.get_worksheet()
            >>> ws.write_cell(1, 1, "제목")
            >>> ws.write_range("A2:C5", [[1,2,3], [4,5,6], [7,8,9], [10,11,12]])
            >>> ws.apply_format("A1", bold=True, font_size=14)
        """
        if not self._initialized:
            self._initialize()
        
        return self.ws_ctrl
    
    def get_workbook(self) -> XwWb:
        """Workbook 제어 객체 반환
        
        Returns:
            XwWb instance (workbook controller)
        """
        if not self._initialized:
            self._initialize()
        
        return self.wb_ctrl
    
    def get_app(self) -> XwApp:
        """Application 제어 객체 반환
        
        Returns:
            XwApp instance (application controller)
        """
        if not self._initialized:
            self._initialize()
        
        return self.app_ctrl
    
    # ==========================================================================
    # Context Manager Protocol
    # ==========================================================================
    
    def __enter__(self) -> "XlWorkflow":
        """Context manager 진입"""
        self._context_managed = True
        self._initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager 종료"""
        self._cleanup()
        return None
