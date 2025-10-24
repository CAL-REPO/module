# -*- coding: utf-8 -*-
"""ExcelLoad - Excel load adapter (ImageLoad pattern).

책임:
1. Excel 파일 접근 및 셀 조작 (xlwings 기반)
2. Excel App → Workbook → Worksheet 생명주기 관리
3. Worksheet 객체 제공

ImageLoad, Translate, SyncCrawl 패턴과 동일:
- Policy: ExcelLoadPolicy (설정, target 없음)
- target은 인자로 받아서 처리
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
    """Excel Load Adapter - 순수 Excel 로드 로직 (ImageLoad pattern).
    
    image_utils.ImageLoad 패턴으로 구현:
    - ConfigLikeLoader for YAML/dict/Policy loading
    - logs_utils LogManager for logging
    - XlWorkflow for Excel operations
    - xlwings 기반 Excel 셀 조작 인터페이스 제공
    
    비즈니스 로직 (DataFrame 처리 등)은 사용자 단에서 수행
    xl_utils는 Excel 파일 접근 및 셀 조작만 담당
    
    Attributes:
        policy: ExcelLoadPolicy 설정
        log: loguru logger
    
    Usage:
        >>> # From YAML
        >>> excel_load = ExcelLoad("configs/excel_load.yaml")
        >>> with excel_load:
        ...     ws = excel_load.get_worksheet("data.xlsx", "Sheet1")
        ...     ws.cell_ops.write(1, 1, "제목")
        
        >>> # With runtime override
        >>> excel_load = ExcelLoad("configs.yaml", xw_app__visible=True)
        
        >>> # With external log_manager
        >>> excel_load = ExcelLoad("config.yaml", log_manager=my_log_manager)
    """
    
    def __init__(
        self,
        cfg_like: Union[ExcelLoadPolicy, Path, str, dict, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize ExcelLoad with configuration.
        
        Args:
            cfg_like: Configuration source:
                - ExcelLoadPolicy: Policy instance
                - str/Path: YAML file path
                - dict: Configuration dict
                - None: Use Pydantic defaults
            log_manager: External LogManager (선택사항)
            **overrides: Runtime overrides (e.g., xw_app__visible=True)
        
        Example:
            >>> # YAML path
            >>> excel_load = ExcelLoad("configs/excel_load.yaml")
            
            >>> # Dict
            >>> excel_load = ExcelLoad(config_dict)
            
            >>> # Runtime override
            >>> excel_load = ExcelLoad("configs.yaml", xw_app__visible=False)
            
            >>> # External logger
            >>> excel_load = ExcelLoad("config.yaml", log_manager=my_log_manager)
        """
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
        self.ws_ctrl: Optional[XwWs] = None
        
        # State
        self._current_excel_path: Optional[Path] = None
        self._current_sheet_name: Optional[Union[str, int]] = None
        self._current_column_aliases: Optional[Dict[str, List[str]]] = None
        self._context_managed = False
        self._initialized = False
        
        self.log.info("ExcelLoad initialized")
    
    # ==========================================================================
    # Configuration Loading (ConfigLikeLoader pattern)
    # ==========================================================================
    
    def _load_config(self, cfg_like, **overrides) -> ExcelLoadPolicy:
        """Load ExcelLoadPolicy from various sources (ImageLoad 패턴).
        
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
    
    def _initialize(
        self,
        excel_path: Union[str, Path],
        sheet_name: Optional[Union[str, int]] = None,
        column_aliases: Optional[Dict[str, List[str]]] = None
    ) -> None:
        """Excel 컴포넌트 초기화 (App → Wb → Ws).
        
        Args:
            excel_path: Excel file path
            sheet_name: Sheet name (optional, default: Sheet1)
            column_aliases: Column alias mapping (optional)
        """
        excel_path = Path(excel_path).resolve()
        target_sheet = sheet_name or 'Sheet1'
        
        # 이미 같은 파일/시트로 초기화되어 있으면 재사용
        if (self._initialized and 
            self._current_excel_path == excel_path and 
            self._current_sheet_name == target_sheet):
            return
        
        # 기존 컴포넌트 정리
        if self._initialized:
            self._cleanup()
        
        self.log.debug(f"Initializing Excel components: {excel_path.name}")
        
        # 1. App 시작 (통합 정책 사용)
        self.app_ctrl = XwApp(
            path=excel_path,
            app_policy=self.policy.xw_app,
            performance_policy=self.policy.performance
        )
        self.app_ctrl.__enter__()
        assert self.app_ctrl.app is not None, "App must be initialized after __enter__"
        
        # 2. Workbook 열기 (통합 정책 전달)
        self.wb_ctrl = XwWb(
            self.app_ctrl.app,
            path=excel_path,
            path_validation=self.policy.path_validation,
            save_policy=self.policy.save
        )
        self.wb_ctrl.__enter__()
        assert self.wb_ctrl.book is not None, "Book must be initialized after __enter__"
        
        # 3. Worksheet 설정 (통합 정책 전달)
        self.ws_ctrl = XwWs(
            self.wb_ctrl.book,
            sheet=target_sheet,
            column_aliases=column_aliases,
            save_policy=self.policy.save,
            error_handling=self.policy.error_handling,
            drop_empty_rows=True,  # 기본값
            clear_before_dataframe=True  # 기본값
        )
        self.ws_ctrl.__enter__()
        
        self._current_excel_path = excel_path
        self._current_sheet_name = target_sheet
        self._current_column_aliases = column_aliases
        self._initialized = True
        
        self.log.debug("Excel components initialized")
    
    def _cleanup(self) -> None:
        """Excel 컴포넌트 정리 (역순: Ws → Wb → App)"""
        if not self._initialized:
            return
        
        # 역순 종료 (XlWorkflow 패턴과 동일)
        if self.ws_ctrl:
            self.ws_ctrl.__exit__(None, None, None)
        
        if self.wb_ctrl:
            self.wb_ctrl.__exit__(None, None, None)
        
        if self.app_ctrl:
            self.app_ctrl.__exit__(None, None, None)
        
        self.app_ctrl = None
        self.wb_ctrl = None
        self.ws_ctrl = None
        self._initialized = False
        
        self.log.debug("Excel components cleaned up")
    
    # ==========================================================================
    # Main Operations (Excel 접근만 제공, 비즈니스 로직은 사용자 단)
    # ==========================================================================
    
    def get_worksheet(
        self,
        excel_path: Union[str, Path],
        sheet_name: Optional[Union[str, int]] = None,
        column_aliases: Optional[dict] = None
    ) -> XwWs:
        """Worksheet 제어 객체 반환
        
        사용자는 이 객체를 통해 xlwings 기반 셀 조작 수행
        
        Args:
            excel_path: Excel file path (required)
            sheet_name: Sheet name (optional, default: Sheet1)
            column_aliases: Column alias mapping (optional)
        
        Returns:
            XwWs instance (worksheet controller)
        
        Example:
            >>> excel_load = ExcelLoad("config.yaml")
            >>> with excel_load:
            ...     # With column aliases
            ...     from xl_utils.presets import get_preset
            ...     aliases = get_preset("PRODUCT_LIST")
            ...     ws = excel_load.get_worksheet("data.xlsx", "Sheet1", aliases)
            ...     
            ...     # Access with alias resolution
            ...     if ws.column_resolver:
            ...         actual_col = ws.column_resolver.resolve(df, "cas")
            ...         print(df[actual_col])
        """
        self._initialize(excel_path, sheet_name, column_aliases)
        
        self.log.info(f"[ExcelLoad] Accessing worksheet: {excel_path}")
        
        return self.ws_ctrl  # type: ignore
    
    # ==========================================================================
    # Context Manager Protocol
    # ==========================================================================
    
    def __enter__(self) -> "ExcelLoad":
        """Context manager entry.
        
        Note: 실제 초기화는 get_worksheet 호출 시 발생 (lazy initialization)
        """
        self._context_managed = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - 컴포넌트 정리"""
        self._cleanup()
        return None
