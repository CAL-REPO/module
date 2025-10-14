
# -*- coding: utf-8 -*-
# crawl_utils/__init__.py
# Web crawling, navigation, extraction, and normalization utilities.

# Policies
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
)

# Pipeline and fetchers
from crawl_utils.services.pipeline import CrawlPipeline
from crawl_utils.services.fetcher import HTTPFetcher, DummyFetcher

# Storage and normalization
from crawl_utils.services.saver import StorageDispatcher
from crawl_utils.services.normalizer import DataNormalizer

# Models
from crawl_utils.core.models import NormalizedItem, SaveSummary, SavedArtifact

__all__ = [
    # Policies
    "CrawlPolicy", "NavigationPolicy", "ScrollPolicy",
    "ExtractorPolicy", "WaitPolicy", "NormalizationPolicy",
    "NormalizationRule", "StoragePolicy", "StorageTargetPolicy",
    "HttpSessionPolicy",

    # Pipeline and fetchers
    "CrawlPipeline", "HTTPFetcher", "DummyFetcher",

    # Storage and normalization
    "StorageDispatcher", "DataNormalizer",

    # Models
    "NormalizedItem", "SaveSummary", "SavedArtifact",
]

