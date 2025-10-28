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
            "selector": "div.detailmodule_image img",
            "timeout_sec": 30.0,
            "condition": "visibility"
        },


        "extractor": {
            "type": "js",
            "js_snippet": r"""
// 0) 정규화 규칙 (기존 규칙 유지)
const __rules = [
    { re: /(\.(?:jpe?g|png|webp))(?:_[^/?#]+)?(?=$|\?)/i, rep: '$1' },
    { re: /(\.(?:jpe?g|png|webp))_\.webp(?=$|\?)/i, rep: '$1' },
    { re: /(\.(?:jpe?g|png|webp))!.*?(?=$|\?)/i, rep: '$1' },
];

function __normalize(u, { stripQuery=true, stripHash=true } = {}){
    if(!u) return null;
    if(typeof u !== 'string') return null;
    u = u.trim();
    if(u.startsWith('//')) u = 'https:' + u;
    if(!/^https?:\/\//i.test(u)) return null;
    for(const {re,rep} of __rules) u = u.replace(re, rep);
    if(stripQuery) u = u.split('?')[0];
    if(stripHash) u = u.split('#')[0];
    return u;
}

// 안전한 텍스트 검사 (View more 버튼 등)
function _textMatches(el, re){
    try{
        const t = (el.textContent || el.innerText || '').trim();
        return re.test(t);
    }catch(e){ return false; }
}

// A) 'View more' 클릭 - :has/:matches 같은 비표준/미지원 선택자를 제거하고
// 버튼 목록을 순회하며 텍스트 매칭으로 클릭을 시도합니다.
function clickViewMore(){
    try{
        const patterns = [/^\s*View more\s*$/i, /더\s*보기|더보기/i, /View\s*more/i, /Show\s*more/i];
        const nodes = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
        for(const node of nodes){
            for(const p of patterns){
                if(_textMatches(node, p)){
                    try{ node.click(); }catch(e){}
                    return true;
                }
            }
        }

        // 특수 data-role 속성 등도 시도
        const special = document.querySelectorAll('[data-role]');
        for(const el of special){
            const dr = el.getAttribute('data-role') || '';
            if(/view-?more/i.test(dr)){
                try{ el.click(); }catch(e){}
                return true;
            }
        }
    }catch(e){}
    return false;
}

// B) 강제 스크롤 / 이벤트 트리거: lazy load를 촉발시키기 위해 여러 단계로 스크롤
function forceLazyLoad(){
    try{
        const H = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight || 0);
        window.scrollTo(0, 0);
        const steps = 6;
        for(let i=1;i<=steps;i++){
            const y = Math.floor((H * i) / steps);
            window.scrollTo(0, y);
        }
        window.scrollTo(0, Math.max(0, H - 10));
        // 추가 이벤트
        window.dispatchEvent(new Event('scroll'));
        window.dispatchEvent(new Event('resize'));
        try{ window.dispatchEvent(new MouseEvent('mousemove')); }catch(e){}
    }catch(e){}
}

// 이미지 URL 추출 헬퍼: src/srcset/background-image 모두 지원
function pickImageUrl(el){
    if(!el) return '';
    try{
        // 우선 표준 속성들
        const attrs = ['src','data-src','data-original','data-lazy','data-srcset','data-ks-lazyload','lazy-src'];
        for(const a of attrs){
            const v = el.getAttribute && el.getAttribute(a);
            if(v && typeof v === 'string' && v.trim()){
                // srcset 같은 경우 첫번째 후보 선택
                if(a.toLowerCase().includes('srcset') || v.includes(',')){
                    const cand = v.split(',').map(s=>s.trim().split(' ')[0]).find(Boolean);
                    if(cand) return cand;
                }
                return v.trim();
            }
        }

        // srcset 속성이 별도로 있을 수 있음
        const ss = el.getAttribute && el.getAttribute('srcset');
        if(ss){
            const cand = ss.split(',').map(s=>s.trim().split(' ')[0]).find(Boolean);
            if(cand) return cand;
        }

        // background-image
        try{
            const st = window.getComputedStyle ? window.getComputedStyle(el) : null;
            const bg = st && st.backgroundImage || '';
            const m = bg && bg.match(/url\(["']?(.*?)["']?\)/i);
            if(m && m[1]) return m[1];
        }catch(e){}

    }catch(e){}
    return '';
}

// 1) 상세 이미지 수집 (iframe, shadowRoot, background 포함)
function __collectDetail(){
    const seen = new Set();
    const out = [];
    const sels = [
        'div.detailmodule_image img',
        '#product-description img',
        '.product-description img',
        '.product-detail img',
        '[data-spm-anchor-id] img',
        'article img',
        '.product-gallery img',
        '.images-wrap img'
    ];

    for(const s of sels){
        try{
            document.querySelectorAll(s).forEach(im=>{
                const raw = pickImageUrl(im) || '';
                const u = __normalize(raw);
                if(u && !seen.has(u)){
                    seen.add(u); out.push(u);
                }
            });
        }catch(e){}
    }

    // 배경 이미지를 가진 요소들도 체크
    try{
        const bgEls = Array.from(document.querySelectorAll('[style*="background"]'));
        bgEls.forEach(el=>{
            const raw = pickImageUrl(el);
            const u = __normalize(raw);
            if(u && !seen.has(u)){ seen.add(u); out.push(u); }
        });
    }catch(e){}


    // Shadow DOM 내부 이미지
    try{
        const desc = document.querySelector('#product-description');
        if(desc && desc.shadowRoot){
            desc.shadowRoot.querySelectorAll('img').forEach(im=>{
                const raw = pickImageUrl(im);
                const u = __normalize(raw);
                if(u && !seen.has(u)){ seen.add(u); out.push(u); }
            });
        }
    }catch(e){}


    // 모든 open shadowRoot를 순회하여 이미지 추출 (host가 #product-description이 아닐 수도 있음)
    try{
        const all = Array.from(document.querySelectorAll('*'));
        for(const el of all){
            try{
                if(el && el.shadowRoot){
                    el.shadowRoot.querySelectorAll('img').forEach(im=>{
                        const raw = pickImageUrl(im);
                        const u = __normalize(raw);
                        if(u && !seen.has(u)){ seen.add(u); out.push(u); }
                    });
                }
            }catch(e){}
        }
    }catch(e){}

    // iframe 내부의 경우 같은 출처이면 접근 시도
    try{
        const iframes = Array.from(document.querySelectorAll('iframe'));
        for(const ifr of iframes){
            try{
                const doc = ifr.contentDocument || ifr.contentWindow && ifr.contentWindow.document;
                if(doc){
                    const imgs = doc.querySelectorAll('img');
                    imgs.forEach(im=>{
                        const raw = (im.getAttribute && pickImageUrl(im)) || '';
                        const u = __normalize(raw);
                        if(u && !seen.has(u)){ seen.add(u); out.push(u); }
                    });
                }
            }catch(e){
                // cross-origin iframe: 접근 불가
            }
        }
    }catch(e){}

    return out;
}

// 2) SKU 옵션 이미지 수집 (이미지-텍스트 추출 보강)
function __collectSku(){
    const opts = [];
    const seen = new Set();
    const roots = [
        '.sku--wrap--xgoW06M',
        "[class*='sku-item--wrap']",
        '[data-sku-col]',
        '.sku-property',
        '.sku-item-list',
        '.sku-attr-list',
        '.sku-attr'
    ];

    let root = null;
    for(const r of roots){ try{ const el = document.querySelector(r); if(el){ root = el; break; } }catch(e){}
    }
    if(!root) return [];

    try{
        root.querySelectorAll('img').forEach(img=>{
            const raw = pickImageUrl(img) || '';
            const url = __normalize(raw);
            if(url && !seen.has(url)){
                seen.add(url);
                // 옵션 라벨 추출: 인접 텍스트 우선
                let label = '';
                try{
                    const parent = img.closest('[class*="sku"]') || img.parentElement || img.closest('li') || img.closest('div');
                    if(parent){
                        const t = parent.querySelector('span, div, [class*="title"], [class*="name"], [class*="text"]');
                        label = t ? (t.textContent || '').trim() : '';
                    }
                }catch(e){}
                opts.push({ url: url, label: label || 'option' });
            }
        });
    }catch(e){}

    return opts;
}

// 3) 제품 제목 추출 (기본 로직 유지)
function __getTitle(){
    const sels = [
        'h1.product-title-text',
        '.product-title',
        '[data-pl="product-title"]',
        'h1'
    ];
    for(const s of sels){ try{ const el = document.querySelector(s); if(el && el.textContent && el.textContent.trim()) return el.textContent.trim(); }catch(e){}
    }
    return 'Untitled';
}

// 실행: 먼저 ViewMore 클릭, lazy load 트리거, 수집
try{ clickViewMore(); }catch(e){}
try{ forceLazyLoad(); }catch(e){}

// inline script/text에서 이미지 URL 추출(embedded JSON 등 처리용)
function __collectFromScripts(){
    const out = [];
    try{
        const re = /https?:\/\/[-\w\.\/@:%_+~#=]+\.(?:jpe?g|png|webp)(?:[^"'\s<>]*)/ig;
        Array.from(document.querySelectorAll('script')).map(s=>s.textContent||'').forEach(txt=>{
            if(!txt) return;
            let m;
            while((m = re.exec(txt))){
                try{ const u = __normalize(m[0]); if(u) out.push(u); }catch(e){}
            }
        });
    }catch(e){}

    return out;
}

const __title = __getTitle();
const images = __collectDetail();

// 스크립트에서 찾은 이미지 병합 (중복 제거)
try{
    const scriptImgs = __collectFromScripts();
    const seen = new Set(images);
    for(const s of scriptImgs){ if(s && !seen.has(s)){ seen.add(s); images.push(s); } }
}catch(e){}

return {
    title: __title,
    images: images,
    skuOptions: __collectSku()
};
""",
    },

        # Save 규칙 (ItemPostProcessPolicy)
        "save": [
            # 1) 상세 이미지 (배열 자동 explode)
            {
                "kind": "image",
                "source": "images",              # KeyPath: images (배열)
                "directory": None,               # None=downloads()
                "name": {
                    "as_type": "file",
                    "prefix": "DETAILED",
                    "name": "TEST",
                    "tail_mode": "counter",
                    "counter_width": 3,          # 001 형태
                    "delimiter": "_",
                    "extension": ".jpg",         # ✅ 기본 확장자
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
                        "require_ext": False,    # ✅ URL 확장자 없어도 저장
                        "default_ext": ".jpg",
                        "allowed_exts": None
                    }
                }
            },

            # 2) SKU 옵션 이미지
            {
                "kind": "image",
                # 엔진이 점 표기만 지원하면 "skuOptions[*].url"로 교체
                "source": "skuOptions__url",
                "directory": None,
                "name": {
                    "as_type": "file",
                    "prefix": "OPTION",
                    "name": "TEST",
                    "tail_mode": "counter",
                    "counter_width": 3,
                    "delimiter": "_",
                    "extension": ".jpg",
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
                        "require_ext": False,
                        "default_ext": ".jpg",
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
