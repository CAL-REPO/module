# -*- coding: utf-8 -*-
"""XlCrawl - Excel + Crawl Pipeline Integration.

XLOTO 패턴 적용:
- policy/: Policy 정의
- services/: 재사용 가능한 Service (UrlAnalyzer, PresetResolver, etc.)
- adapter/: Standalone Adapter (run에서 config 받음)
- entry_point/: ConfigLoader 기반 EntryPoint

Usage:
    >>> from xlcrawl.adapter import XlCrawl
    >>> adapter = XlCrawl(cfg_like="configs/xlcrawl.yaml")
    >>> result = adapter.run(
    ...     config_path="configs/loader/config_loader_xlcrawl.yaml",
    ...     url_list=["https://..."]
    ... )
"""

__version__ = "1.0.0"
__all__ = []
