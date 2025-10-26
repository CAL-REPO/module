# -*- coding: utf-8 -*-
"""crawl_utils.presets.sites
==============================

Site별 크롤링 정책 모듈 (v2.0 - Python Preset Functions Only)
"""

from .aliexpress import (
    get_aliexpress_detail_preset,
    get_aliexpress_search_preset
)


__all__ = [
    # v2.0 - Function-based Presets
    "get_aliexpress_detail_preset",
    "get_aliexpress_search_preset",
]


