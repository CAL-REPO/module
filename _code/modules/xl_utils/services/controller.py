# -*- coding: utf-8 -*-
"""
xl_utils/services/controller.py
Excel Controller - Main entrypoint for xl_utils

translate_utils.Translator와 동일한 패턴:
- ConfigLoader integration for YAML/dict/Policy loading
- logs_utils LogContextManager for logging
- Context manager support
- xlwings 기반 Excel 셀 조작 인터페이스 제공

비즈니스 로직 (DataFrame 처리 등)은 사용자 단에서 수행
xl_utils는 Excel 파일 접근 및 셀 조작만 담당

Example:
    >>> # YAML config
    >>> with XlController("configs/excel.yaml") as xl:
    ...     ws = xl.get_worksheet()
    ...     ws.write_cell(1, 1, "제목")
    ...     ws.write_range("A2:C10", data_list)
    ...     ws.apply_format("A1", bold=True)
    
    >>> # DataFrame 변환 (필요시)
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

from cfg_utils import ConfigLoader, ConfigPolicy
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
    
    Usage:
        >>> # From YAML
        >>> with XlController("configs/excel.yaml") as xl:
        ...     ws = xl.get_worksheet()
        ...     ws.write_cell(1, 1, "제목")
        ...     ws.write_range("A2:C10", data_list)
        
        >>> # With runtime override
        >>> controller = XlController("configs.yaml", xw_app__visible=True)
        
        >>> # DataFrame 변환 (필요시)
        >>> with XlController("configs.yaml") as xl:
        ...     ws = xl.get_worksheet()
        ...     df = ws.to_dataframe(anchor="A1")
        ...     # ... 비즈니스 로직 (외부에서 처리) ...
        ...     ws.from_dataframe(processed_df, anchor="A10")
    """
    
    def __init__(
        self,
        cfg_like: Union[XlPolicyManager, Path, str, dict, list, None] = None,
        *,
        policy_overrides: Optional[dict] = None,
        **overrides: Any
    ):
        """Initialize XlController with configuration.
        
        Args:
            cfg_like: Configuration source:
                - XlPolicyManager: Policy instance
                - str/Path: YAML file path
                - dict: Configuration dict
                - list[str/Path]: Multiple YAML files (merged)
                - None: Use default configs/excel.yaml
            policy_overrides: ConfigPolicy 필드 개별 오버라이드 (merge_mode, yaml.source_paths 등)
            **overrides: Runtime overrides (e.g., xw_app__visible=True)
        
        Example:
            >>> # YAML path
            >>> xl = XlController("configs/excel.yaml")
            
            >>> # Multiple files
            >>> xl = XlController(["base.yaml", "override.yaml"])
            
            >>> # Dict
            >>> xl = XlController({"xw_app": {"visible": True}})
            
            >>> # Runtime override
            >>> xl = XlController("configs.yaml", xw_app__visible=False)
        """
        self.config = self._load_config(cfg_like, policy_overrides=policy_overrides, **overrides)
        self._workflow: Optional[XlWorkflow] = None
        self._logging_active = False
        self._context_managed = False
        self._setup_logging()
    
    # ==========================================================================
    # Configuration Loading
    # ==========================================================================
    
    def _load_config(
        self,
        cfg_like: Union[XlPolicyManager, Path, str, dict, list, None],
        *,
        policy_overrides: Optional[dict] = None,
        **overrides: Any
    ) -> XlPolicyManager:
        """Load configuration (완전 간소화 버전)
        
        Args:
            cfg_like: 설정 소스 (list 지원)
            policy_overrides: ConfigPolicy 필드 개별 오버라이드 (merge_mode, yaml.source_paths 등)
            **overrides: 런타임 오버라이드
        
        Returns:
            XlPolicyManager 인스턴스
        """
        # 1. Already a Policy instance
        if isinstance(cfg_like, XlPolicyManager):
            if not overrides:
                return cfg_like
            # With overrides, reload from default and apply overrides
            default_path = Path("modules/xl_utils/configs/excel.yaml")
            if policy_overrides is None:
                policy_overrides = {}
            
            policy_overrides.setdefault("yaml.source_paths", {
                "path": str(default_path),
                "section": "excel"
            })
            
            cfg_dict = ConfigLoader.load(None, policy_overrides=policy_overrides)
            cfg_dict = self._apply_overrides(cfg_dict, **overrides)
            return XlPolicyManager.from_dict(cfg_dict)
        
        # 2. ConfigLoader.load() 사용 (list 자동 병합 지원)
        if cfg_like is None:
            default_path = Path("modules/xl_utils/configs/excel.yaml")
            if policy_overrides is None:
                policy_overrides = {}
            
            policy_overrides.setdefault("yaml.source_paths", {
                "path": str(default_path),
                "section": "excel"
            })
        
        cfg_dict = ConfigLoader.load(cfg_like, policy_overrides=policy_overrides)
        
        # 3. Apply runtime overrides
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
        """Setup logging using logs_utils.LogContextManager.
        
        translate_utils.Translator._setup_logging과 동일한 패턴
        """
        if not hasattr(self.config, 'logging') or not self.config.logging:
            self.logger = DummyLogger()
            return
        
        log_config = self.config.logging
        
        try:
            # LogConfig는 translate_utils 스타일 (name, sinks)
            # logs_utils.LogContextManager와 호환되지 않으므로 DummyLogger 사용
            # 실제 프로덕션에서는 log_config.sinks를 파싱하여 LogContextManager 설정
            self.logger = DummyLogger()
            self._logging_active = False
            
            print(f"[INFO] Logging config detected: {log_config.name}")
            
        except Exception as e:
            print(f"[WARN] Logging setup failed: {e}")
            self.logger = DummyLogger()
    
    def _teardown_logging(self) -> None:
        """Teardown logging context."""
        if self._logging_active and hasattr(self, 'log_context'):
            self.log_context.__exit__(None, None, None)
            self._logging_active = False
    
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
        # config에서 target 정보 추출
        target_path = excel_path or getattr(self.config, 'target_excel_path', None)
        target_sheet = sheet_name or getattr(self.config, 'target_sheet_name', 'Sheet1')
        
        if not target_path:
            raise ValueError("excel_path must be provided in config or as argument")
        
        if self._workflow is None:
            self._workflow = XlWorkflow(
                excel_path=target_path,
                sheet_name=target_sheet,
                policy_mgr=self.config
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
            >>> ws.write_cell(1, 1, "제목")
            >>> ws.write_range("A2:C10", data_list)
            >>> ws.apply_format("A1", bold=True, font_size=14)
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
        
        self._teardown_logging()
        
        return None
