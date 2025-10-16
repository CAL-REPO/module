# -*- coding: utf-8 -*-
# crawl_utils/services/__init__.py
# Crawl Utils Services - 크롤링 서비스 컴포넌트

"""
Crawl Utils Services
====================

크롤링 파이프라인의 핵심 서비스 컴포넌트:

**Async/Sync 통합 Services**:
- AsyncSeleniumAdapter, SyncSeleniumAdapter: Selenium WebDriver Adapter
- SeleniumNavigator, SyncNavigator: 페이지 탐색 및 스크롤 처리
- ExtractorFactory, DOMExtractor, JSExtractor, APIExtractor: 데이터 추출 (Async)
- HTTPFetcher, SyncHTTPFetcher: HTTP 리소스 페칭
- FileSaver, SyncFileSaver: 정규화된 아이템 파일 저장
  

**Sync Services**:
- DataNormalizer: 추출 데이터 정규화
- SmartNormalizer: 타입 추론 정규화
  
Note: 고수준 오케스트레이션(CrawlPipeline/SyncRunner/SiteCrawler)은 현재 패키지에서 제공하지 않습니다.
"""

from __future__ import annotations

# Async/Sync Adapters
from .adapter import AsyncSeleniumAdapter, SyncSeleniumAdapter, SeleniumAdapter

# Navigator (Async/Sync)
from .navigator import SeleniumNavigator, SyncNavigator, Navigator

# Extractors (Async)
from .extractor import (
    ExtractorFactory,
    DOMExtractor,
    JSExtractor,
    APIExtractor,
)

# Fetchers (Async/Sync)
from .fetcher import HTTPFetcher, SyncHTTPFetcher, DummyFetcher

# Savers (Async/Sync)
from .saver import FileSaver, SyncFileSaver

# Sync Services
from .normalizer import DataNormalizer
from .smart_normalizer import SmartNormalizer


__all__ = [
    # Adapters (Async/Sync)
    "AsyncSeleniumAdapter",
    "SyncSeleniumAdapter",
    "SeleniumAdapter",  # Alias for AsyncSeleniumAdapter
    
    # Navigator (Async/Sync)
    "SeleniumNavigator",
    "SyncNavigator",
    "Navigator",  # Alias for SeleniumNavigator
    
    # Extractors (Async)
    "ExtractorFactory",
    "DOMExtractor",
    "JSExtractor",
    "APIExtractor",
    
    # Fetchers (Async/Sync)
    "HTTPFetcher",
    "SyncHTTPFetcher",
    "DummyFetcher",
    
    # Savers (Async/Sync)
    "FileSaver",
    "SyncFileSaver",
    
    # Sync Services
    "DataNormalizer",
    "SmartNormalizer",
]



