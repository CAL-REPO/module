# -*- coding: utf-8 -*-
"""
Aliexpress 크롤링 프리셋
"""

from pathlib import Path
from typing import Dict, Any


# -*- coding: utf-8 -*-
from typing import Dict, Any

def get_aliexpress_detail_preset() -> Dict[str, Any]:
    """
    Aliexpress 상품 상세 페이지 하이브리드 추출 프리셋
    - DOM 셀렉터 1차 추출 + JS 보정 2차 추출 → 병합 반환
    - 이미지/옵션 이미지 저장 시 확장자 기본값 부여 (.jpg)
    """
    return {
        "scroll": {
            "strategy": "step",
            "max_scrolls": 5,
            "scroll_pause_sec": 0.5,  # ✅ 스크롤 후 충분한 대기
            "scroll_count": 10,
            "scroll_step_px": 600,
        },
        # Wait 정책 (후보 셀렉터 OR)
        "wait": {
            "hook": "css",
            "selector": "product-description nav-description img",
            "timeout_sec": 15.0,
            "condition": "visibility"
        },


        "extractor": {
            "type": "js",
            "js_snippet": r"""
// --- 최소 헬퍼: URL 정규화/추출만 남김 ---
const normalizeRules = [
    { re: /(\.(?:jpe?g|png|webp))(?:_[^/?#]+)?(?=$|\?)/i, rep: '$1' },
    { re: /(\.(?:jpe?g|png|webp))_\.webp(?=$|\?)/i, rep: '$1' },
    { re: /(\.(?:jpe?g|png|webp))!.*?(?=$|\?)/i, rep: '$1' },
];

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

function normalizeUrl(url, { stripQuery=true, stripHash=true } = {}){
    if(!url || typeof url !== 'string') return null;
    url = url.trim();
    if(url.startsWith('//')) url = 'https:' + url;
    if(!/^https?:\/\//i.test(url)) return null;
    for(const {re,rep} of normalizeRules) url = url.replace(re, rep);
    if(stripQuery) url = url.split('?')[0];
    if(stripHash) url = url.split('#')[0];
    return url;
}

// 이미지 URL 추출 헬퍼: src/srcset/background-image 모두 지원
function getImageUrl(el){
    if(!el) return '';
    try{
        // 우선 표준 속성들
        const attrs = [
            'src',
            'data-src',
            'data-original',
            'data-lazy',
            'data-srcset',
            'data-ks-lazyload',
            'lazy-src'
        ];
        for(const attr of attrs){
            const str = el.getAttribute && el.getAttribute(attr);
            if(str && typeof str === 'string' && str.trim()){
                // srcset 같은 경우 첫번째 후보 선택
                if(attr.toLowerCase().includes('srcset') || str.includes(',')){
                    const cand = str.split(',').map(s=>s.trim().split(' ')[0]).find(Boolean);
                    if(cand) return cand;
                }
                return str.trim();
            }
        }

        // srcset 속성이 별도로 있을 수 있음
        const srcSet = el.getAttribute && el.getAttribute('srcset');
        if(srcSet){
            const cand = srcSet.split(',').map(s=>s.trim().split(' ')[0]).find(Boolean);
            if(cand) return cand;
        }

        // background-image
        try{
            const st = window.getComputedStyle ? window.getComputedStyle(el) : null;
            const bg = st && st.backgroundImage || '';
            const match = bg && bg.match(/url\(["']?(.*?)["']?\)/i);
            if(match && match[1]) return match[1];
        }catch(e){}

    }catch(e){}
    return '';
}

// --- "open shadowRoot 순회 + 이미지 추출"만 ---
function getDetailImages(){
  const seen = new Set();
  const out = [];

    // 모든 open shadowRoot를 순회하여 이미지 추출
    try{
        const all = Array.from(document.querySelectorAll('*'));
        for(const el of all){
            try{
                if(el && el.shadowRoot){
                    el.shadowRoot.querySelectorAll('img').forEach(im=>{
                        const raw = getImageUrl(im);
                        const url = normalizeUrl(raw);
                        if(url && !seen.has(url)){ seen.add(url); out.push(url); }
                    });
                }
            }catch(e){}
        }
    }catch(e){}
  
    try{
        const iframes = Array.from(document.querySelectorAll('iframe'));
        for(const ifr of iframes){
            try{
                const doc = ifr.contentDocument || ifr.contentWindow && ifr.contentWindow.document;
                if(doc){
                    const imgs = doc.querySelectorAll('img');
                    imgs.forEach(im=>{
                        const raw = (im.getAttribute && getImageUrl(im)) || '';
                        const url = normalizeUrl(raw);
                        if(url && !seen.has(url)){ seen.add(url); out.push(url); }
                    });
                }
            }catch(e){
                // cross-origin iframe: 접근 불가
            }
        }
    }catch(e){}

    return out;
}
    
// inline script/text에서 이미지 URL 추출(embedded JSON 등 처리용)
function getEmbedImages(){
    const out = [];
    try{
        const re = /https?:\/\/[-\w\.\/@:%_+~#=]+\.(?:jpe?g|png|webp)(?:[^"'\s<>]*)/ig;
        Array.from(document.querySelectorAll('script')).map(s=>s.textContent||'').forEach(txt=>{
            if(!txt) return;
            let str;
            while((str = re.exec(txt))){
                try{ const url = normalizeUrl(str[0]); if(url) out.push(url); }catch(e){}
            }
        });
    }catch(e){}

    return out;
}

// option extraction
function getOptionsItems() {
    const optionsItems = [];
    const seen = new Set();
    const roots = [
        '.sku--wrap--xgoW06M',
        "[class*='sku-item--wrap']",
        '[data-sku-col]',
        '.sku-property',
        '.sku-item-list',
        '.sku-attr-list'
    ];
    //루트 탐색
    let root = null;
    for (const selector of roots) {
        const el = document.querySelector(selector);
        if (el) { root = el; break; }
    }
    if (!root) return optionsItems;

    //후보 이미지 탐색
    const cand = root.querySelectorAll('img, [data-sku-col]');
    cand.forEach(item => {

        // 이미지 엘리먼트 식별
        const img = (item.tagName && item.tagName.toLowerCase() === 'img')
            ? item
            : (item.querySelector && item.querySelector('img'));

        if (!img) return;

        // URL 정규화
        let url = normalizeUrl(img.getAttribute('src') || img.getAttribute('data-src') || img.src);
        if (!url) return;
        url = enhanceUrl(url);

        // 옵션 이름 추출
        let optionName = (
            img.getAttribute('alt') ||
            img.getAttribute('title') ||
            (item.getAttribute && item.getAttribute('title')) ||
            item.textContent ||
            ''
        ).trim();

        // 중복 제거
        const key = `${url}|${optionName}`;
        if (seen.has(key)) return;
        seen.add(key);

        // SKU 정보 저장
        optionsItems.push({
            url,
            name: optionName.replace(/\s+/g, '').replace(/[^a-zA-Z0-9가-힣]/g, '')
        });

    });

    return optionsItems;
}


const images = getDetailImages();
// 스크립트에서 찾은 이미지 병합 (중복 제거)
try{
    const embedImages = getEmbedImages();
    const seen = new Set(images);
    for(const img of embedImages){ if(img && !seen.has(img)){ seen.add(img); images.push(img); } }
}catch(e){}

return {
    images: images,
    optionsItems: getOptionsItems()
};

""",
        },

        # items policy
        "items": [
            # 1) 상세 이미지 (배열 자동 explode)
            {
                "kind": "image",
                "source": "images",              # KeyPath: images (배열)
                "dir_path": None,               # None=downloads()
                "fso_name": {
                    "as_type": "file",
                    "prefix": "ALI",
                    "name": "DETAILED",
                    "tail_mode": "counter",
                    "tail_suffix": "",
                    "counter_width": 2,         # 01 형태
                    "delimiter": "_",
                    "extension": "",         # ✅ 기본 확장자
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

            # 2) 옵션 이미지
            {
                "kind": "image",
                "source": "optionsItems__url",
                "dir_path": None,
                "fso_name": {
                    "as_type": "file",
                    "prefix": "ALI",
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
        
        "items": [
            # 각 검색 결과의 썸네일 이미지
            {
                "kind": "image",
                "source": "thumbnail",  # KeyPath: thumbnail (각 record)
                "dir_path": None,  # ✅ None = downloads() 사용 (사용자가 override로 주입 권장)
                "fso_name": {
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
                "fso_ops": {
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
