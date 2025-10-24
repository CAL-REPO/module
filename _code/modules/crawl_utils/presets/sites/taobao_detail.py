# -*- coding: utf-8 -*-
"""crawl_utils.presets.taobao_detail
======================================

Taobao Product Detail 크롤링 정책

Site: Taobao
Method: Product Detail (상품 상세)

역할: sync_crawl.yaml 기본값을 override
포함: Site별 차별화가 필요한 설정만 정의
제외: 공통 설정(log, execution, http_session 등)
"""

TAOBAO_DETAIL_POLICY = {
    # Site/Method 식별
    "site": "taobao",
    "method": "detail",
    
    # ============================================================================
    # Site-specific 설정만 포함
    # ============================================================================
    
    # Scroll 설정 (기본값 사용 - 명시적 override 불필요)
    "scroll": {
        "strategy": "infinite",
        "max_scrolls": 10,
        "scroll_pause_sec": 1.0
    },
    
    # Wait 설정 (Taobao 특정 selector)
    "wait": {
        "hook": "css",
        "selector": ".tb-gallery, .tb-booth",
        "timeout_sec": 20.0,  # 기본값(10.0)보다 길게
        "condition": "visibility"
    },
    
    # Extractor 설정 (Taobao 전용 JS snippet)
    "extractor": {
        "type": "js",
        "js_snippet": """
            // Taobao 상품 상세 페이지 데이터 추출
            const extractImages = () => {
                const images = [];
                const selectors = [
                    '.tb-gallery img',
                    '.tb-thumb img',
                    'img[class*="tb-"]',
                    'img[class*="pic"]'
                ];
                
                selectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach((img) => {
                        let url = img.getAttribute('data-src') || img.getAttribute('src') || '';
                        if (url.startsWith('//')) url = 'https:' + url;
                        if (/^https?:\\/\\//i.test(url) && !images.includes(url)) {
                            images.push(url);
                        }
                    });
                });
                
                return images;
            };
            
            const extractTitle = () => {
                const selectors = [
                    '.tb-main-title',
                    'h1.tb-title',
                    '[class*="item-title"]',
                    'h1'
                ];
                
                for (const selector of selectors) {
                    const el = document.querySelector(selector);
                    if (el && el.innerText.trim()) {
                        return el.innerText.trim();
                    }
                }
                return '';
            };
            
            const extractPrice = () => {
                const selectors = [
                    '.tb-rmb-num',
                    '[class*="price"]',
                    '[class*="Price"]'
                ];
                
                for (const selector of selectors) {
                    const el = document.querySelector(selector);
                    if (el && el.innerText.trim()) {
                        return el.innerText.trim();
                    }
                }
                return '';
            };
            
            return {
                images: extractImages(),
                title: extractTitle(),
                price: extractPrice(),
                category: document.querySelector('.crumb a:last-child')?.innerText?.trim() || 'uncategorized',
                shop: document.querySelector('.tb-shop-name')?.innerText?.trim() || ''
            };
        """
    },
    
    # PostProcessor 설정 (Taobao 전용 경로 + prefix)
    "post_processor": {
        "target_dir": "{{output_dir}}/crawl/taobao",
        "use_smart_normalizer": True,
        "rules": [
            {
                "kind": "image",
                "source": "images",
                "allow_empty": False,
                "dynamic_subdir": "{{cas_no}}/images",
                "fso_name_policy": {
                    "prefix": "TB",  # Taobao용 prefix
                    "tail_mode": "counter",
                    "counter_width": 3,
                    "extension": "jpg",
                    "sanitize": True,
                    "ensure_unique": True
                },
                "fso_ops_policy": {
                    "as_type": "file",
                    "exist": {
                        "must_exist": False,
                        "create_if_missing": True,
                        "overwrite": False
                    }
                }
            },
            {
                "kind": "text",
                "source": "title",
                "allow_empty": False,
                "dynamic_subdir": "{{cas_no}}/metadata",
                "fso_name_policy": {
                    "name": "title",
                    "extension": "txt",
                    "sanitize": True
                }
            }
        ]
    }
}


__all__ = ["TAOBAO_DETAIL_POLICY"]
