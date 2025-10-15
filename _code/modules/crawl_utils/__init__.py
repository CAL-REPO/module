
# -*- coding: utf-8 -*-
# crawl_utils/__init__.py
# Web crawling, navigation, extraction, and normalization utilities.

# WebDriver Factory
from crawl_utils.provider import create_webdriver

# WebDriver Base & Implementations
from crawl_utils.provider import BaseWebDriver, FirefoxWebDriver

# WebDriver Policies
from crawl_utils.core.policy import (
    WebDriverPolicy,
    FirefoxPolicy,
    ChromePolicy,
    ProviderType,
)

# Crawl Policies
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

# Pipeline and fetchers
from crawl_utils.services.crawl import CrawlPipeline
from crawl_utils.services.fetcher import HTTPFetcher, DummyFetcher

# Storage and normalization
from crawl_utils.services.saver import FileSaver
from crawl_utils.services.normalizer import DataNormalizer
from crawl_utils.services.smart_normalizer import SmartNormalizer

# Sync runner
from crawl_utils.services.sync_runner import SyncCrawlRunner, run_sync_crawl

# Entry Points
from crawl_utils.services.entry_points import DetailEntryPoint

# Site Crawler Service (NEW)
from crawl_utils.services.site_crawler import SiteCrawler

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
    # WebDriver Factory
    "create_webdriver",
    
    # WebDriver Base & Implementations
    "BaseWebDriver", "FirefoxWebDriver",
    
    # WebDriver Policies
    "WebDriverPolicy", "FirefoxPolicy", "ChromePolicy", "ProviderType",
    
    # Crawl Policies
    "CrawlPolicy", "NavigationPolicy", "ScrollPolicy",
    "ExtractorPolicy", "WaitPolicy", "NormalizationPolicy",
    "NormalizationRule", "StoragePolicy", "StorageTargetPolicy",
    "HttpSessionPolicy", "ExecutionMode",

    # Pipeline and fetchers
    "CrawlPipeline", "HTTPFetcher", "DummyFetcher",

    # Storage and normalization
    "FileSaver", "DataNormalizer", "SmartNormalizer",
    
    # Sync runner
    "SyncCrawlRunner", "run_sync_crawl",

    # Entry Points
    "DetailEntryPoint",

    # Site Crawler Service
    "SiteCrawler",
    
    # Filter Utils
    "manual_filter_urls", "filter_by_price", "filter_by_rating", "filter_by_custom",

    # Models
    "NormalizedItem", "SaveSummary", "SavedArtifact",
]

