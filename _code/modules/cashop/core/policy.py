# -*- coding: utf-8 -*-
"""cashop 공통 Policy - 여러 파이프라인에서 재사용되는 정책.

책임:
1. 경로 정책 관리 (CashopPathsPolicy)
2. Excel 설정 관리 (CashopExcelConfig)
3. xloto, xlcrawl 등 여러 파이프라인에서 공통으로 사용

사용 예:
    >>> from cashop.core.policy import CashopPathsPolicy, CashopExcelConfig
    >>> 
    >>> # xloto에서 사용
    >>> class XlOtoPolicy(BaseModel):
    ...     excel: CashopExcelConfig
    ...     paths: CashopPathsPolicy
    >>> 
    >>> # xlcrawl에서 사용
    >>> class XlCrawlPolicy(BaseModel):
    ...     excel: CashopExcelConfig
    ...     paths: CashopPathsPolicy
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional

from xl_utils.core.policy import SheetConfig
from logs_utils.core.policy import LogPolicy


class CashopPathsPolicy(BaseModel):
    """cashop 경로 정책 (xloto, xlcrawl 공통).
    
    여러 파이프라인에서 공통으로 사용되는 경로 설정.
    
    Attributes:
        public_img_dir: 공용 이미지 디렉토리 (xloto 이미지 저장)
        origin_dirname: 원본 이미지 폴더명 (xloto)
        translated_dirname: 번역 이미지 폴더명 (xloto)
        output_dir: 크롤링 결과 저장 디렉토리 (xlcrawl)
    
    Example:
        >>> # xloto에서 사용
        >>> paths = CashopPathsPolicy(
        ...     public_img_dir="${public_dir}/01.IMAGE",
        ...     origin_dirname="original",
        ...     translated_dirname="translated"
        ... )
        >>> 
        >>> # xlcrawl에서 사용
        >>> paths = CashopPathsPolicy(
        ...     output_dir="output/crawl"
        ... )
    """
    # ===== xloto 전용 경로 =====
    public_img_dir: str = Field(
        "${public_dir}/01.IMAGE",
        description="공용 이미지 디렉토리 (xloto)"
    )
    origin_dirname: str = Field(
        "original",
        description="원본 이미지 폴더명 (xloto)"
    )
    translated_dirname: str = Field(
        "translated",
        description="번역 이미지 폴더명 (xloto)"
    )
    
    # ===== xlcrawl 전용 경로 =====
    output_dir: str = Field(
        "output/crawl",
        description="크롤링 결과 저장 디렉토리 (xlcrawl)"
    )


class CashopExcelConfig(BaseModel):
    """cashop Excel 설정 (단일 파일/시트, xloto/xlcrawl 공통).
    
    여러 파이프라인에서 공통으로 사용되는 Excel 파일/시트 설정.
    
    Attributes:
        file_path: Excel 파일 경로
        sheet: Sheet 설정 (xl_utils.SheetConfig)
    
    Example:
        >>> # xloto/xlcrawl 공통 사용
        >>> excel_config = CashopExcelConfig(
        ...     file_path="data.xlsx",
        ...     sheet=SheetConfig(
        ...         sheet_name="Purchase",
        ...         column_alias="PRODUCT_LIST"
        ...     )
        ... )
        >>> 
        >>> # xloto에서 사용
        >>> class XlOtoPolicy(BaseModel):
        ...     excel: CashopExcelConfig
        >>> 
        >>> # xlcrawl에서 사용
        >>> class XlCrawlPolicy(BaseModel):
        ...     excel: CashopExcelConfig
    """
    file_path: str = Field(
        ...,  # Required!
        description="Excel 파일 경로"
    )
    sheet: SheetConfig = Field(
        default_factory=SheetConfig,  # type: ignore
        description="Sheet 설정 (xl_utils.SheetConfig)"
    )


class CashopBasePolicy(BaseModel):
    """Cashop Base Pipeline 정책 (xloto, xlcrawl 공통 기반).
    
    Excel 기반 파이프라인 통합 정책.
    서브 모듈 정책은 SectionExtractor로 동적으로 추출됩니다.
    
    xloto와 xlcrawl에서 공통으로 사용하는 기본 Policy.
    각 파이프라인에서 name만 오버라이드하여 사용.
    
    ⚠️ Excel 파일 경로는 ExcelLoadPolicy.files에서 관리
    
    Attributes:
        name: Policy 이름 ("xloto" 또는 "xlcrawl")
        paths: 경로 정책 (CashopPathsPolicy)
        log: 파이프라인 로그 정책
    
    Example:
        >>> # xloto에서 사용
        >>> from cashop.core.policy import CashopBasePolicy
        >>> 
        >>> xloto_policy = CashopBasePolicy(
        ...     name="xloto",
        ...     paths=CashopPathsPolicy(),
        ...     log=LogPolicy()
        ... )
        >>> 
        >>> # xlcrawl에서 사용
        >>> xlcrawl_policy = CashopBasePolicy(
        ...     name="xlcrawl",
        ...     paths=CashopPathsPolicy(output_dir="output/crawl"),
        ...     log=LogPolicy()
        ... )
    
    YAML Example:
        >>> # xloto_config.yaml
        >>> xloto:
        ...   paths:
        ...     public_img_dir: "${public_dir}/01.IMAGE"
        ...   log: ...
        >>> 
        >>> # Excel 파일은 ExcelLoadPolicy.files에서 정의
        >>> excel:
        ...   files:
        ...     - file_path: "data.xlsx"
        ...       sheets:
        ...         - sheet_name: "Purchase"
        ...           column_alias: "PRODUCT_LIST"
    
    Note:
        ⚠️ 서브 모듈 정책 필드는 없음 (SectionExtractor가 동적 추출).
        ⚠️ ConfigLoader 섹션명과 Policy.name 필드가 일치해야 함.
        ⚠️ Excel 파일 경로는 ExcelLoadPolicy.files[0].file_path에서 가져옴.
    """
    name: str = Field(
        ...,  # Required! "xloto" or "xlcrawl"
        description="Pipeline 이름 (xloto/xlcrawl)"
    )
    
    # ===== Paths 설정 (공통) =====
    paths: CashopPathsPolicy = Field(
        default_factory=CashopPathsPolicy,  # type: ignore
        description="경로 정책 (CashopPathsPolicy)"
    )
    
    # ===== Log 설정 (공통) =====
    log: LogPolicy = Field(
        default_factory=LogPolicy,
        description="파이프라인 로그 정책"
    )
