"""
xl_utils
--------
Excel automation and worksheet utilities for data extraction and manipulation.
Exports only intended API.

Main Component:
- ExcelLoad: Adapter for Excel file access and cell manipulation

비즈니스 로직 (DataFrame 처리 등)은 사용자 단에서 수행
xl_utils는 Excel 파일 접근 및 셀 조작만 담당

다른 모듈에서 재사용:
    >>> from xl_utils import ExcelLoad
    >>> 
    >>> # From YAML config
    >>> excel_load = ExcelLoad("configs/excel_load.yaml")
    >>> with excel_load:
    ...     ws = excel_load.get_worksheet("data.xlsx", "Sheet1")
    ...     ws.cell_ops.write(1, 1, "Title")
    
    >>> # With runtime override
    >>> excel_load = ExcelLoad("config.yaml", xw_app__visible=True)
"""
from .core.policy import (
    # Adapter Policy
    ExcelLoadPolicy,
    
    # Sub-policies
    XwAppPolicy,
    SheetConfig,
    
    # Unified Policies
    SavePolicy,
    PerformancePolicy,
    ErrorHandlingPolicy,
    PathValidationPolicy,
)

# Adapter (비즈니스 로직)
from .adapter import ExcelLoad

# Services (low-level)
from .services.xw_app import XwApp
from .services.xw_wb import XwWb
from .services.xw_ws import XwWs
from .services.save_manager import XwSaveManager
from .services.column_resolver import ColumnResolver

# Core helpers
from .core.save_helper import SavePolicyHelper

# Presets
from .presets import get_preset, PRESETS

__all__ = [
    # Adapter
    "ExcelLoad",
    
    # Policies
    "ExcelLoadPolicy",
    
    # Sub-policies
    "XwAppPolicy",
    "SheetConfig",
    
    # Unified Policies
    "SavePolicy",
    "PerformancePolicy",
    "ErrorHandlingPolicy",
    "PathValidationPolicy",
    
    # Services (low-level)
    "XwApp",
    "XwWb",
    "XwWs",
    "XwSaveManager",
    "ColumnResolver",
    
    # Core helpers
    "SavePolicyHelper",
    
    # Presets
    "get_preset",
    "PRESETS",
]
