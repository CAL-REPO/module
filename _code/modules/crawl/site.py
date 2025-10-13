# -*- coding: utf-8 -*-
# crawl/site.py

"""
crawlsite.py — 사이트별 크롤링 설정 모음
==========================================
사이트별:
- accept_header_context
- url_attrs
- js_context (wait_for, scroll, delay, selector, extract_script)
- option_context (image_selector, title_selector)
- normalizer 규칙

"""
url_attrs = {
    "google": {
            "base_url": "https://www.google.com",
            "search_path": "/search?q={keyword}&hl=ko",
    },
    
    "taobao":{
            "base_url": "https://s.taobao.com",
            "search_path": "/search?q={keyword}",
    },
    
    "tmall":{
            "base_url": "https://list.tmall.com",
            "search_path": "/search_product.htm?q={keyword}"
    },
    
    "aliexpress":{
            "base_url": "https://www.aliexpress.com",
            "search_path": "/wholesale?SearchText={keyword}",
    },
    
    "1688":{
            "base_url": "https://s.1688.com",
            "search_path": "/selloffer/offer_search.htm?keywords={keyword}",
    }
}


# 📌 Google
google_img = {
    "wait": {
        "selector": "img",
        "timeout": 20 # second
    },
    "scroll": {
        "min_steps": 10,
        "max_steps": 20,
        "min_pause": 0.5,
        "max_pause": 3
    },
    "js_extract_script": """
            const urls = new Set();
            document.querySelectorAll("img").forEach(im => {
                let u = im.getAttribute("data-src") || im.getAttribute("src") || "";
                if (u.startsWith("//")) u = "https:" + u;
                if (/^https?:\/\//i.test(u) && !/s\.gif$/i.test(u)) urls.add(u);
            });
            return Array.from(urls);
        """,
    "regex": [
        {
            "pattern": r'(\.(?:jpe?g|png|webp))(?:_[^/?#]+)?(?=$|\?)',
            "replace": r'\1',
            "flags": 'i'
        }
    ],
    "file": {
        "save_method": "searched_img",
        "save_dir": "",
        "name": "DETAILED",
        "name_prefix": "",
        "min_size": 1024,
        "max_width": 4096,
        "max_height": 4096,
        "quality": 85,
        "exif": false,
    },
    
}

# 📌 Taobao, Tmall
taobao_tmall_detailed_page = {
    "Accept_context": "",
    "Accept_encoding": "",

    "wait": {
        "selector": ".descV8-singleImage .valueItemImgWrap--ZvA2Cmim img",
        "timeout": 20 # second
    },
    "scroll": {
        "min_steps": 10,
        "max_steps": 20,
        "min_pause": 0.5,
        "max_pause": 3
    },
    "regex": [
        {
            "pattern": r'(\.(?:jpe?g|png|webp))(?:_[^/?#]+)?(?=$|\?)',
            "replace": r'\1',
            "flags": 'i'
        },
        {
            "pattern": r'(\.(?:jpe?g|png|webp))_\.webp(?=$|\?)',
            "replace": r'\1',
            "flags": 'i'
        },
        {
            "pattern": r'(\.(?:jpe?g|png|webp))!.*?(?=$|\?)',
            "replace": r'\1',
            "flags": 'i'
        }
    ],
    "js_extract_script": """
        const result = {
            detailed: [],
            option: [],
        };
        // 상세 이미지 추출
        document.querySelectorAll(".descV8-singleImage img").forEach(im => {
        let u = im.getAttribute("data-src") || im.getAttribute("src") || "";
        if (u.startsWith("//")) u = "https:" + u;

        let title = "";

        // 유효한 URL인 경우
        if (/^https?:\/\//i.test(u) && !/s\.gif$/i.test(u)) {
            result.detailed.push([title, u]);
        }
        });

        // 옵션 이미지 추출
        document.querySelectorAll(".valueItemImgWrap--ZvA2Cmim img").forEach(im => {
        let u = im.getAttribute("data-src") || im.getAttribute("src") || "";
        if (u.startsWith("//")) u = "https:" + u;

        let title = "";
        const span = im.parentElement?.nextElementSibling;
        if (span) {
            title = span.getAttribute("title") || span.textContent.trim();
        }

        // 유효한 URL인 경우
        if (/^https?:\/\//i.test(u) && !/s\.gif$/i.test(u)) {
            result.option.push([title, u]);
        }
        });
        """,
    "file": {
        "save_dir": "",
        "name": "",
        "name_prefix": "",
        "name_suffix": "",
        "min_size": 1024,
        "max_width": 4096,
        "max_height": 4096,
        "quality": 85,
        "exif": false,
    }
}

# 📌 AliExpress
aliexpress_detailed_page_img = {
    "wait": {
        "selector": "div.detailmodule_image img",
        "timeout": 20 # second
    },
    "scroll": {
        "step": 15,
        "pause": 0.5
    },
    "js_extract_script": """
            const urls = new Set();
            document.querySelectorAll("div.detailmodule_image img").forEach(im => {
                let u = im.getAttribute("data-src") || im.getAttribute("src") || "";
                if (u.startsWith("//")) u = "https:" + u;
                if (/^https?:\/\//i.test(u)) urls.add(u);
            });
            return Array.from(urls);,
        """,
    "js_extract_script2": """
            const items = [];
            document.querySelectorAll("div.sku-item--image--jMUnnGA img").forEach(im => {
                let u = im.getAttribute("src") || "";
                if (u.startsWith("//")) u = "https:" + u;
                if (/^https?:\/\//i.test(u)) {
                    let title = im.getAttribute("alt") || "";
                    items.push({url: u, title: title});
                }
            });
            return items;
        """,
    "file": {
        "save_method": "detailed_page_img",
        "save_dir": "",
        "name": "DETAILED",
        "name_prefix": "",
        "min_size": 1024,
        "max_width": 4096,
        "max_height": 4096,
        "quality": 85,
        "exif": false,
    }
}