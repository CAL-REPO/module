
# -*- coding: utf-8 -*-
# crawl_utils/__init__.py
# Web crawling, navigation, extraction, and normalization utilities.

# WebDriver Manager (ImageLoad pattern)
from crawl_utils.adapter import WebDriverManager

# WebDriver Provider (Pure logic)
from crawl_utils.provider import FirefoxWebDriver

# WebDriver Policies
from crawl_utils.provider.policy import (
    WebDriverManagerPolicy,
    FirefoxConfig,
    ChromeConfig,
    ProviderType,
)

# Core Policies
from crawl_utils.core.policy import (
    CrawlPolicy,
    NavigationPolicy,
    ScrollPolicy,
    ExtractorPolicy,
    WaitPolicy,
    NormalizationPolicy,
    NormalizationRule,
    StoragePolicy,
    StorageTargetPolicy,
    HttpSessionPolicy,
    ExecutionMode,
)

# Fetchers
from crawl_utils.services.fetcher import AsyncHTTPFetcher, AsyncDummyFetcher, SyncHTTPFetcher

# Storage and normalization
from crawl_utils.services.saver import AsyncFileSaver, SyncFileSaver
from crawl_utils.services.normalizer import DataNormalizer
from crawl_utils.services.smart_normalizer import SmartNormalizer

# Adapter & EntryPoint (Two-Policy pattern)
from crawl_utils.adapter import SyncCrawl
from crawl_utils.entry_point import Crawler

# Note: 고수준 오케스트레이션(CrawlPipeline/SyncRunner/EntryPoints/SiteCrawler)
# 은 현재 패키지에서 제공하지 않습니다.

# Filter Utils (NEW)
from crawl_utils.utils.filter_utils import (
    manual_filter_urls,
    filter_by_price,
    filter_by_rating,
    filter_by_custom,
)

# Models
from crawl_utils.core.models import NormalizedItem, SaveSummary, SavedArtifact

__all__ = [
    # WebDriver Manager (Recommended)
    "WebDriverManager",
    
    # WebDriver Provider (Pure logic)
    "FirefoxWebDriver",
    
    # WebDriver Policies
    "WebDriverManagerPolicy", "FirefoxConfig", "ChromeConfig", "ProviderType",
    
    # Crawl Policies
    "CrawlPolicy", "NavigationPolicy", "ScrollPolicy",
    "ExtractorPolicy", "WaitPolicy", "NormalizationPolicy",
    "NormalizationRule", "StoragePolicy", "StorageTargetPolicy",
    "HttpSessionPolicy", "ExecutionMode",

    # Fetchers
    "AsyncHTTPFetcher", "AsyncDummyFetcher", "SyncHTTPFetcher",

    # Storage and normalization
    "AsyncFileSaver", "SyncFileSaver", "DataNormalizer", "SmartNormalizer",
    
    # Adapter & EntryPoint (Two-Policy pattern)
    "SyncCrawl", "Crawler",
    
    # (고수준 오케스트레이션은 미노출)
    
    # Filter Utils
    "manual_filter_urls", "filter_by_price", "filter_by_rating", "filter_by_custom",

    # Models
    "NormalizedItem", "SaveSummary", "SavedArtifact",
]
