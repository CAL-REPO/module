# -*- coding: utf-8 -*-
"""crawl_utils.adapter - Core crawling logic (Adapter layer)."""

from .crawl import Crawl
from .webdriver_manager import WebDriverManager

__all__ = [
    "Crawl",
    "WebDriverManager",
]
