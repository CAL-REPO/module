# -*- coding: utf-8 -*-
"""XLCRAWL Pipeline Policy - Logging + Paths configuration only.

책임:
1. XLCRAWL 파이프라인 로그 정책 관리
2. 크롤링 경로 정책 관리
3. 서브 모듈 정책은 SectionExtractor로 동적 추출 (Pass-through Pattern)

Note:
    ⚠️ CashopPathsPolicy, CashopExcelConfig는 cashop/core/policy.py에서 import
    ⚠️ xloto, xlcrawl 등 여러 파이프라인에서 공통으로 사용
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional

from logs_utils.core.policy import LogPolicy

# cashop 공통 Policy import
from cashop.core.policy import CashopPathsPolicy, CashopExcelConfig


class XlCrawlPolicy(BaseModel):
    """XLCRAWL Pipeline 정책 (Pass-through Pattern + Excel 설정).
    
    Excel + Crawl 파이프라인 통합 정책.
    서브 모듈 정책은 SectionExtractor로 동적으로 추출됩니다.
    
    서브 모듈 정책 관리 (SectionExtractor 사용):
    - sync_crawl: SyncCrawl config dict (SyncCrawl Adapter에서 처리)
    
    Attributes:
        name: Policy 이름 ("xlcrawl")
        excel: Excel 파일/시트 설정 (CashopExcelConfig)
        paths: 크롤링 경로 정책 (CashopPathsPolicy)
        log: XLCRAWL 파이프라인 로그 정책
    
    Example:
        >>> # xlcrawl_config.yaml
        >>> xlcrawl:
        ...   excel:
        ...     file_path: "data.xlsx"
        ...     sheet:
        ...       sheet_name: "Purchase"
        ...       column_alias: "PRODUCT_LIST"
        ...   paths:
        ...     output_dir: "output/crawl"
        ...   log: ...
    
    Note:
        ⚠️ SyncCrawl 서브 모듈 정책 필드는 없음 (SectionExtractor가 동적 추출).
        ⚠️ ConfigLoader 섹션명과 Policy.name 필드가 일치해야 함.
        ⚠️ CashopExcelConfig, CashopPathsPolicy는 cashop/core/policy.py에서 정의
    """
    name: str = "cashop_base"
    
    # ===== Excel 설정 (cashop 공통) =====
    excel: CashopExcelConfig = Field(
        ...,  # Required!
        description="Excel 파일/시트 설정 (CashopExcelConfig)"
    )
    
    # ===== Paths 설정 (cashop 공통) =====
    paths: CashopPathsPolicy = Field(
        default_factory=CashopPathsPolicy,  # type: ignore
        description="크롤링 경로 정책 (CashopPathsPolicy)"
    )
    
    log: LogPolicy = Field(
        default_factory=LogPolicy,
        description="XLCRAWL 통합 로그 정책"
    )
