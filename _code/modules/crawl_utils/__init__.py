
"""crawl_utils public API (v1).

This module exposes the main adapter and policy classes for convenience.
This is intentionally concise and direct — no defensive import shims.
"""

from __future__ import annotations

from .adapter import SyncCrawl, WebDriverManager
from .core.policy import SyncCrawlPolicy
from .services import SyncItemSaver, SyncHTTPFetcher

__all__ = [
    "SyncCrawl",
    "WebDriverManager",
    "SyncCrawlPolicy",
    "SyncItemSaver",
    "SyncHTTPFetcher",
]
