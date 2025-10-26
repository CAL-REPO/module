# -*- coding: utf-8 -*-
"""ExcelLoad - Excel file access adapter.

책임:
1. Excel 파일 접근 및 셀 조작 (xlwings 기반)
2. Excel App → Workbook → Worksheet 생명주기 관리
3. Worksheet 객체 제공

ImageLoad 패턴과 동일:
- Policy: ExcelLoadPolicy (설정)
- 파일/시트 경로를 인자로 받아 처리
- 직접 컴포넌트 관리 (XwApp, XwWb, XwWs)

비즈니스 로직 (DataFrame 처리 등)은 사용자 단에서 수행
xl_utils는 Excel 파일 접근 및 셀 조작만 담당
"""

from __future__ import annotations
from pathlib import Path
from typing import Union, Optional, Any, Dict, List

from logs_utils import LogManager

from xl_utils.core.policy import ExcelLoadPolicy
from xl_utils.services.xw_app import XwApp
from xl_utils.services.xw_wb import XwWb
from xl_utils.services.xw_ws import XwWs


class ExcelLoad:
    """Excel Load Adapter - 파일 단위 Excel 접근.
    
    파일 단위 설계:
    - __init__(file_path, policy) - 파일 경로와 정책 받음
    - open() - Excel 파일 열기 (App + Workbook)
    - get_worksheet(sheet_name, column_aliases) - Sheet 접근
    - close() - Excel 파일 닫기
    
    Attributes:
        file_path: Excel 파일 경로
        policy: ExcelLoadPolicy 설정
        log: loguru logger
    
    Usage:
        >>> # 파일 단위 사용
        >>> excel = ExcelLoad(
        ...     file_path="data.xlsx",
        ...     cfg_like="config.yaml"
        ... )
        >>> with excel:
        ...     ws = excel.get_worksheet("Sheet1", aliases)
        ...     df = ws.to_dataframe(used_range=True)
    """
    
    def __init__(
        self,
        file_path: Optional[Union[Path, str]] = None,  # ← Optional로 변경
        cfg_like: Union[ExcelLoadPolicy, Path, str, dict, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize ExcelLoad with optional file path and configuration.
        
        Args:
            file_path: Excel 파일 경로 (선택사항)
                - None: App 단위 모드 (open_workbook()으로 파일 열기)
                - str/Path: 파일 단위 모드 (open()에서 자동으로 Workbook 열기)
            cfg_like: Configuration source:
                - ExcelLoadPolicy: Policy instance
                - str/Path: YAML file path
                - dict: Configuration dict
                - None: Use Pydantic defaults
            log_manager: External LogManager (선택사항)
            **overrides: Runtime overrides (e.g., xw_app__visible=True)
        
        Example:
            >>> # 파일 단위 모드
            >>> excel = ExcelLoad(
            ...     file_path="data.xlsx",
            ...     cfg_like="config.yaml"
            ... )
            
            >>> # App 단위 모드
            >>> excel = ExcelLoad(cfg_like="config.yaml")
            >>> with excel:
            ...     wb = excel.open_workbook("file1.xlsx")
            ...     ws = excel.get_worksheet(wb, "Sheet1")
        """
        self.file_path = Path(file_path).resolve() if file_path else None
        self._mode = "file" if file_path else "app"  # 모드 결정
        
        # Load policy (ConfigLikeLoader pattern)
        self.policy = self._load_config(cfg_like, **overrides)
        
        # Setup logging (ImageLoad 패턴: LogManager 직접 사용)
        if log_manager:
            self.log = log_manager.logger
        elif self.policy.log:
            self._log_manager = LogManager(self.policy.log)
            self.log = self._log_manager.logger
        else:
            self.log = LogManager({"enabled": False}).logger
        
        # Initialize components (lazy)
        self.app_ctrl: Optional[XwApp] = None
        self.wb_ctrl: Optional[XwWb] = None
        
        # State
        self._opened = False
        self._context_managed = False
        
        if self._mode == "file":
            assert self.file_path is not None
            mode_msg = f"file mode: {self.file_path.name}"
        else:
            mode_msg = "app mode"
        self.log.info(f"ExcelLoad initialized ({mode_msg})")
    
    # ==========================================================================
    # Configuration Loading (ConfigLikeLoader pattern)
    # ==========================================================================
    
    def _load_config(self, cfg_like, **overrides) -> ExcelLoadPolicy:
        """Load ExcelLoadPolicy from various sources.
        
        ConfigLikeLoader가 모든 경우를 처리:
        1. Policy 인스턴스 → 그대로 반환
        2. Path/str → ConfigLoader로 YAML 로드
        3. dict → ConfigLoader로 파싱 (Policy.name section 자동 추출)
        4. None → 기본 YAML 또는 Pydantic 기본값
        
        Args:
            cfg_like: ExcelLoadPolicy instance, YAML path, dict, or None
            **overrides: Runtime overrides (xw_app__visible=True)
        
        Returns:
            ExcelLoadPolicy instance
        """
        from cfg_utils.services import ConfigLikeLoader
        
        return ConfigLikeLoader.load(
            cfg_like=cfg_like,
            policy_class=ExcelLoadPolicy,
            module_file=__file__,
            config_filename="excel_load.yaml",
            **overrides
        )  # type: ignore
    
    # ==========================================================================
    # Component Management
    # ==========================================================================
    
    def open(self) -> "ExcelLoad":
        """Excel App/Workbook 열기.
        
        파일 모드: Workbook 자동 열기
        App 모드: App만 열기 (open_workbook()으로 파일 열기)
        
        Returns:
            self (method chaining)
        
        Example:
            >>> # 파일 모드
            >>> excel = ExcelLoad(file_path="data.xlsx", cfg_like="config.yaml")
            >>> excel.open()
            >>> ws = excel.get_worksheet("Sheet1")
            
            >>> # App 모드
            >>> excel = ExcelLoad(cfg_like="config.yaml")
            >>> excel.open()
            >>> wb = excel.open_workbook("data.xlsx")
        """
        if self._opened:
            return self
        
        # App 시작
        self.log.debug(f"Opening Excel App ({self._mode} mode)")
        self.app_ctrl = XwApp(
            path=self.file_path,
            app_policy=self.policy.xw_app,
            performance_policy=self.policy.performance
        )
        self.app_ctrl.__enter__()
        assert self.app_ctrl.app is not None, "App must be initialized"
        
        # 파일 모드: Workbook도 바로 열기
        if self._mode == "file":
            assert self.file_path is not None, "file_path required for file mode"
            self.log.debug(f"Opening workbook: {self.file_path.name}")
            
            self.wb_ctrl = XwWb(
                self.app_ctrl.app,
                path=self.file_path,
                path_validation=self.policy.path_validation,
                save_policy=self.policy.save
            )
            self.wb_ctrl.__enter__()
            assert self.wb_ctrl.book is not None, "Book must be initialized"
            
            self.log.info(f"Excel file opened: {self.file_path.name}")
        else:
            # App 모드: Workbook은 나중에 open_workbook()으로
            self.log.info("Excel App opened (app mode)")
        
        self._opened = True
        return self
    
    def open_workbook(self, file_path: Union[Path, str]) -> XwWb:
        """Workbook 열기 (App 단위 모드 전용).
        
        ⚠️ App 모드에서만 사용 가능
        ⚠️ open() 먼저 호출 필요
        
        Args:
            file_path: Excel 파일 경로
        
        Returns:
            XwWb instance
        
        Example:
            >>> excel = ExcelLoad(cfg_like="config.yaml")  # App 모드
            >>> with excel:
            ...     wb1 = excel.open_workbook("file1.xlsx")
            ...     wb2 = excel.open_workbook("file2.xlsx")
            ...     ws1 = excel.get_worksheet(wb1, "Sheet1")
            ...     ws2 = excel.get_worksheet(wb2, "Sheet1")
        """
        if self._mode != "app":
            raise RuntimeError("open_workbook() requires app mode (ExcelLoad without file_path)")
        
        if not self._opened:
            raise RuntimeError("open() must be called first")
        
        file_path = Path(file_path).resolve()
        self.log.debug(f"Opening workbook: {file_path.name}")
        
        wb_ctrl = XwWb(
            self.app_ctrl.app,  # type: ignore
            path=file_path,
            path_validation=self.policy.path_validation,
            save_policy=self.policy.save
        )
        wb_ctrl.__enter__()
        
        self.log.info(f"Workbook opened: {file_path.name}")
        return wb_ctrl
    
    def get_worksheet(
        self,
        sheet_name_or_wb: Union[str, int, XwWb] = "Sheet1",
        sheet_name: Optional[Union[str, int]] = None,
        column_aliases: Optional[Dict[str, List[str]]] = None
    ) -> XwWs:
        """Worksheet 제어 객체 반환.
        
        ⚠️ open() 먼저 호출 필요
        
        파일 모드: sheet_name만 받음
        App 모드: wb + sheet_name 받음
        
        Args:
            sheet_name_or_wb: Sheet name (파일 모드) 또는 XwWb (App 모드)
            sheet_name: Sheet name (App 모드 전용)
            column_aliases: Column alias mapping (optional)
        
        Returns:
            XwWs instance
        
        Example:
            >>> # 파일 모드
            >>> excel = ExcelLoad(file_path="data.xlsx", cfg_like="config.yaml")
            >>> with excel:
            ...     ws = excel.get_worksheet("Sheet1")
            
            >>> # App 모드
            >>> excel = ExcelLoad(cfg_like="config.yaml")
            >>> with excel:
            ...     wb = excel.open_workbook("data.xlsx")
            ...     ws = excel.get_worksheet(wb, "Sheet1")
        """
        if not self._opened:
            raise RuntimeError("open() must be called first")
        
        # 파일 모드: sheet_name만
        if self._mode == "file":
            if isinstance(sheet_name_or_wb, XwWb):
                raise RuntimeError("File mode: use get_worksheet(sheet_name), not get_worksheet(wb, sheet_name)")
            
            sheet = sheet_name_or_wb
            wb_ctrl = self.wb_ctrl
            assert wb_ctrl is not None, "Workbook not opened"
            
        # App 모드: wb + sheet_name
        else:
            if not isinstance(sheet_name_or_wb, XwWb):
                raise RuntimeError("App mode: use get_worksheet(wb, sheet_name)")
            
            wb_ctrl = sheet_name_or_wb
            sheet = sheet_name
            if sheet is None:
                raise ValueError("sheet_name required in app mode")
        
        self.log.debug(f"Accessing worksheet: {sheet}")
        
        # Worksheet 설정
        ws_ctrl = XwWs(
            wb_ctrl.book,  # type: ignore
            sheet=sheet,
            column_aliases=column_aliases,
            save_policy=self.policy.save,
            error_handling=self.policy.error_handling,
            drop_empty_rows=False,  # 빈 컬럼 유지 (Translation 등)
            clear_before_dataframe=True
        )
        ws_ctrl.__enter__()
        
        self.log.info(f"Worksheet accessed: {sheet}")
        
        return ws_ctrl
    
    def close(self) -> None:
        """Excel 파일 닫기 (역순: Wb → App)."""
        if not self._opened:
            return
        
        if self.wb_ctrl:
            self.wb_ctrl.__exit__(None, None, None)
            self.wb_ctrl = None
        
        if self.app_ctrl:
            self.app_ctrl.__exit__(None, None, None)
            self.app_ctrl = None
        
        self._opened = False
        self.log.debug("Excel file closed")
    
    # ==========================================================================
    # Context Manager Protocol
    # ==========================================================================
    
    def __enter__(self) -> "ExcelLoad":
        """Context manager entry - open() 호출."""
        self._context_managed = True
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close() 호출."""
        self.close()
        return None

