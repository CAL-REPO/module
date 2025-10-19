# -*- coding: utf-8 -*-
"""
xl_utils/entry_point/xl_controller.py
Excel Controller - Main entrypoint for xl_utils

translate_utils.Translator와 동일한 패턴:
- ConfigLoader integration for YAML/dict/Policy loading
- logs_utils LogContextManager for logging
- Context manager support
- xlwings 기반 Excel 셀 조작 인터페이스 제공

비즈니스 로직 (DataFrame 처리 등)은 사용자 단에서 수행
xl_utils는 Excel 파일 접근 및 셀 조작만 담당

다른 모듈에서 재사용 가능:
    >>> from xl_utils.entry_point import XlController
    >>> 
    >>> # ConfigLoader로 설정 주입
    >>> config = ConfigLoader(src=("configs/excel.yaml", "excel"))
    >>> excel_config = config.to_dict()
    >>> 
    >>> # XlController 사용
    >>> with XlController(cfg_like=excel_config) as xl:
    ...     ws = xl.get_worksheet()
    ...     df = ws.to_dataframe()

Example:
    >>> # YAML config
    >>> with XlController("configs/excel.yaml") as xl:
    ...     ws = xl.get_worksheet()
    ...     ws.cell_ops.write(1, 1, "제목")
    ...     ws.cell_ops.write_range("A2:C10", data_list)
    ...     ws.cell_ops.apply_format("A1", bold=True)
    
    >>> # DataFrame 변환 (편의 메서드)
    >>> with XlController("configs.yaml") as xl:
    ...     ws = xl.get_worksheet()
    ...     df = ws.to_dataframe(anchor="A1")
    ...     # ... 비즈니스 로직 (외부에서 처리) ...
    ...     ws.from_dataframe(processed_df, anchor="A10")
"""

from __future__ import annotations
from pathlib import Path
from typing import Union, Optional, Any
import pandas as pd

from cfg_utils import ConfigLoader
from logs_utils import LogContextManager
from structured_io import BaseParserPolicy

from xl_utils.core.policy import XlPolicyManager
from xl_utils.services.workflow import XlWorkflow
from xl_utils.services.xw_ws import XwWs


class DummyLogger:
    """No-op logger when logging is disabled."""
    def debug(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def success(self, *args, **kwargs): pass


class XlController:
    """Excel Controller - Main entrypoint for xl_utils.
    
    translate_utils.Translator와 동일한 패턴으로 구현:
    - ConfigLoader for YAML/dict/Policy loading
    - logs_utils LogContextManager for logging
    - XlWorkflow for Excel operations
    - xlwings 기반 Excel 셀 조작 인터페이스 제공
    
    비즈니스 로직 (DataFrame 처리 등)은 사용자 단에서 수행
    xl_utils는 Excel 파일 접근 및 셀 조작만 담당
    
    다른 모듈에서 재사용 가능:
        - cfg_utils ConfigLoader로 설정 주입
        - dict, YAML path, Policy instance 모두 지원
        - 런타임 오버라이드 가능 (xw_app__visible=True)
    
    Usage:
        >>> # From YAML
        >>> with XlController("configs/excel.yaml") as xl:
        ...     ws = xl.get_worksheet()
        ...     ws.cell_ops.write(1, 1, "제목")
        ...     ws.cell_ops.write_range("A2:C10", data_list)
        
        >>> # With runtime override
        >>> controller = XlController("configs.yaml", xw_app__visible=True)
        
        >>> # DataFrame 변환 (편의 메서드)
        >>> with XlController("configs.yaml") as xl:
        ...     ws = xl.get_worksheet()
        ...     df = ws.to_dataframe(anchor="A1")
        ...     # ... 비즈니스 로직 (외부에서 처리) ...
        ...     ws.from_dataframe(processed_df, anchor="A10")
        
        >>> # ConfigLoader로 설정 주입 (다른 모듈에서 재사용)
        >>> config = ConfigLoader(src=("configs/excel.yaml", "excel"))
        >>> excel_config = config.to_dict()
        >>> with XlController(cfg_like=excel_config) as xl:
        ...     ws = xl.get_worksheet()
    """
    
    def __init__(
        self,
        cfg_like: Union[XlPolicyManager, Path, str, dict, None] = None,
        *,
        log: Optional[LogContextManager] = None,
        **overrides: Any
    ):
        """Initialize XlController with configuration.
        
        Args:
            cfg_like: Configuration source:
                - XlPolicyManager: Policy instance
                - str/Path: YAML file path
                - dict: Configuration dict (ConfigLoader.to_dict() 결과)
                - None: Use default configs/excel.yaml
            log: External LogContextManager (if None, use policy.log)
            **overrides: Runtime overrides (e.g., xw_app__visible=True)
        
        Example:
            >>> # YAML path
            >>> xl = XlController("configs/excel.yaml")
            
            >>> # Dict (ConfigLoader 결과)
            >>> config = ConfigLoader(src=("configs/excel.yaml", "excel"))
            >>> xl = XlController(config.to_dict())
            
            >>> # Runtime override
            >>> xl = XlController("configs.yaml", xw_app__visible=False)
            
            >>> # External logger
            >>> xl = XlController("config.yaml", log=my_logger)
        """
        # Load policy using cfg_utils v2 pattern
        self.policy = self._load_config(cfg_like, **overrides)
        
        # Setup logging
        self._external_log = log
        self._setup_logging()
        
        # Initialize workflow
        self._workflow: Optional[XlWorkflow] = None
        self._context_managed = False
    
    # ==========================================================================
    # Configuration Loading (cfg_utils v2 pattern)
    # ==========================================================================
    
    def _load_config(
        self,
        cfg_like: Union[XlPolicyManager, Path, str, dict, None],
        **overrides: Any
    ) -> XlPolicyManager:
        """Load XlPolicyManager using cfg_utils v2 API.
        
        Args:
            cfg_like: Configuration source
            **overrides: Runtime overrides (xw_app__visible=True)
        
        Returns:
            XlPolicyManager instance
        """
        # 1. Already a Policy instance
        if isinstance(cfg_like, XlPolicyManager):
            if not overrides:
                return cfg_like
            # With overrides, convert to dict and apply
            cfg_dict = {
                "xw_app": cfg_like.app.model_dump(),
                "xw_lifecycle": cfg_like.lifecycle.model_dump(),
                "xw_wb": cfg_like.wb.model_dump(),
                "xw_ws": cfg_like.ws.model_dump(),
            }
            if cfg_like.logging:
                cfg_dict["log"] = cfg_like.logging.model_dump()
            if cfg_like.target:
                cfg_dict["target"] = cfg_like.target.model_dump()
            
            cfg_dict = self._apply_overrides(cfg_dict, **overrides)
            return XlPolicyManager.from_dict(cfg_dict)
        
        # 2. dict 직접 사용 (ConfigLoader.to_dict() 결과)
        if isinstance(cfg_like, dict):
            cfg_dict = cfg_like.copy()
            if overrides:
                cfg_dict = self._apply_overrides(cfg_dict, **overrides)
            return XlPolicyManager.from_dict(cfg_dict)
        
        # 3. YAML 파일 또는 None (기본 경로)
        cfg_path = cfg_like
        if cfg_like is None:
            # 기본 경로 시도: modules/xl_utils/configs/excel.yaml
            current = Path(__file__).parent.parent
            default_path = current / "configs" / "excel.yaml"
            if not default_path.exists():
                # 기본 정책 사용
                cfg_dict = {}
                if overrides:
                    cfg_dict = self._apply_overrides(cfg_dict, **overrides)
                return XlPolicyManager.from_dict(cfg_dict)
            cfg_path = default_path
        
        # 4. cfg_utils v2 API 사용
        try:
            loader = ConfigLoader(src=(str(cfg_path), "excel"))
            cfg_dict = loader.to_dict()
            
            # 'excel' 섹션이 있으면 추출
            if 'excel' in cfg_dict:
                cfg_dict = cfg_dict['excel']
        except Exception as e:
            # 로드 실패 시 기본 정책
            print(f"[WARN] Failed to load config from {cfg_path}: {e}")
            cfg_dict = {}
        
        # 5. Apply runtime overrides
        if overrides:
            cfg_dict = self._apply_overrides(cfg_dict, **overrides)
        
        return XlPolicyManager.from_dict(cfg_dict)
    
    def _apply_overrides(self, cfg_dict: dict, **overrides: Any) -> dict:
        """Apply runtime overrides to config dict.
        
        Example: xw_app__visible=False → cfg_dict['xw_app']['visible'] = False
        """
        for key, value in overrides.items():
            parts = key.split('__')
            if len(parts) == 2:
                section, field = parts
                if section not in cfg_dict:
                    cfg_dict[section] = {}
                cfg_dict[section][field] = value
        
        return cfg_dict
    
    # ==========================================================================
    # Logging Setup
    # ==========================================================================
    
    def _setup_logging(self) -> None:
        """Setup logging (translate_utils pattern).
        
        Uses external logger if provided, otherwise creates from policy.logging
        """
        if self._external_log:
            self.logger = self._external_log
            return
        
        # Create logger from policy.logging if available
        if hasattr(self.policy, 'logging') and self.policy.logging:
            try:
                from logs_utils import LogManager
                log_mgr = LogManager(self.policy.logging)
                self.logger = log_mgr.logger
            except Exception as e:
                self.logger = DummyLogger()
        else:
            self.logger = DummyLogger()
    
    # ==========================================================================
    # Workflow Management
    # ==========================================================================
    
    def _get_workflow(
        self,
        excel_path: Optional[Union[str, Path]] = None,
        sheet_name: Optional[Union[str, int]] = None
    ) -> XlWorkflow:
        """Get or create XlWorkflow instance.
        
        Args:
            excel_path: Excel file path (overrides config)
            sheet_name: Sheet name (overrides config)
        
        Returns:
            XlWorkflow instance
        """
        # policy.target에서 정보 추출
        target_path = excel_path
        target_sheet = sheet_name or 'Sheet1'
        
        if not target_path and hasattr(self.policy, 'target') and self.policy.target:
            target_path = self.policy.target.excel_path
            target_sheet = self.policy.target.sheet_name or 'Sheet1'
        
        if not target_path:
            raise ValueError("excel_path must be provided in config or as argument")
        
        if self._workflow is None:
            self._workflow = XlWorkflow(
                excel_path=target_path,
                sheet_name=target_sheet,
                policy_mgr=self.policy
            )
        
        return self._workflow
    
    # ==========================================================================
    # Main Operations (Excel 접근만 제공, 비즈니스 로직은 사용자 단)
    # ==========================================================================
    
    def get_worksheet(
        self,
        *,
        excel_path: Optional[Union[str, Path]] = None,
        sheet_name: Optional[Union[str, int]] = None
    ) -> XwWs:
        """Worksheet 제어 객체 반환
        
        사용자는 이 객체를 통해 xlwings 기반 셀 조작 수행
        
        Args:
            excel_path: Excel file path (overrides config)
            sheet_name: Sheet name (overrides config)
        
        Returns:
            XwWs instance (worksheet controller)
        
        Example:
            >>> ws = xl.get_worksheet()
            >>> ws.cell_ops.write(1, 1, "제목")
            >>> ws.cell_ops.write_range("A2:C10", data_list)
            >>> ws.cell_ops.apply_format("A1", bold=True, font_size=14)
        """
        workflow = self._get_workflow(excel_path, sheet_name)
        
        self.logger.info(f"[XlController] Accessing worksheet")
        
        return workflow.get_worksheet()
    
    def get_workflow(
        self,
        *,
        excel_path: Optional[Union[str, Path]] = None,
        sheet_name: Optional[Union[str, int]] = None
    ) -> XlWorkflow:
        """Workflow 객체 반환 (고급 사용자용)
        
        Args:
            excel_path: Excel file path (overrides config)
            sheet_name: Sheet name (overrides config)
        
        Returns:
            XlWorkflow instance
        """
        return self._get_workflow(excel_path, sheet_name)
    
    # ==========================================================================
    # Context Manager Protocol
    # ==========================================================================
    
    def __enter__(self) -> "XlController":
        """Context manager entry."""
        self._context_managed = True
        
        # Workflow는 나중에 lazy 초기화
        if self._workflow:
            self._workflow.__enter__()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if self._workflow and self._workflow._initialized:
            self._workflow.__exit__(exc_type, exc_val, exc_tb)
        
        return None
