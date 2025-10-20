# crawl_utils Config 기반 리팩토링 완료 보고서

## 📋 변경 사항 요약

### 🎯 핵심 변경: Mapping 제거 + Config 기반으로 전환

**Before (Mapping 하드코딩)**:
```python
# ❌ MethodResolver - PRESET_MAPPING 하드코딩
PRESET_MAPPING = {
    ("aliexpress", "product_detail"): "crawl__aliexpress__detail",
    ("taobao", "product_search"): "crawl__taobao__search",
}

# ❌ UrlAnalyzer - SITE_DOMAINS, METHOD_PATTERNS 하드코딩
SITE_DOMAINS = {
    "aliexpress": ["aliexpress.com"],
    "taobao": ["taobao.com"],
}
METHOD_PATTERNS = {
    "product_detail": ["/item/", "item.htm"],
    "product_search": ["/search"],
}
```

**After (Config 기반)**:
```yaml
# ✅ crawl_base.yaml - URL 패턴 설정
url_patterns:
  site_domains:
    aliexpress: ["aliexpress.com", "aliexpress.us"]
    taobao: ["taobao.com", "world.taobao.com"]
  
  method_patterns:
    product_detail: ["/item/", "item.htm"]
    product_search: ["/wholesale", "/search"]
```

```python
# ✅ UrlAnalyzer - config 받아서 사용
analyzer = UrlAnalyzer(url_patterns)

# ✅ MethodResolver - 단순 section 이름 생성
section = MethodResolver.get_section_name(site, method)
# → "crawl__aliexpress__detail"
```

---

## ✅ 수정된 파일 목록

### 1. `services/method_resolver.py` - Mapping 제거

**변경 내용**:
- ❌ `PRESET_MAPPING` 제거 (하드코딩 mapping 삭제)
- ❌ `resolve()` 메서드 제거 (ConfigLoader 사용 중복)
- ✅ `get_section_name(site, method)` - static method로 변경
- ✅ Section 이름 생성 로직: `f"crawl__{site}__{method.replace('product_', '')}"`

**Before**:
```python
PRESET_MAPPING = {
    ("aliexpress", "product_detail"): "crawl__aliexpress__detail",
}

def resolve(self, site, method):
    section = self.PRESET_MAPPING.get((site, method))
    return self.config.to_dict(section=section)
```

**After**:
```python
@staticmethod
def get_section_name(site: str, method: str) -> str:
    """Section 이름 생성"""
    method_short = method.replace("product_", "")
    return f"crawl__{site}__{method_short}"
```

---

### 2. `services/url_analyzer.py` - 하드코딩 제거

**변경 내용**:
- ❌ `SITE_DOMAINS` 하드코딩 제거
- ❌ `METHOD_PATTERNS` 하드코딩 제거
- ✅ `__init__(url_patterns)` - config 받기
- ✅ `self.site_domains` - config에서 로드
- ✅ `self.method_patterns` - config에서 로드

**Before**:
```python
class UrlAnalyzer:
    SITE_DOMAINS = {
        "aliexpress": ["aliexpress.com"],
        "taobao": ["taobao.com"],
    }
    METHOD_PATTERNS = {
        "product_detail": ["/item/"],
    }
```

**After**:
```python
class UrlAnalyzer:
    def __init__(self, url_patterns: Optional[Dict] = None):
        if url_patterns is None:
            url_patterns = {"site_domains": {}, "method_patterns": {}}
        
        self.site_domains = url_patterns.get("site_domains", {})
        self.method_patterns = url_patterns.get("method_patterns", {})
    
    def _extract_site(self, domain):
        for site, domains in self.site_domains.items():
            if any(d in domain for d in domains):
                return site
        return "unknown"
    
    def _extract_method(self, path, url):
        detail_patterns = self.method_patterns.get("product_detail", [])
        for pattern in detail_patterns:
            if pattern in path or pattern in url:
                return "product_detail"
        
        search_patterns = self.method_patterns.get("product_search", [])
        for pattern in search_patterns:
            if pattern in path or pattern in url:
                return "product_search"
        
        return "product_detail"
```

---

### 3. `core/policy.py` - url_patterns 필드 추가

**변경 내용**:
- ✅ `CrawlPolicy`에 `url_patterns` 필드 추가
- ✅ Optional 타입: `Optional[Dict[str, Dict[str, List[str]]]]`
- ✅ UrlAnalyzer에서 사용할 패턴 설정

**코드**:
```python
class CrawlPolicy(BaseModel):
    """Crawl Adapter Policy"""
    
    # URL 패턴 설정 (UrlAnalyzer에서 사용)
    url_patterns: Optional[Dict[str, Dict[str, List[str]]]] = Field(
        None,
        description="URL pattern configuration for UrlAnalyzer (site_domains, method_patterns)"
    )
```

---

### 4. `adapter/crawl.py` - UrlAnalyzer에 config 전달

**변경 내용**:
- ✅ `policy.url_patterns` 추출
- ✅ UrlAnalyzer 생성 시 config 전달
- ❌ MethodResolver 인스턴스 제거 (static method 사용)

**Before**:
```python
self.url_analyzer = UrlAnalyzer()
self.method_resolver = MethodResolver()
```

**After**:
```python
# URL 분석 서비스 (config에서 url_patterns 추출)
url_patterns = None
if hasattr(self.policy, 'url_patterns') and self.policy.url_patterns:
    url_patterns = self.policy.url_patterns
self.url_analyzer = UrlAnalyzer(url_patterns)
```

---

### 5. `configs/crawl_base.yaml` - 기본 설정 파일 생성

**새로 추가**:
- ✅ `url_patterns` 섹션 - site_domains, method_patterns
- ✅ 모든 필수 설정 포함 (navigation, scroll, extractor, wait 등)
- ✅ 주석으로 상세 설명

**구조**:
```yaml
url_patterns:
  site_domains:
    aliexpress: ["aliexpress.com", "aliexpress.us", "aliexpress.ru"]
    taobao: ["taobao.com", "world.taobao.com", "item.taobao.com"]
    1688: ["1688.com", "detail.1688.com"]
  
  method_patterns:
    product_detail:
      - "/item/"
      - "item.htm"
      - "/product/"
      - "detail.html"
    
    product_search:
      - "/wholesale"
      - "/search"
      - "/category"
      - "s.taobao.com"

source:
  urls: []
  method: "product_detail"

site: ""    # auto-detected
method: ""  # from source.method

navigation:
  base_url: "https://www.aliexpress.com"
  page_param: "page"
  start_page: 1
  max_pages: 1

# ... (scroll, extractor, wait, etc.)
```

---

### 6. 테스트 스크립트 업데이트 (`test_crawl_adapter.py`)

**변경 내용**:
- ✅ UrlAnalyzer 테스트 - config 전달
- ✅ MethodResolver 테스트 - static method 사용
- ✅ 통합 테스트 - config 기반 흐름

**Before**:
```python
analyzer = UrlAnalyzer()  # ❌ 하드코딩 사용
resolver = MethodResolver()
section = resolver.get_section_name(site, method)
```

**After**:
```python
url_patterns = {
    "site_domains": {"aliexpress": [...]},
    "method_patterns": {"product_detail": [...]}
}
analyzer = UrlAnalyzer(url_patterns)  # ✅ config 전달

section = MethodResolver.get_section_name(site, method)  # ✅ static method
```

---

## 🎯 사용 예시

### 1. ConfigLoader와 함께 사용 (권장)

```python
from cfg_utils import ConfigLoader
from crawl_utils.adapter import Crawl

# ConfigLoader로 설정 로드 (url_patterns 포함)
config = ConfigLoader(config_loader_cfg_path="configs/loader/config_loader_crawl.yaml")
crawl_config = config.to_dict(section="crawl")

# crawl_config에 url_patterns 포함됨:
# {
#   "url_patterns": {
#     "site_domains": {...},
#     "method_patterns": {...}
#   },
#   ...
# }

# Crawl Adapter 생성 (url_patterns 자동 전달)
crawl = Crawl(crawl_config)

# URLs 크롤링 (자동 site/method 감지)
urls = ["https://aliexpress.com/item/123"]
results = crawl.run(urls)
```

### 2. YAML 파일 직접 사용

```python
from crawl_utils.adapter import Crawl

# YAML 파일에서 직접 로드 (url_patterns 포함)
crawl = Crawl("modules/crawl_utils/configs/crawl_base.yaml")

# URLs 크롤링
urls = ["https://aliexpress.com/item/123"]
results = crawl.run(urls)
```

### 3. UrlAnalyzer 단독 사용

```python
from crawl_utils.services import UrlAnalyzer

# URL 패턴 설정
url_patterns = {
    "site_domains": {
        "aliexpress": ["aliexpress.com"],
        "taobao": ["taobao.com"]
    },
    "method_patterns": {
        "product_detail": ["/item/"],
        "product_search": ["/search"]
    }
}

# UrlAnalyzer 생성
analyzer = UrlAnalyzer(url_patterns)

# URL 분석
site, method = analyzer.analyze("https://aliexpress.com/item/123")
print(site, method)  # aliexpress product_detail
```

### 4. Section 이름 생성

```python
from crawl_utils.services import MethodResolver

# Section 이름 생성 (static method)
section = MethodResolver.get_section_name("aliexpress", "product_detail")
print(section)  # crawl__aliexpress__detail

# ConfigLoader에서 해당 section 추출
config = ConfigLoader("config_loader_crawl.yaml")
preset = config.to_dict(section=section)
```

---

## 🧪 테스트 결과

```
======================================================================
[Test 1] UrlAnalyzer - URL 분석 및 site/method 감지 (Config 기반)
======================================================================
URL: https://www.aliexpress.com/item/123456.html
  → Site: aliexpress, Method: product_detail

URL: https://aliexpress.com/wholesale?SearchText=laptop
  → Site: aliexpress, Method: product_search

URL: https://item.taobao.com/item.htm?id=123456
  → Site: taobao, Method: product_detail

URL: https://s.taobao.com/search?q=laptop
  → Site: taobao, Method: product_search


======================================================================
[Test 2] MethodResolver - Section 이름 생성
======================================================================
Site: aliexpress, Method: product_detail
  → Section: crawl__aliexpress__detail

Site: aliexpress, Method: product_search
  → Section: crawl__aliexpress__search

Site: taobao, Method: product_detail
  → Section: crawl__taobao__detail

Site: taobao, Method: product_search
  → Section: crawl__taobao__search


======================================================================
✅ All tests passed!
======================================================================
```

---

## 📊 변경 전후 비교

### Before (Mapping 하드코딩)

**문제점**:
- ❌ PRESET_MAPPING 하드코딩 - 새로운 site/method 추가 시 코드 수정 필요
- ❌ SITE_DOMAINS 하드코딩 - 도메인 추가 시 코드 수정 필요
- ❌ METHOD_PATTERNS 하드코딩 - 패턴 추가 시 코드 수정 필요
- ❌ 설정 변경 시 코드 재배포 필요

**코드**:
```python
# ❌ 하드코딩 - 변경 시 코드 수정 필요
PRESET_MAPPING = {
    ("aliexpress", "product_detail"): "crawl__aliexpress__detail",
}
SITE_DOMAINS = {"aliexpress": ["aliexpress.com"]}
METHOD_PATTERNS = {"product_detail": ["/item/"]}
```

---

### After (Config 기반)

**장점**:
- ✅ YAML 파일로 설정 관리 - 코드 수정 없이 설정 변경
- ✅ 새로운 site 추가 - yaml에 도메인만 추가
- ✅ 새로운 method 추가 - yaml에 패턴만 추가
- ✅ ConfigLoader 통합 - 통합 설정 관리
- ✅ 설정 변경 시 YAML만 수정, 코드 재배포 불필요

**코드**:
```yaml
# ✅ YAML 설정 - 코드 수정 없이 설정 변경
url_patterns:
  site_domains:
    aliexpress: ["aliexpress.com", "aliexpress.us"]
    taobao: ["taobao.com"]
    # 새로운 사이트 추가 - YAML만 수정
    1688: ["1688.com"]
  
  method_patterns:
    product_detail: ["/item/", "item.htm"]
    product_search: ["/search"]
    # 새로운 메서드 추가 - YAML만 수정
```

---

## 🎯 핵심 개선 사항

### 1. Mapping 제거
- ✅ MethodResolver의 PRESET_MAPPING 제거
- ✅ UrlAnalyzer의 SITE_DOMAINS, METHOD_PATTERNS 제거
- ✅ Section 이름 동적 생성: `crawl__{site}__{method}`

### 2. Config 기반 전환
- ✅ url_patterns를 crawl_base.yaml로 이동
- ✅ UrlAnalyzer가 config 받아서 사용
- ✅ CrawlPolicy에 url_patterns 필드 추가

### 3. 확장성 향상
- ✅ 새로운 사이트 추가 - YAML만 수정
- ✅ 새로운 메서드 추가 - YAML만 수정
- ✅ 도메인/패턴 수정 - YAML만 수정
- ✅ 코드 재배포 불필요

### 4. ConfigLoader 통합
- ✅ config_loader_crawl.yaml로 모든 설정 통합 관리
- ✅ url_patterns, navigation, scroll 등 모두 YAML로 관리
- ✅ section 기반 preset 분리

---

## 📚 다음 단계

### 1. config_loader_crawl.yaml 작성

```yaml
name: "config_loader_crawl"

cashop_paths:
  enabled: true
  env_var: "CASHOP_PATHS"

source:
  # Base 설정 (url_patterns 포함)
  - src: ["{{configs_dir}}/crawl/crawl_base.yaml", "crawl"]
    yaml_parser:
      enable_env: true
  
  # AliExpress preset
  - src: ["{{configs_dir}}/crawl/crawl_aliexpress_detail.yaml", "crawl__aliexpress__detail"]
    yaml_parser:
      enable_env: true
  
  - src: ["{{configs_dir}}/crawl/crawl_aliexpress_search.yaml", "crawl__aliexpress__search"]
    yaml_parser:
      enable_env: true

merge:
  strategy: "deep"
  list_handling: "replace"
```

### 2. Site별 Preset 파일 작성

```yaml
# configs/crawl/crawl_aliexpress_detail.yaml
site: "aliexpress"
method: "product_detail"

navigation:
  base_url: "https://www.aliexpress.com"
  max_pages: 1

wait:
  timeout_sec: 25.0

extractor:
  js_snippet: |
    return {
      images: [...document.querySelectorAll('.magnifier-image')].map(i => i.src),
      title: document.querySelector('.product-title-text').textContent
    };
```

### 3. 실제 WebDriver 통합

```python
# adapter/crawl.py
@property
def webdriver(self) -> BaseWebDriver:
    if self._webdriver is None:
        from ..provider import create_webdriver
        self._webdriver = create_webdriver(self.policy.webdriver)
    return self._webdriver
```

---

**완료일**: 2024-01-XX  
**작성자**: GitHub Copilot  
**검수**: 사용자

## ✅ 핵심 요약

> **Mapping 하드코딩 제거 완료!**  
> - MethodResolver: PRESET_MAPPING 삭제 → Section 이름 동적 생성  
> - UrlAnalyzer: 하드코딩 삭제 → crawl_base.yaml에서 로드  
> - CrawlPolicy: url_patterns 필드 추가  
> - Config 기반으로 전환 완료! 🎉
