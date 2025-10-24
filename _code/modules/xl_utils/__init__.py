"""
xl_utils
--------
Excel automation and worksheet utilities for data extraction and manipulation.
Exports only intended API.

Main Components:
- ExcelLoader: Main entrypoint (ImageLoader pattern)
- ExcelLoad: Adapter for pure Excel logic

비즈니스 로직 (DataFrame 처리 등)은 사용자 단에서 수행
xl_utils는 Excel 파일 접근 및 셀 조작만 담당

다른 모듈에서 재사용:
    >>> from xl_utils import ExcelLoader
    >>> 
    >>> # From YAML config
    >>> with ExcelLoader("configs/excel_loader.yaml") as xl:
    ...     ws = xl.get_worksheet()
    ...     ws.cell_ops.write(1, 1, "Title")
    
    >>> # Direct adapter usage (advanced)
    >>> from xl_utils import ExcelLoad
    >>> excel_load = ExcelLoad("configs/excel_load.yaml")
    >>> with excel_load:
    ...     ws = excel_load.get_worksheet("data.xlsx", "Sheet1")
"""
from .core.policy import (
    # New Policies (Adapter vs EntryPoint pattern)
    ExcelLoadPolicy,
    ExcelLoaderPolicy,
    
    # Sub-policies
    XwAppPolicy,
    SourceConfig,  # 변경: TargetConfig → SourceConfig
    SheetConfig,   # 신규 추가
    
    # Unified Policies
    SavePolicy,
    PerformancePolicy,
    ErrorHandlingPolicy,
    PathValidationPolicy,
)

# Adapter (비즈니스 로직, source 없음)
from .adapter import ExcelLoad

# EntryPoint (외부 진입점, source 포함)
from .entry_point import ExcelLoader

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
    # Adapter (비즈니스 로직, source 없음)
    "ExcelLoad",
    
    # EntryPoint (외부 진입점, source 포함)
    "ExcelLoader",
    
    # New Policies (Adapter vs EntryPoint pattern)
    "ExcelLoadPolicy",
    "ExcelLoaderPolicy",
    
    # Sub-policies
    "XwAppPolicy",
    "SourceConfig",  # 변경: TargetConfig → SourceConfig
    "SheetConfig",   # 신규 추가
    
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
