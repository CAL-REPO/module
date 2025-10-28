# -*- coding: utf-8 -*-
"""crawl_utils.presets.sites
==============================

Site별 크롤링 정책 모듈 (v2.0 - Python Preset Functions Only)
"""

from .aliexpress import (
    get_aliexpress_detail_preset,
    get_aliexpress_search_preset
)

from .tb_tm_1688 import (
    get_taobao_detail_preset,
    get_tmall_detail_preset,
    get_1688_detail_preset
)


__all__ = [
    # v2.0 - Function-based Presets
    "get_aliexpress_detail_preset",
    "get_aliexpress_search_preset",
    "get_taobao_detail_preset",
    "get_tmall_detail_preset",
    "get_1688_detail_preset",
]


