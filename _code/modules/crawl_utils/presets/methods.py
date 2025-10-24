# -*- coding: utf-8 -*-
"""crawl_utils.presets.sites.methods
======================================

URL 패턴 → method 매핑

이 모듈은 URL 경로를 분석하여 method를 추출합니다.
"""

# URL 패턴 → method 매핑
METHOD_PATTERNS = {
    "detail": [
        "/item/",
        "/i/",
        ".htm",
        ".html",
        "/product/",
        "/detail/",
        "/goods/",
        "/offer/",
        "/ssr/",  # AliExpress SSR (Server-Side Rendering) 상품 페이지
    ],
    
    "search": [
        "/category/",
        "/search",
        "/wholesale/",
        "/w/wholesale",
        "/s?",
        "/search?",
        "/list?",
    ],
}


__all__ = ["METHOD_PATTERNS"]

