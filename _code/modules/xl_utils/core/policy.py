# -*- coding: utf-8 -*-
# xl_utils/policy.py
# xlwings 관련 모든 정책 정의 및 검증

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional


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
    """정책 통합 관리 클래스"""
    
    def __init__(
        self,
        app_policy: Optional[XwAppPolicy] = None,
        lifecycle_policy: Optional[XwLifecyclePolicy] = None,
        wb_policy: Optional[XwWbPolicy] = None,
        ws_policy: Optional[XwWsPolicy] = None,
    ):
        self.app = app_policy or XwAppPolicy() # pyright: ignore[reportCallIssue]
        self.lifecycle = lifecycle_policy or XwLifecyclePolicy() # pyright: ignore[reportCallIssue]
        self.wb = wb_policy or XwWbPolicy() # pyright: ignore[reportCallIssue]
        self.ws = ws_policy or XwWsPolicy() # pyright: ignore[reportCallIssue]
    
    @classmethod
    def from_dict(cls, config: dict) -> "XlPolicyManager":
        """딕셔너리에서 정책 로드"""
        return cls(
            app_policy=XwAppPolicy(**config.get("xw_app", {})),
            lifecycle_policy=XwLifecyclePolicy(**config.get("xw_lifecycle", {})),
            wb_policy=XwWbPolicy(**config.get("xw_wb", {})),
            ws_policy=XwWsPolicy(**config.get("xw_ws", {})),
        )