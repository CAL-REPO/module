# -*- coding: utf-8 -*-
"""crawl_utils.presets.aliexpress_detail
==========================================

AliExpress Product Detail 크롤링 정책

Site: AliExpress
Method: Product Detail (상품 상세)

역할: sync_crawl.yaml 기본값을 override
포함: Site별 차별화가 필요한 설정만 정의
제외: 공통 설정(log, execution, http_session 등)
"""

ALIEXPRESS_DETAIL_POLICY = {
    # Site/Method 식별
    "site": "aliexpress",
    "method": "detail",
    
    # ============================================================================
    # Site-specific 설정만 포함
    # ============================================================================
    
    # Scroll 설정 (AliExpress는 긴 상세 페이지)
    "scroll": {
        "strategy": "infinite",
        "max_scrolls": 15,  # 기본값(10)보다 많이
        "scroll_pause_sec": 1.0
    },
    
    # Wait 설정 (AliExpress 특정 selector)
    "wait": {
        "hook": "css",
        "selector": "[class*='product'], .product-main",
        "timeout_sec": 25.0,  # 기본값(10.0)보다 길게
        "condition": "visibility"
    },
    
    # Extractor 설정 (AliExpress 전용 JS snippet)
    "extractor": {
        "type": "js",
        "js_snippet": """
            // AliExpress 상품 상세 페이지 데이터 추출 (Shadow DOM + SKU 옵션)
            const extractImages = () => {
                const images = [];
                const imageUrls = new Set(); // 중복 방지
                
                // 1. Shadow DOM 내부 이미지 추출 (#product-description)
                const productDesc = document.querySelector('#product-description');
                if (productDesc && productDesc.shadowRoot) {
                    const shadowImages = productDesc.shadowRoot.querySelectorAll('img');
                    shadowImages.forEach(img => {
                        let url = img.getAttribute('src') || img.getAttribute('data-src') || '';
                        if (url && url.includes('ae01.alicdn.com')) {
                            if (url.startsWith('//')) url = 'https:' + url;
                            if (!imageUrls.has(url)) {
                                imageUrls.add(url);
                                images.push({
                                    url: url,
                                    type: 'detail'
                                });
                            }
                        }
                    });
                }
                
                // 2. 일반 DOM 이미지 추출 (상품 메인 이미지, 썸네일 등)
                const selectors = [
                    '.magnifier-image img',
                    '.product-image img',
                    '.images-view-item img',
                    'img[class*="product"]',
                    'img[class*="magnifier"]'
                ];
                
                selectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(img => {
                        let url = img.getAttribute('src') || img.getAttribute('data-src') || '';
                        if (url) {
                            if (url.startsWith('//')) url = 'https:' + url;
                            // alicdn.com 이미지만 추출
                            if (url.includes('alicdn.com') && !imageUrls.has(url)) {
                                imageUrls.add(url);
                                images.push({
                                    url: url,
                                    type: 'product'
                                });
                            }
                        }
                    });
                });
                
                // 3. URL만 추출 (PostProcessor에서 사용)
                return images.map(img => img.url);
            };
            
            const extractSkuOptions = () => {
                const skuOptions = [];
                
                // SKU 옵션 컨테이너 찾기
                const skuWrap = document.querySelector('.sku--wrap--xgoW06M, [class*="sku-item--wrap"]');
                if (!skuWrap) return skuOptions;
                
                // 각 SKU 아이템 추출
                const skuItems = skuWrap.querySelectorAll('[class*="sku-item--image"], [data-sku-col]');
                
                skuItems.forEach(item => {
                    const img = item.querySelector('img');
                    if (!img) return;
                    
                    // 이미지 URL 추출
                    let url = img.getAttribute('src') || img.getAttribute('data-src') || '';
                    if (url.startsWith('//')) url = 'https:' + url;
                    
                    // Alt 속성에서 옵션명 추출 (예: "Note 8", "Note 9")
                    let optionName = img.getAttribute('alt') || '';
                    
                    // data-sku-col에서 추가 정보 추출 가능
                    const skuCol = item.getAttribute('data-sku-col') || '';
                    
                    if (url && url.includes('alicdn.com')) {
                        // 옵션명 정리 (공백 제거, 특수문자 처리)
                        const sanitizedName = optionName.replace(/\\s+/g, '').replace(/[^a-zA-Z0-9가-힣]/g, '');
                        
                        skuOptions.push({
                            url: url,
                            option_name: optionName,
                            sanitized_name: sanitizedName,
                            sku_col: skuCol
                        });
                    }
                });
                
                return skuOptions;
            };
        """
    },
    
    # PostProcessor 설정 (AliExpress 전용 경로 + prefix)
    "post_processor": {
        "target_dir": "{{output_dir}}/crawl/aliexpress",
        "use_smart_normalizer": True,
        "rules": [
            # Rule 1: 상세 이미지 (Detail Images)
            {
                "kind": "image",
                "source": "images",
                "allow_empty": False,
                "dynamic_subdir": "{{cas_no}}/images",
                "fso_name_policy": {
                    "prefix": "DETAILED",  # AliExpress 상세 이미지용 prefix
                    "tail_mode": "counter",
                    "counter_width": 3,
                    # extension 제거: URL에서 자동 추출 (jpg, png, webp 등)
                    "sanitize": True,
                    "ensure_unique": True
                },
                "fso_ops_policy": {
                    "as_type": "file",
                    "exist": {
                        "must_exist": False,
                        "create_if_missing": True,
                        "overwrite": True
                    },
                    "ext": {
                        "default_ext": ".jpg",  # fallback 확장자
                        "force_ext": False,  # URL 기반 확장자 우선 사용
                        "allowed_exts": [".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"]
                    }
                }
            },
            # Rule 2: SKU 옵션 이미지 (Option Images)
            {
                "kind": "image",
                "source": "sku_options[*].url",  # ✨ SKU 옵션 URL 배열 추출
                "allow_empty": True,  # SKU 옵션이 없을 수도 있음
                "dynamic_subdir": "{{cas_no}}/options",  # 별도 폴더에 저장
                "fso_name_policy": {
                    "prefix": "OPTION",  # SKU 옵션 이미지용 prefix
                    "tail_mode": "counter",
                    "counter_width": 2,
                    "tail_suffix": "sku_options[*].sanitized_name",  # ✨ 런타임에 sku_options[*].sanitized_name으로 동적 설정
                    # 예: OPTION_01_Note8.jpg (tail_suffix="Note8")
                    # 예: OPTION_02_Note9.jpg (tail_suffix="Note9")
                    "sanitize": True,
                    "ensure_unique": True
                },
                "fso_ops_policy": {
                    "as_type": "file",
                    "exist": {
                        "must_exist": False,
                        "create_if_missing": True,
                        "overwrite": True
                    },
                    "ext": {
                        "default_ext": ".jpg",
                        "force_ext": False,
                        "allowed_exts": [".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"]
                    }
                }
            }
        ]
    }
}


__all__ = ["ALIEXPRESS_DETAIL_POLICY"]

