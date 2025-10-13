# -*- coding: utf-8 -*-
# xl_utils/policy.py
# xlwings 관련 모든 정책 정의 (App / Workbook)

from __future__ import annotations
from pydantic import BaseModel, Field

class XwAppPolicy(BaseModel):
    visible: bool = Field(True, description="Excel 창 표시 여부")
    display_alerts: bool = Field(False, description="경고창 표시 여부")
    screen_updating: bool = Field(True, description="화면 갱신 허용 여부")
    add_book: bool = Field(False, description="App 생성 시 기본 Workbook 추가 여부")
    quit_on_exit: bool = Field(True, description="직접 실행한 경우 with 종료 시 자동 종료 여부")

class XwWbPolicy(BaseModel):
    auto_save: bool = Field(False, description="워크북 변경 시 자동 저장 여부")
    must_exist: bool = Field(True, description="파일이 반드시 존재해야 하는지 여부")
    create_if_missing: bool = Field(False, description="파일이 없을 경우 새로 생성 여부")

