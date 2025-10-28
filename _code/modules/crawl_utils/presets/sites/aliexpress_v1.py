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
            "strategy": "step",
            "max_scrolls": 5,
            "scroll_pause_sec": 0.5,  # ✅ 스크롤 후 충분한 대기
            "scroll_count": 10,
            "scroll_step_px": 600,
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
            "js_snippet": r"""
                (() => {
                const debug = { imageCandidates: 0, imageKept: 0, skuCandidates: 0, skuKept: 0, fromShadow: 0, fromDom: 0, fromBg: 0, fromIframe: 0 };

                const normalizeUrl = (url) => {
                    if (!url) return null;
                    // protocol-relative -> add https
                    url = url.startsWith("//") ? "https:" + url : url;
                    // root-relative -> make absolute against aliexpress
                    url = url.startsWith("/") ? "https://ko.aliexpress.com" + url : url;
                    // strip query/string for normalization
                    try { return url.split("?")[0]; } catch (e) { return url; }
                };

                const enhanceUrl = (url) => {
                    if (!url) return url;
                    return url
                    .replace(/_50x50\..*$/i, "")
                    .replace(/_100x100\..*$/i, "")
                    .replace(/_220x220\..*$/i, "")
                    .replace(/_640x640\..*$/i, "")
                    .replace(/_Q90\./i, ".")
                    .replace(/_Q\d+\./i, ".")
                    .replace(/\.webp$/i, ".webp");
                };

                const images = [];
                const seen = new Set();

                const pushImg = (url, source) => {
                    debug.imageCandidates++;
                    if (!url) return;
                    url = normalizeUrl(url);
                    if (!url) return;
                    url = enhanceUrl(url);
                    if (seen.has(url)) return;
                    seen.add(url);
                    images.push(url);
                    debug.imageKept++;
                    if (source === "shadow") debug.fromShadow++; else if (source === "dom") debug.fromDom++; else if (source === "bg") debug.fromBg++; else if (source === "iframe") debug.fromIframe++;
                };

                const productDesc = document.querySelector("#product-description");
                const outerHTML = productDesc ? productDesc.outerHTML : null;
                const text = productDesc ? productDesc.innerText : (document.querySelector('#product-description') ? document.querySelector('#product-description').innerText : '');

                // gather imgs within product description
                if (productDesc) {
                    // images in shadow root
                    try {
                        if (productDesc.shadowRoot) {
                            productDesc.shadowRoot.querySelectorAll('img').forEach(img => {
                                pushImg(img.getAttribute('src') || img.getAttribute('data-src') || img.src, 'shadow');
                            });
                        }
                    } catch (e) { /* ignore cross-origin or missing shadowRoot */ }

                    // standard img elements
                    productDesc.querySelectorAll('img').forEach(img => {
                        pushImg(img.getAttribute('src') || img.getAttribute('data-src') || img.src, 'dom');
                    });

                    // inline background-image styles
                    productDesc.querySelectorAll('*').forEach(el => {
                        const s = el.getAttribute('style');
                        if (!s) return;
                        const m = s.match(/url\(([^)]+)\)/);
                        if (m && m[1]) {
                            const u = m[1].replace(/['\"]+/g, '');
                            pushImg(u, 'bg');
                        }
                    });

                    // try to read iframes inside product description (best-effort)
                    productDesc.querySelectorAll('iframe').forEach(fr => {
                        try {
                            const doc = fr.contentDocument || (fr.contentWindow && fr.contentWindow.document);
                            if (!doc) return;
                            doc.querySelectorAll('img').forEach(img => {
                                pushImg(img.getAttribute('src') || img.getAttribute('data-src') || img.src, 'iframe');
                            });
                            doc.querySelectorAll('*').forEach(el => {
                                const ss = el.getAttribute && el.getAttribute('style');
                                if (!ss) return;
                                const mm = ss.match(/url\(([^)]+)\)/);
                                if (mm && mm[1]) {
                                    const uu = mm[1].replace(/['\"]+/g, '');
                                    pushImg(uu, 'iframe');
                                }
                            });
                        } catch (e) { /* cross-origin iframe, ignore */ }
                    });
                } else {
                    // fallback: search whole document
                    document.querySelectorAll('img').forEach(img => {
                        pushImg(img.getAttribute('src') || img.getAttribute('data-src') || img.src, 'dom');
                    });
                }

                // SKU extraction (best-effort)
                function extractSkuOptions() {
                    const skuOptions = [];
                    const seen2 = new Set();
                    const roots = ['.sku--wrap--xgoW06M', "[class*='sku-item--wrap']", '[data-sku-col]', '.sku-property', '.sku-item-list', '.sku-attr-list'];
                    let skuRoot = null;
                    for (const s of roots) { const el = document.querySelector(s); if (el) { skuRoot = el; break; } }
                    if (!skuRoot) return skuOptions;

                    const candidates = skuRoot.querySelectorAll('img, [data-sku-col]');
                    candidates.forEach(item => {
                        debug.skuCandidates++;
                        const img = (item.tagName && item.tagName.toLowerCase() === 'img') ? item : item.querySelector && item.querySelector('img');
                        if (!img) return;
                        let url = normalizeUrl(img.getAttribute('src') || img.getAttribute('data-src') || img.src);
                        if (!url) return;
                        url = enhanceUrl(url);
                        let optionName = (img.getAttribute('alt') || img.getAttribute('title') || (item.getAttribute && item.getAttribute('title')) || item.textContent || '').trim();
                        const key = url + '|' + optionName;
                        if (seen2.has(key)) return; seen2.add(key);
                        skuOptions.push({ url, option_name: optionName, sanitized_name: optionName.replace(/\s+/g, '').replace(/[^a-zA-Z0-9가-힣]/g, '') });
                        debug.skuKept++;
                    });

                    return skuOptions;
                }

                return {
                    outerHTML: outerHTML,
                    text: text,
                    images: images,
                    imageDebug: debug,
                    skuOptions: extractSkuOptions()
                };
                })();
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
