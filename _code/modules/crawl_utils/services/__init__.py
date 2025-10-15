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
- CrawlPipeline: 전체 크롤링 워크플로우 조율 (Async)

**Sync Services**:
- DataNormalizer: 추출 데이터 정규화
- SmartNormalizer: 타입 추론 정규화
- SiteCrawler: 사이트별 크롤링 실행

**Hybrid Services**:
- SyncCrawlRunner: 비동기 파이프라인의 동기 래퍼
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

# Pipeline (Async)
from .crawl import CrawlPipeline

# Sync Services
from .normalizer import DataNormalizer
from .smart_normalizer import SmartNormalizer
from .site_crawler import SiteCrawler
from .sync_runner import SyncCrawlRunner


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
    
    # Pipeline (Async)
    "CrawlPipeline",
    
    # Sync Services
    "DataNormalizer",
    "SmartNormalizer",
    "SiteCrawler",
    "SyncCrawlRunner",
]



