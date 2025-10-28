# -*- coding: utf-8 -*-
"""cashop - CAShop 구매대행 통합 모듈.

여러 파이프라인(xloto, xlcrawl 등)에서 공통으로 사용되는 정책과 유틸리티를 제공합니다.

Modules:
    - core.policy: 공통 Policy (CashopPathsPolicy, CashopExcelConfig)
    - utils: 공통 Service (CasExtractor, ExcelUpdater)
    - xloto: Excel + OTO 파이프라인
    - xlcrawl: Excel + Crawl 파이프라인
"""

__all__ = []
