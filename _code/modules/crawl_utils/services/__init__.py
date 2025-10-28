"""Service entrypoint for crawl_utils (compact, v1).

Expose only currently-implemented sync/async service classes. This
module avoids importing optional/removed components at package import
time to keep imports fast and predictable.
"""

from __future__ import annotations

# Core adapters
from .adapter import AsyncSeleniumAdapter, SyncSeleniumAdapter

# Navigator
from .navigator import SyncNavigator

# Extractors
from .extractor import SyncDOMExtractor, SyncJSExtractor, SyncExtractorFactory

# Fetchers
from .fetcher import AsyncHTTPFetcher, AsyncDummyFetcher, SyncHTTPFetcher

# Normalizers / items
from .item_normalizer import ItemNormalizer
from .items_normalizer import ItemsNormalizer
from .preset_policy_normalizer import PresetPolicyNormalizer

# Saver
from .item_saver import SyncItemSaver, AsyncItemSaver

__all__ = [
    "AsyncSeleniumAdapter",
    "SyncSeleniumAdapter",
    "SyncNavigator",
    "SyncDOMExtractor",
    "SyncJSExtractor",
    "SyncExtractorFactory",
    "AsyncHTTPFetcher",
    "AsyncDummyFetcher",
    "SyncHTTPFetcher",
    "ItemNormalizer",
    "ItemsNormalizer",
    "PresetPolicyNormalizer",
    "SyncItemSaver",
    "AsyncItemSaver",
]
