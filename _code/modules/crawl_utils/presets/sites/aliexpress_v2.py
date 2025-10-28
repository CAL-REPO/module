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
            "selector": "product-description img",
            "timeout_sec": 15.0,
            "condition": "visibility"
        },


        "extractor": {
            "type": "js",
            "js_snippet": r"""
// --- 최소 헬퍼: URL 정규화/추출만 남김 ---
const __rules = [
    { re: /(\.(?:jpe?g|png|webp))(?:_[^/?#]+)?(?=$|\?)/i, rep: '$1' },
    { re: /(\.(?:jpe?g|png|webp))_\.webp(?=$|\?)/i, rep: '$1' },
    { re: /(\.(?:jpe?g|png|webp))!.*?(?=$|\?)/i, rep: '$1' },
];

function __normalize(u, { stripQuery=true, stripHash=true } = {}){
    if(!u || typeof u !== 'string') return null;
    u = u.trim();
    if(u.startsWith('//')) u = 'https:' + u;
    if(!/^https?:\/\//i.test(u)) return null;
    for(const {re,rep} of __rules) u = u.replace(re, rep);
    if(stripQuery) u = u.split('?')[0];
    if(stripHash) u = u.split('#')[0];
    return u;
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

// --- "open shadowRoot 순회 + 이미지 추출"만 ---

# function __collectDetail(){
#   const seen = new Set();
#   const out = [];

#   // 1️⃣ shadowRoot 열린 host 자동 탐색
#   const hosts = [];
#   document.querySelectorAll('*').forEach(el => {
#     if (el.shadowRoot) hosts.push(el);
#     else if (el.querySelector && el.querySelector('template[shadowrootmode="open"]')) {
#       hosts.push(el.querySelector('template[shadowrootmode="open"]').parentElement);
#     }
#   });

#   // 2️⃣ 내부 이미지 추출
#   hosts.forEach(host => {
#     try {
#       const imgs = host.shadowRoot ? host.shadowRoot.querySelectorAll('img') : [];
#       imgs.forEach(im => {
#         const raw = pickImageUrl(im);
#         const u = __normalize(raw);
#         if (u && !seen.has(u)) { seen.add(u); out.push(u); }
#       });
#     } catch (e) {}
#   });

#   console.log(`[auto shadowRoot] found: ${out.length}`);
#   console.table(out);
#   return out;
# }

function __collectDetail(){
  const seen = new Set();
  const out = [];

    // 모든 open shadowRoot를 순회하여 이미지 추출
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

const images = __collectDetail();

// 스크립트에서 찾은 이미지 병합 (중복 제거)
try{
    const scriptImgs = __collectFromScripts();
    const seen = new Set(images);
    for(const s of scriptImgs){ if(s && !seen.has(s)){ seen.add(s); images.push(s); } }
}catch(e){}

return {
    images: images,
};

""",
        },

    # Save 규칙 (ItemPostProcessPolicy)
    "items": [
            # 1) 상세 이미지 (배열 자동 explode)
            {
                "kind": "image",
                "source": "images",              # KeyPath: images (배열)
                "dir_path": None,               # None=downloads()
                "fso_name": {
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
                "fso_ops": {
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

            # # 2) SKU 옵션 이미지
            # {
            #     "kind": "image",
            #     # 엔진이 점 표기만 지원하면 "skuOptions[*].url"로 교체
            #     "source": "",
            #     "directory": None,
            #     "name": {
            #         "as_type": "file",
            #         "prefix": "OPTION",
            #         "name": "TEST",
            #         "tail_mode": "counter",
            #         "counter_width": 3,
            #         "delimiter": "_",
            #         "extension": ".jpg",
            #         "auto_expand": True,
            #         "sanitize": True,
            #         "case": "keep",
            #         "ensure_unique": False
            #     },
            #     "ops": {
            #         "as_type": "file",
            #         "exist": {
            #             "must_exist": False,
            #             "create_if_missing": True,
            #             "overwrite": True
            #         },
            #         "ext": {
            #             "require_ext": False,
            #             "default_ext": ".jpg",
            #             "allowed_exts": None
            #         }
            #     }
            # }
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
