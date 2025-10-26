# -*- coding: utf-8 -*-
"""XLOTO Pipeline Policy - Logging + Paths configuration only.

책임:
1. XLOTO 파이프라인 로그 정책 관리
2. 이미지 경로 정책 관리
3. 서브 모듈 정책은 SectionExtractor로 동적 추출 (Pass-through Pattern)
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional

from logs_utils.core.policy import LogPolicy
from xl_utils.core.policy import SheetConfig


class XlOtoPathsPolicy(BaseModel):
    """이미지 경로 정책.
    
    Attributes:
        public_img_dir: 공용 이미지 디렉토리
        origin_dirname: 원본 이미지 폴더명
        translated_dirname: 번역 이미지 폴더명
    """
    public_img_dir: str = Field(
        "${public_dir}/01.IMAGE",
        description="공용 이미지 디렉토리"
    )
    origin_dirname: str = "original"
    translated_dirname: str = "translated"


class XlOtoExcelConfig(BaseModel):
    """XLOTO Excel 설정 (단일 파일/시트).
    
    Attributes:
        file_path: Excel 파일 경로
        sheet: Sheet 설정 (xl_utils.SheetConfig)
    
    Example:
        >>> XlOtoExcelConfig(
        ...     file_path="data.xlsx",
        ...     sheet=SheetConfig(sheet_name="Purchase", column_alias="PRODUCT_LIST")
        ... )
    """
    file_path: str = Field(..., description="Excel 파일 경로")
    sheet: SheetConfig = Field(
        default_factory=SheetConfig,  # type: ignore
        description="Sheet 설정"
    )


class XlOtoPolicy(BaseModel):
    """XLOTO Pipeline 정책 (Pass-through Pattern + Excel 설정).
    
    Excel + OTO 파이프라인 통합 정책.
    서브 모듈 정책은 SectionExtractor로 동적으로 추출됩니다.
    
    서브 모듈 정책 관리 (SectionExtractor 사용):
    - oto: OTO config dict (Oto Adapter에서 처리)
    
    Attributes:
        name: Policy 이름 ("xloto")
        excel: Excel 파일/시트 설정
        paths: 이미지 경로 정책
        log: XLOTO 파이프라인 로그 정책
    
    Example:
        >>> # xloto_config.yaml
        >>> xloto:
        ...   excel:
        ...     file_path: "data.xlsx"
        ...     sheet:
        ...       sheet_name: "Purchase"
        ...       column_alias: "PRODUCT_LIST"
        ...   paths: ...
        ...   log: ...
    
    Note:
        ⚠️ OTO 서브 모듈 정책 필드는 없음 (SectionExtractor가 동적 추출).
        ⚠️ ConfigLoader 섹션명과 Policy.name 필드가 일치해야 함.
    """
    name: str = "xloto"
    
    # ===== Excel 설정 =====
    excel: XlOtoExcelConfig = Field(
        ...,  # Required!
        description="Excel 파일/시트 설정"
    )
    
    paths: XlOtoPathsPolicy = Field(
        default_factory=XlOtoPathsPolicy,  # type: ignore
        description="이미지 경로 정책"
    )
    log: LogPolicy = Field(
        default_factory=LogPolicy,
        description="XLOTO 통합 로그 정책"
    )
