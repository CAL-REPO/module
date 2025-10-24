# -*- coding: utf-8 -*-
"""crawl_utils.presets.sites.domains
======================================

도메인 → site, region 매핑

이 모듈은 URL 도메인을 분석하여 site와 region을 추출합니다.
region은 WebDriver 선택에 사용됩니다.
"""

# 도메인 → site, region 매핑
DOMAIN_MAPPING = {
    "aliexpress": {
        "domains": [
            "aliexpress.com",
            "aliexpress.ru",
            "aliexpress.us",
            "ae01.alicdn.com",
            "aliexpress.com.br",
        ],
        "region": "global",  # WebDriver region
        "description": "AliExpress - 글로벌 B2C 플랫폼"
    },
    
    "taobao": {
        "domains": [
            "taobao.com",
            "world.taobao.com",
            "item.taobao.com",
            "taobao.world.taobao.com",
        ],
        "region": "china",  # WebDriver region
        "description": "Taobao - 중국 C2C 플랫폼"
    },
    
    "tmall": {
        "domains": [
            "tmall.com",
            "detail.tmall.com",
            "tmall.hk",
            "chaoshi.tmall.com",
        ],
        "region": "china",
        "description": "Tmall - 중국 B2C 플랫폼"
    },
    
    "1688": {
        "domains": [
            "1688.com",
            "detail.1688.com",
            "s.1688.com",
            "page.1688.com",
        ],
        "region": "china",
        "description": "1688 - 중국 B2B 플랫폼"
    },
}


__all__ = ["DOMAIN_MAPPING"]

