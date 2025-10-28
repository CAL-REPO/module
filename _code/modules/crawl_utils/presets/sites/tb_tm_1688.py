# -*- coding: utf-8 -*-
"""
Taobao/Tmall 크롤링 프리셋
- 동일한 HTML 구조 사용 (descV8-container)
"""

from typing import Dict, Any


def get_taobao_detail_preset() -> Dict[str, Any]:
    """
    Taobao 상품 상세 페이지 프리셋
    - 상세 이미지: .descV8-singleImage img
    - 옵션 이미지: .valueItemImgWrap img
    """
    return {
        "scroll": {
            "strategy": "step",
            "max_scrolls": 5,
            "scroll_pause_sec": 0.5,
            "scroll_count": 10,
            "scroll_step_px": 600,
        },
        
        "wait": {
            "hook": "css",
            "selector": ".descV8-container, .desc-root",
            "timeout_sec": 15.0,
            "condition": "visibility"
        },

        "extractor": {
            "type": "js",
            "js_snippet": r"""
// URL 정규화 헬퍼
const urlNormRules = [
    { pattern: /(\.(?:jpe?g|png|webp))(?:_[^/?#]+)?(?=$|\?)/i, replacement: '$1' },
    { pattern: /(\.(?:jpe?g|png|webp))_\.webp(?=$|\?)/i, replacement: '$1' },
    { pattern: /(\.(?:jpe?g|png|webp))!.*?(?=$|\?)/i, replacement: '$1' },
];

function cleanupUrl(rawUrl) {
    if (!rawUrl || typeof rawUrl !== 'string') return null;
    
    let cleaned = rawUrl.trim();
    if (cleaned.startsWith('//')) cleaned = 'https:' + cleaned;
    if (!/^https?:\/\//i.test(cleaned)) return null;
    
    // 썸네일 제거
    cleaned = cleaned
        .replace(/_50x50\..*$/i, "")
        .replace(/_90x90q30\..*$/i, "")
        .replace(/_100x100\..*$/i, "")
        .replace(/_220x220\..*$/i, "")
        .replace(/_640x640\..*$/i, "");
    
    // 정규화 규칙 적용
    for (const {pattern, replacement} of urlNormRules) {
        cleaned = cleaned.replace(pattern, replacement);
    }
    
    // 쿼리 제거
    cleaned = cleaned.split('?')[0].split('#')[0];
    
    return cleaned;
}

// 이미지 URL 추출
function extractImageUrl(element) {
    if (!element) return '';
    
    const candidates = [
        'src', 'data-src', 'data-original', 
        'data-lazy', 'data-srcset', 'lazy-src'
    ];
    
    for (const attr of candidates) {
        const val = element.getAttribute && element.getAttribute(attr);
        if (val && val.trim() && !val.includes('s.gif')) {
            return val.trim();
        }
    }
    
    return '';
}

// 상세 이미지 수집
function collectDetailImages() {
    const foundUrls = new Set();
    const resultList = [];
    
    // descV8-singleImage 이미지
    const detailImgs = document.querySelectorAll('.descV8-singleImage img, .desc-root img');
    detailImgs.forEach(img => {
        const raw = extractImageUrl(img);
        const normalized = cleanupUrl(raw);
        if (normalized && !foundUrls.has(normalized)) {
            foundUrls.add(normalized);
            resultList.push(normalized);
        }
    });
    
    return resultList;
}

// 옵션 이미지 수집
function collectOptionImages() {
    const optionsList = [];
    const foundKeys = new Set();
    
    // 옵션 영역 탐색
    const optionRoots = [
        '.skuItem--Z2AJB9Ew',
        '#skuOptionsArea',
        '.sku-property',
        '.sku-item-list'
    ];
    
    let rootEl = null;
    for (const sel of optionRoots) {
        const found = document.querySelector(sel);
        if (found) { rootEl = found; break; }
    }
    
    if (!rootEl) return optionsList;
    
    // 옵션 이미지 추출
    const optionItems = rootEl.querySelectorAll('.valueItemImgWrap img, .valueItem img');
    optionItems.forEach(img => {
        const raw = extractImageUrl(img);
        const normalized = cleanupUrl(raw);
        if (!normalized) return;
        
        // 옵션 이름
        const parent = img.closest('.valueItem--smR4pNt4, .valueItem');
        let optName = '';
        if (parent) {
            const nameEl = parent.querySelector('[title], span.f-els-1');
            optName = (nameEl && (nameEl.getAttribute('title') || nameEl.textContent || '')).trim();
        }
        
        // 이름 정규화
        optName = optName.replace(/\s+/g, '').replace(/[^a-zA-Z0-9가-힣]/g, '');
        
        const uniqueKey = `${normalized}|${optName}`;
        if (!foundKeys.has(uniqueKey)) {
            foundKeys.add(uniqueKey);
            optionsList.push({
                url: normalized,
                name: optName
            });
        }
    });
    
    return optionsList;
}

return {
    images: collectDetailImages(),
    optionsItems: collectOptionImages()
};
""",
        },

        "items": [
            # 상세 이미지
            {
                "kind": "image",
                "source": "images",
                "dir_path": None,
                "fso_name": {
                    "as_type": "file",
                    "prefix": "TB",
                    "name": "DETAILED",
                    "tail_mode": "counter",
                    "tail_suffix": "",
                    "counter_width": 2,
                    "delimiter": "_",
                    "extension": "",
                    "auto_expand": True,
                    "sanitize": True,
                    "case": "upper",
                    "ensure_unique": False
                },
                "fso_ops": {
                    "as_type": "file",
                    "exist": {
                        "must_exist": True,
                        "create_if_missing": True,
                        "overwrite": True
                    }
                }
            },

            # 옵션 이미지
            {
                "kind": "image",
                "source": "optionsItems__url",
                "dir_path": None,
                "fso_name": {
                    "as_type": "file",
                    "prefix": "TB",
                    "name": "OPTION",
                    "tail_mode": "counter",
                    "tail_suffix": "optionsItems__name",
                    "counter_width": 2,
                    "delimiter": "_",
                    "extension": "",
                    "auto_expand": True,
                    "sanitize": True,
                    "case": "upper",
                    "ensure_unique": False
                },
                "fso_ops": {
                    "as_type": "file",
                    "exist": {
                        "must_exist": True,
                        "create_if_missing": True,
                        "overwrite": True
                    }
                }
            }
        ]
    }


def get_tmall_detail_preset() -> Dict[str, Any]:
    """
    Tmall 상품 상세 페이지 프리셋
    - Taobao와 동일한 HTML 구조 사용
    """
    preset = get_taobao_detail_preset()
    # Prefix만 변경
    preset["items"][0]["fso_name"]["prefix"] = "TM"
    preset["items"][1]["fso_name"]["prefix"] = "TM"
    return preset


def get_1688_detail_preset() -> Dict[str, Any]:
    """
    1688 상품 상세 페이지 프리셋
    - Shadow DOM 사용: v-detail-q 컴포넌트
    - 옵션 이미지: .sku-filter-button img
    """
    return {
        "scroll": {
            "strategy": "step",
            "max_scrolls": 5,
            "scroll_pause_sec": 0.5,
            "scroll_count": 10,
            "scroll_step_px": 600,
        },
        
        "wait": {
            "hook": "css",
            "selector": ".od-collapse-module, v-detail-q",
            "timeout_sec": 15.0,
            "condition": "visibility"
        },

        "extractor": {
            "type": "js",
            "js_snippet": r"""
// URL 정규화
const urlRules = [
    { pattern: /(\.(?:jpe?g|png|webp))(?:_[^/?#]+)?(?=$|\?)/i, replacement: '$1' },
    { pattern: /(\.(?:jpe?g|png|webp))_\.webp(?=$|\?)/i, replacement: '$1' },
    { pattern: /(\.(?:jpe?g|png|webp))!.*?(?=$|\?)/i, replacement: '$1' },
];

function normalizeImageUrl(rawUrl) {
    if (!rawUrl || typeof rawUrl !== 'string') return null;
    
    let url = rawUrl.trim();
    if (url.startsWith('//')) url = 'https:' + url;
    if (!/^https?:\/\//i.test(url)) return null;
    
    // 썸네일 제거
    url = url
        .replace(/_sum\.jpg$/i, ".jpg")
        .replace(/_\d+x\d+\..*$/i, "")
        .replace(/_Q\d+\./i, ".");
    
    // 정규화
    for (const {pattern, replacement} of urlRules) {
        url = url.replace(pattern, replacement);
    }
    
    // 쿼리/해시 제거
    url = url.split('?')[0].split('#')[0];
    return url;
}

// 이미지 URL 추출
function getImgUrl(elem) {
    if (!elem) return '';
    const attrs = ['src', 'data-src', 'data-original', 'lazy-src'];
    for (const attr of attrs) {
        const val = elem.getAttribute && elem.getAttribute(attr);
        if (val && val.trim()) return val.trim();
    }
    return '';
}

// Shadow DOM 상세 이미지 수집
function collectShadowDetailImages() {
    const foundUrls = new Set();
    const results = [];
    
    // v-detail-q shadow root 탐색
    try {
        const vDetailQ = document.querySelector('v-detail-q');
        if (vDetailQ && vDetailQ.shadowRoot) {
            const shadowImgs = vDetailQ.shadowRoot.querySelectorAll('img');
            shadowImgs.forEach(img => {
                const raw = getImgUrl(img);
                const normalized = normalizeImageUrl(raw);
                if (normalized && !foundUrls.has(normalized)) {
                    foundUrls.add(normalized);
                    results.push(normalized);
                }
            });
        }
    } catch(e) {}
    
    // 일반 DOM 이미지도 수집
    try {
        const regularImgs = document.querySelectorAll('.od-collapse-module img, #detail img');
        regularImgs.forEach(img => {
            const raw = getImgUrl(img);
            const normalized = normalizeImageUrl(raw);
            if (normalized && !foundUrls.has(normalized)) {
                foundUrls.add(normalized);
                results.push(normalized);
            }
        });
    } catch(e) {}
    
    return results;
}

// 옵션 이미지 수집
function collectOptionImages() {
    const options = [];
    const foundKeys = new Set();
    
    // 옵션 버튼 탐색
    const optionButtons = document.querySelectorAll('.sku-filter-button, .transverse-filter button');
    optionButtons.forEach(btn => {
        try {
            const img = btn.querySelector('img');
            if (!img) return;
            
            const raw = getImgUrl(img);
            const normalized = normalizeImageUrl(raw);
            if (!normalized) return;
            
            // 옵션명 추출
            const nameEl = btn.querySelector('.label-name');
            let optName = (nameEl && nameEl.textContent || '').trim();
            optName = optName.replace(/\s+/g, '').replace(/[^a-zA-Z0-9가-힣]/g, '');
            
            const key = `${normalized}|${optName}`;
            if (!foundKeys.has(key)) {
                foundKeys.add(key);
                options.push({
                    url: normalized,
                    name: optName
                });
            }
        } catch(e) {}
    });
    
    return options;
}

return {
    images: collectShadowDetailImages(),
    optionsItems: collectOptionImages()
};
""",
        },

        "items": [
            # 상세 이미지
            {
                "kind": "image",
                "source": "images",
                "dir_path": None,
                "fso_name": {
                    "as_type": "file",
                    "prefix": "AL",  # 1688 = Alibaba
                    "name": "DETAILED",
                    "tail_mode": "counter",
                    "tail_suffix": "",
                    "counter_width": 2,
                    "delimiter": "_",
                    "extension": "",
                    "auto_expand": True,
                    "sanitize": True,
                    "case": "upper",
                    "ensure_unique": False
                },
                "fso_ops": {
                    "as_type": "file",
                    "exist": {
                        "must_exist": True,
                        "create_if_missing": True,
                        "overwrite": True
                    }
                }
            },

            # 옵션 이미지
            {
                "kind": "image",
                "source": "optionsItems__url",
                "dir_path": None,
                "fso_name": {
                    "as_type": "file",
                    "prefix": "AL",
                    "name": "OPTION",
                    "tail_mode": "counter",
                    "tail_suffix": "optionsItems__name",
                    "counter_width": 2,
                    "delimiter": "_",
                    "extension": "",
                    "auto_expand": True,
                    "sanitize": True,
                    "case": "upper",
                    "ensure_unique": False
                },
                "fso_ops": {
                    "as_type": "file",
                    "exist": {
                        "must_exist": True,
                        "create_if_missing": True,
                        "overwrite": True
                    }
                }
            }
        ]
    }


__all__ = [
    "get_taobao_detail_preset",
    "get_tmall_detail_preset",
    "get_1688_detail_preset",
]
