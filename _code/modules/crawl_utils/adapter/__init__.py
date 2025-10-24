# -*- coding: utf-8 -*-
"""crawl_utils.adapter - Core crawling logic (Adapter layer)."""

from .sync_crawl import SyncCrawl
from .webdriver_manager import WebDriverManager

__all__ = [
    "SyncCrawl",
    "WebDriverManager",
]
