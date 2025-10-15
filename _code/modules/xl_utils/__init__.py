"""
xl_utils
--------
Excel automation and worksheet utilities for data extraction and manipulation.
Exports only intended API.

Main Components:
- XlController: Main entrypoint (translate_utils.Translator pattern)
- XlWorkflow: Excel workflow orchestration (App → Wb → Ws lifecycle management)
- XlPolicyManager: Unified policy management
- XwWs: Worksheet services (cell manipulation via xlwings)

비즈니스 로직 (DataFrame 처리 등)은 사용자 단에서 수행
xl_utils는 Excel 파일 접근 및 셀 조작만 담당
"""
from .core.policy import (
    XlPolicyManager,
    XwAppPolicy,
    XwLifecyclePolicy,
    XwWbPolicy,
    XwWsPolicy,
    LogConfig,
    TargetConfig,
)
from .services.xw_app import XwApp
from .services.xw_wb import XwWb
from .services.xw_ws import XwWs
from .services.save_manager import XwSaveManager
from .services.workflow import XlWorkflow
from .services.controller import XlController

__all__ = [
    # Main API
    "XlController",
    "XlWorkflow",
    
    # Policy
    "XlPolicyManager",
    "XwAppPolicy",
    "XwLifecyclePolicy",
    "XwWbPolicy",
    "XwWsPolicy",
    "LogConfig",
    "TargetConfig",
    
    # Services (low-level)
    "XwApp",
    "XwWb",
    "XwWs",
    "XwSaveManager",
]
