# -*- coding: utf-8 -*-
"""cashop Core - 공통 Policy 정의.

여러 파이프라인(xloto, xlcrawl 등)에서 재사용되는 Policy 클래스를 제공합니다.

Classes:
    - CashopPathsPolicy: 경로 정책 (xloto, xlcrawl 공통)
    - CashopExcelConfig: Excel 설정 (xloto, xlcrawl 공통)
    - CashopBasePolicy: 기본 파이프라인 정책 (xloto, xlcrawl 공통 기반)
"""

from .policy import CashopPathsPolicy, CashopExcelConfig, CashopBasePolicy

__all__ = [
    "CashopPathsPolicy",
    "CashopExcelConfig",
    "CashopBasePolicy",
]
