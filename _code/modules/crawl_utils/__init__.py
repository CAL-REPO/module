
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
    SyncCrawlPolicy,
    ExtractorPolicy,
    WaitPolicy,
    NavigationPolicy,
    ScrollPolicy,
    ExecutionPolicy,
    RetryPolicy,
    ItemSaveResult,
    ItemSaveSummary,
    ItemPostProcessPolicy,
)

# Fetchers
from crawl_utils.services.fetcher import AsyncHTTPFetcher, AsyncDummyFetcher, SyncHTTPFetcher

# PreProcessor
from crawl_utils.services.pre_processor import PreProcessor

# Pipeline
from crawl_utils.services.pipeline import SyncPipeline

# PostProcessor (v5.0)
from crawl_utils.services.item_saver import (
    AsyncItemSaver,
    SyncItemSaver,
)

# Adapter (OTO pattern)
from crawl_utils.adapter import SyncCrawl

# Note: 고수준 오케스트레이션(CrawlPipeline/SyncRunner/EntryPoints/SiteCrawler)
# 은 현재 패키지에서 제공하지 않습니다.

# Models
from crawl_utils.core.policy import ItemList

__all__ = [
    # WebDriver Manager (Recommended)
    "WebDriverManager",
    
    # WebDriver Provider (Pure logic)
    "FirefoxWebDriver",
    
    # WebDriver Policies
    "WebDriverManagerPolicy", "FirefoxConfig", "ChromeConfig", "ProviderType",
    
    # Crawl Policies
    "CrawlPolicy", "SyncCrawlPolicy", "NavigationPolicy", "ScrollPolicy",
    "ExtractorPolicy", "WaitPolicy", 
    "ExecutionPolicy", "RetryPolicy",
    "ItemSaveResult", "ItemSaveSummary",
    "ItemPostProcessPolicy",

    # Fetchers
    "AsyncHTTPFetcher", "AsyncDummyFetcher", "SyncHTTPFetcher",
    
    # PreProcessor
    "PreProcessor",
    
    # Pipeline
    "SyncPipeline",
    
    # PostProcessor (v5.0)
    # Services - ItemSaver (PostProcessor)
    "AsyncItemSaver",
    "SyncItemSaver",
    
    # Adapter (OTO pattern)
    "SyncCrawl",
    
    # (고수준 오케스트레이션은 미노출)

    # Models
    "ItemList",
]
