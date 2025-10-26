# -*- coding: utf-8 -*-
"""
Aliexpress 크롤링 프리셋
"""

from pathlib import Path
from typing import Dict, Any


def get_aliexpress_detail_preset() -> Dict[str, Any]:
    """Aliexpress 상품 상세 페이지 프리셋
    
    Returns:
        Preset dict (SyncCrawlPolicy 호환)
        
    Features:
        - 무한 스크롤 (최대 5회)
        - 상품 이미지 자동 다운로드
        - 상품명 텍스트 저장
        - SKU 옵션 추출
    """
    return {
        # Scroll 정책
        "scroll": {
            "strategy": "infinite",
            "max_scrolls": 15,
            "scroll_pause_sec": 3.0  # ✅ 스크롤 후 충분한 대기
        },
        
        # Wait 정책
        "wait": {
            "hook": "css",
            "selector": "#product-description",  # ✅ #product-description 로드 대기
            "timeout_sec": 20.0,  # ✅ 충분한 대기 시간
            "condition": "presence"
        },
        
        # Extractor 정책
        "extractor": {
            "type": "js",
            "js_snippet": """
                // AliExpress 상품 상세 페이지 데이터 추출 (검증된 selector 사용)
                
                const extractImages = (() => {
                    const images = [];
                    const seen = new Set();

                    // 이미지 URL 정규화 함수
                    const normalizeUrl = (url) => {
                        if (!url) return null;
                        if (url.startsWith("//")) url = "https:" + url;
                        if (url.startsWith("/")) url = "https://ko.aliexpress.com" + url;
                        if (!url.includes("alicdn.com")) return null; // alicdn 도메인만 수집
                        return url.split("?")[0];
                    };

                    // 1️⃣ Shadow DOM 내부 (#product-description)
                    const productDesc = document.querySelector("#product-description");
                    if (productDesc && productDesc.shadowRoot) {
                        const shadowImgs = productDesc.shadowRoot.querySelectorAll("img");
                        shadowImgs.forEach((img) => {
                            const url = normalizeUrl(img.getAttribute("src") || img.getAttribute("data-src"));
                            if (url && !seen.has(url)) {
                                seen.add(url);
                                images.push({
                                    url,
                                    type: "detail",
                                    source: "shadow"
                                });
                            }
                        });
                    }

                    // 2️⃣ 일반 DOM (대체 구조 포함)
                    const selectors = [
                        "#product-description img",
                        ".product-description img",
                        ".product-detail img",
                        "div[data-spm-anchor-id] img"
                    ];
                    selectors.forEach((selector) => {
                        document.querySelectorAll(selector).forEach((img) => {
                            const url = normalizeUrl(img.getAttribute("src") || img.getAttribute("data-src"));
                            if (url && !seen.has(url)) {
                                seen.add(url);
                                images.push({
                                    url,
                                    type: "detail",
                                    source: "dom"
                                });
                            }
                        });
                    });

                    // 3️⃣ 이미지 품질 업그레이드 (썸네일 -> 원본)
                    const enhanceUrl = (url) => {
                        if (!url) return url;
                        return url
                            .replace(/_50x50\..*$/i, "")
                            .replace(/_100x100\..*$/i, "")
                            .replace(/_220x220\..*$/i, "")
                            .replace(/_640x640\..*$/i, "")
                            .replace(/_Q90\./i, ".")
                            .replace(/_Q\d+\./i, ".")
                            .replace(/_\.webp$/i, ".jpg");
                    };

                    images.forEach((img) => (img.url = enhanceUrl(img.url)));

                    // 4️⃣ URL만 배열로 리턴
                    return images.map((i) => i.url);
                })();
                
                const extractSkuOptions = (() => {
                    const skuOptions = [];
                    const seen = new Set();

                    // URL 정규화
                    const normalizeUrl = (url) => {
                        if (!url) return null;
                        if (url.startsWith("//")) url = "https:" + url;
                        if (url.startsWith("/")) url = "https://ko.aliexpress.com" + url;
                        if (!url.includes("alicdn.com")) return null; // alicdn 이미지만
                        return url.split("?")[0];
                    };

                    // 1️⃣ SKU 컨테이너 탐색
                    const possibleSkuRoots = [
                        ".sku--wrap--xgoW06M",
                        "[class*='sku-item--wrap']",
                        "[data-sku-col]",
                        ".sku-property",
                        ".sku-item-list",
                        ".sku-attr-list",
                    ];

                    let skuRoot = null;
                    for (const selector of possibleSkuRoots) {
                        const el = document.querySelector(selector);
                        if (el) {
                            skuRoot = el.closest("div");
                            break;
                        }
                    }

                    if (!skuRoot) {
                        console.warn("SKU container not found");
                        return [];
                    }

                    // 2️⃣ SKU 항목 추출
                    const skuItems = skuRoot.querySelectorAll(
                        "[class*='sku-item--image'], [data-sku-col], [class*='sku-property'] img, img[role='option']"
                    );

                    skuItems.forEach((item) => {
                        const img = item.tagName.toLowerCase() === "img" ? item : item.querySelector("img");
                        if (!img) return;

                        // 이미지 URL
                        let url = normalizeUrl(img.getAttribute("src") || img.getAttribute("data-src"));
                        if (!url) return;

                        // 옵션명
                        let optionName =
                            img.getAttribute("alt") ||
                            img.getAttribute("title") ||
                            item.getAttribute("title") ||
                            item.textContent ||
                            "";

                        optionName = optionName.trim();

                        // SKU 컬럼 정보
                        const skuCol = item.getAttribute("data-sku-col") || "";

                        // 중복 방지
                        const key = url + "|" + optionName;
                        if (seen.has(key)) return;
                        seen.add(key);

                        skuOptions.push({
                            url,
                            option_name: optionName,
                            sanitized_name: optionName.replace(/\s+/g, "").replace(/[^a-zA-Z0-9가-힣]/g, ""),
                            sku_col: skuCol,
                        });
                    });

                    // 3️⃣ 이미지 고화질 정규화
                    const enhanceUrl = (url) => {
                        if (!url) return url;
                        return url
                            .replace(/_50x50\..*$/i, "")
                            .replace(/_100x100\..*$/i, "")
                            .replace(/_220x220\..*$/i, "")
                            .replace(/_640x640\..*$/i, "")
                            .replace(/_Q90\./i, ".")
                            .replace(/_Q\d+\./i, ".")
                            .replace(/_\.webp$/i, ".jpg");
                    };

                    skuOptions.forEach((opt) => (opt.url = enhanceUrl(opt.url)));

                    // 4️⃣ 결과 리턴
                    return skuOptions;
                })();
                
                // 최종 결과 반환
                const result = extractImages();
                return {
                    images: result.urls,
                    imageDebug: result.debug,
                    skuOptions: extractSkuOptions()
                };
            """
        },
        
        # Save 규칙 (ItemPostProcessPolicy)
        "save": [
            # 규칙 1: 상품 이미지 (배열 자동 explode)
            {
                "kind": "image",
                "source": "images",  # KeyPath: images (배열, 각 요소는 URL 문자열)
                "directory": None,  # ✅ None = downloads() 사용 (사용자가 override로 주입 권장)
                "name": {
                    "as_type": "file",
                    "prefix": "DETAILED",
                    "name": "TEST",
                    "tail_mode": "counter",  # 001, 002, 003, ...
                    "counter_width": 2,
                    "delimiter": "_",
                    "extension": "",
                    "auto_expand": True,
                    "sanitize": True,
                    "case": "keep",
                    "ensure_unique": False
                },
                "ops": {
                    "as_type": "file",
                    "exist": {
                        "must_exist": False,
                        "create_if_missing": True,
                        "overwrite": True
                    },
                    "ext": {
                        "require_ext": True,
                        "default_ext": "",
                        "allowed_exts": None
                    }
                }
            },
            
            # 규칙 2: SKU 옵션 이미지 (Option Images)
            {
                "kind": "image",
                "source": "skuOptions__url",  # KeyPath: skuOptions[*].url (배열 내 객체의 url 필드)
                "directory": None,  # ✅ None = downloads() 사용 (사용자가 override로 주입 권장)
                "name": {
                    "as_type": "file",
                    "prefix": "OPTION",
                    "name": "TEST",
                    "tail_mode": "counter",  # 001, 002, 003, ...
                    "counter_width": 2,
                    "delimiter": "_",
                    "extension": "",
                    "auto_expand": True,
                    "sanitize": True,
                    "case": "keep",
                    "ensure_unique": False
                },
                "ops": {
                    "as_type": "file",
                    "exist": {
                        "must_exist": False,
                        "create_if_missing": True,
                        "overwrite": True
                    },
                    "ext": {
                        "require_ext": True,
                        "default_ext": "",
                        "allowed_exts": None
                    }
                }
            }
        ]
    }


def get_aliexpress_search_preset() -> Dict[str, Any]:
    """Aliexpress 검색 페이지 프리셋
    
    Returns:
        Preset dict (SyncCrawlPolicy 호환)
        
    Features:
        - 무한 스크롤 (검색 결과 로드)
        - 상품 썸네일 이미지 수집
        - 상품 제목 수집
    """
    return {
        "scroll": {
            "strategy": "infinite",
            "max_scrolls": 10,
            "scroll_pause_sec": 1.5
        },
        
        "wait": {
            "hook": "css",
            "selector": ".search-item",
            "timeout_sec": 10.0,
            "condition": "presence"
        },
        
        "extractor": {
            "type": "js",
            "js_snippet": """
                return Array.from(document.querySelectorAll('.search-item')).map(item => ({
                    title: item.querySelector('.item-title')?.textContent?.trim() || '',
                    thumbnail: item.querySelector('.item-image img')?.src || '',
                    price: item.querySelector('.item-price')?.textContent?.trim() || '',
                    url: item.querySelector('a')?.href || ''
                }));
            """
        },
        
        "save": [
            # 각 검색 결과의 썸네일 이미지
            {
                "kind": "image",
                "source": "thumbnail",  # KeyPath: thumbnail (각 record)
                "directory": None,  # ✅ None = downloads() 사용 (사용자가 override로 주입 권장)
                "name": {
                    "as_type": "file",
                    "prefix": "thumbnail",
                    "tail_mode": "counter",
                    "counter_width": 4,
                    "delimiter": "_",
                    "extension": ".jpg",
                    "date_format": "%Y-%m-%d",
                    "auto_expand": True,
                    "sanitize": True,
                    "case": "keep",
                    "ensure_unique": True
                },
                "ops": {
                    "as_type": "file",
                    "exist": {
                        "must_exist": False,
                        "create_if_missing": True,
                        "overwrite": True
                    },
                    "ext": {
                        "require_ext": False,
                        "default_ext": ".jpg",
                        "allowed_exts": None
                    }
                }
            }
        ]
    }


__all__ = [
    "get_aliexpress_detail_preset",
    "get_aliexpress_search_preset"
]
