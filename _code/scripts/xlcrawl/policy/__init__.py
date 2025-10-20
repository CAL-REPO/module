# -*- coding: utf-8 -*-
"""XlCrawl Policy Module."""

from .policy import (
    # PostProcessor
    PostProcessorRule,
    PostProcessorPolicy,
    # XlCrawl
    XlCrawlFilterPolicy,
    XlCrawlPathsPolicy,
    PresetMappingRule,
    PresetMappingPolicy,
    XlCrawlPolicy,
)

__all__ = [
    # PostProcessor
    "PostProcessorRule",
    "PostProcessorPolicy",
    # XlCrawl
    "XlCrawlFilterPolicy",
    "XlCrawlPathsPolicy",
    "PresetMappingRule",
    "PresetMappingPolicy",
    "XlCrawlPolicy",
]
