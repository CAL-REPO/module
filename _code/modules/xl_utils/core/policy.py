# -*- coding: utf-8 -*-
# xl_utils/policy.py
# xlwings 관련 모든 정책 정의 및 검증
# translate_utils.core.policy 패턴 적용: cfg_utils/logs_utils 통합

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from pathlib import Path

from cfg_utils import ConfigLoader, ConfigPolicy
from structured_io import BaseParserPolicy


class LogConfig(BaseModel):
    """Logging configuration model compatible with logs_utils.LogContextManager"""
    name: str = Field(default="Translator")
    sinks: List[Dict[str, Any]] = Field(default_factory=lambda: [
        {
            "sink_type": "console",
            "level": "INFO",
            "format": "<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> | <level>{message}</level>",
            "colorize": True
        }
    ])


class TargetConfig(BaseModel):
    """Target Excel file and sheet configuration"""
    excel_path: str = Field(default="", description="Excel file path")
    sheet_name: str = Field(default="Sheet1", description="Target sheet name or index")


class XwAppPolicy(BaseModel):
    """Excel Application 실행 정책"""
    visible: bool = Field(True, description="Excel 창 표시 여부")
    display_alerts: bool = Field(False, description="경고창 표시 여부")
    screen_updating: bool = Field(True, description="화면 갱신 허용 여부")
    add_book: bool = Field(False, description="App 생성 시 기본 Workbook 추가 여부")


class XwLifecyclePolicy(BaseModel):
    """Excel Application 수명주기 정책"""
    quit_on_exit: bool = Field(True, description="Context 종료 시 자동 종료 여부")
    save_on_exit: bool = Field(True, description="Context 종료 시 자동 저장 여부")
    save_attached_instance: bool = Field(False, description="기존 Excel 인스턴스도 저장할지 여부")


class XwWbPolicy(BaseModel):
    """Workbook 관리 정책"""
    auto_save: bool = Field(False, description="워크북 변경 시 자동 저장 여부")
    must_exist: bool = Field(True, description="파일이 반드시 존재해야 하는지 여부")
    create_if_missing: bool = Field(False, description="파일이 없을 경우 새로 생성 여부")

    @field_validator('create_if_missing')
    @classmethod
    def validate_create_policy(cls, v: bool, info) -> bool:
        """must_exist=True이면 create_if_missing=True 불가"""
        if info.data.get('must_exist') and v:
            raise ValueError("must_exist=True일 때 create_if_missing=True 불가")
        return v


class XwWsPolicy(BaseModel):
    """Worksheet 조작 정책"""
    create_if_missing: bool = Field(True, description="시트가 없을 경우 생성 여부")
    auto_save_on_write: bool = Field(False, description="셀 쓰기 시 자동 저장 여부")
    clear_before_dataframe: bool = Field(True, description="DataFrame 쓰기 전 시트 초기화")
    drop_empty_rows: bool = Field(True, description="DataFrame 변환 시 빈 행 제거")


class XlPolicyManager:
    """정책 통합 관리 클래스 (translate_utils 패턴 적용)"""
    
    def __init__(
        self,
        app_policy: Optional[XwAppPolicy] = None,
        lifecycle_policy: Optional[XwLifecyclePolicy] = None,
        wb_policy: Optional[XwWbPolicy] = None,
        ws_policy: Optional[XwWsPolicy] = None,
        logging: Optional[LogConfig] = None,
        target: Optional[TargetConfig] = None,
    ):
        self.app = app_policy or XwAppPolicy() # pyright: ignore[reportCallIssue]
        self.lifecycle = lifecycle_policy or XwLifecyclePolicy() # pyright: ignore[reportCallIssue]
        self.wb = wb_policy or XwWbPolicy() # pyright: ignore[reportCallIssue]
        self.ws = ws_policy or XwWsPolicy() # pyright: ignore[reportCallIssue]
        self.logging = logging
        self.target = target or TargetConfig()
        
        # target 정보를 편리하게 접근
        self.target_excel_path = self.target.excel_path if self.target else ""
        self.target_sheet_name = self.target.sheet_name if self.target else "Sheet1"
    
    @classmethod
    def from_dict(cls, config: dict) -> "XlPolicyManager":
        """딕셔너리에서 정책 로드 (translate_utils 패턴)"""
        return cls(
            app_policy=XwAppPolicy(**config.get("xw_app", {})),
            lifecycle_policy=XwLifecyclePolicy(**config.get("xw_lifecycle", {})),
            wb_policy=XwWbPolicy(**config.get("xw_wb", {})),
            ws_policy=XwWsPolicy(**config.get("xw_ws", {})),
            logging=LogConfig(**config.get("logging", {})) if config.get("logging") else None,
            target=TargetConfig(**config.get("target", {})) if config.get("target") else None,
        )
    
    @staticmethod
    def load(
        cfg_like: str | Path | dict | BaseModel | None = None,
        *,
        policy: ConfigPolicy | None = None
    ) -> "XlPolicyManager":
        """ConfigLoader를 사용한 로딩 (translate_utils 패턴)
        
        기본 동작:
        - cfg_like이 None이면 'xl_utils/configs/excel.yaml' 시도
        - 파일이 없으면 기본 정책 사용 (argument만으로 설정 가능)
        - 파일이 있으면 로드하여 사용
        """
        if isinstance(cfg_like, XlPolicyManager):
            return cfg_like
        
        # Case 1: None - 기본 YAML 경로 시도, 없으면 기본 정책
        if cfg_like is None:
            default_path = Path("modules/xl_utils/config/excel.yaml")
            if default_path.exists():
                cfg_like = default_path
            else:
                # YAML 파일 없으면 기본 정책 사용 (argument로 설정 가능)
                return XlPolicyManager()
        
        # Case 2: dict - 바로 from_dict
        if isinstance(cfg_like, dict):
            # 'excel' 섹션이 있으면 추출
            if 'excel' in cfg_like:
                cfg_like = cfg_like['excel']
            return XlPolicyManager.from_dict(cfg_like)
        
        # Case 3: YAML 파일 경로 - ConfigLoader 사용
        # ConfigLoader 생성
        loader = ConfigLoader(cfg_like, policy=policy or ConfigPolicy())
        cfg_dict = loader.as_dict()
        
        # 'excel' 섹션이 있으면 추출 (기본 섹션)
        if 'excel' in cfg_dict:
            cfg_dict = cfg_dict['excel']
        
        return XlPolicyManager.from_dict(cfg_dict)
