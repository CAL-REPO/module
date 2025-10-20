# ✅ Extractor 통합 및 메서드 분리 완료

## 📋 완료 작업 요약

### 1. 메서드별 크롤링 서비스 분리 (`crawl_methods.py`)

#### ✅ CrawlProductDetail
- **책임**: 상품 상세 페이지 크롤링
- **Pipeline**:
  1. Navigator로 페이지 로드
  2. Wait hook 실행 (policy 기반)
  3. Extractor로 데이터 추출
  4. Runtime context 추가
  5. 결과 반환

#### ✅ CrawlProductSearch
- **책임**: 상품 검색 결과 크롤링
- **Pipeline**:
  1. Navigator로 페이지 로드
  2. Wait hook 실행
  3. Scroll (선택사항)
  4. Extractor로 리스트 아이템 추출
  5. Runtime context 추가
  6. 결과 반환

#### ✅ CrawlMethodFactory
- **책임**: 메서드 타입에 따라 적절한 크롤링 서비스 생성
- **지원 메서드**: `product_detail`, `product_search`

---

### 2. Sync Extractor 구현 (`sync_extractor.py`)

#### ✅ SyncDOMExtractor
- **책임**: BeautifulSoup을 사용한 DOM 기반 데이터 추출
- **메서드**:
  - `extract(dom)` - 단일 아이템 추출 (상품 상세)
  - `extract_list(dom)` - 리스트 아이템 추출 (상품 검색)
- **기능**:
  - CSS selector 기반 element 추출
  - HTML, text, attributes 추출
  - Element 없을 때 graceful handling

#### ✅ SyncJSExtractor
- **책임**: JavaScript snippet 실행 결과 추출
- **메서드**:
  - `extract(dom)` - 단일 결과 추출
  - `extract_list(dom)` - 리스트 결과 추출
- **기능**:
  - policy.extractor.js_snippet 실행
  - 결과 타입 자동 처리 (dict, list, other)
  - 에러 핸들링

#### ✅ SyncExtractorFactory
- **책임**: ExtractorType에 따라 적절한 Extractor 생성
- **지원 타입**: `DOM`, `JS` (API는 미구현)

---

### 3. Crawl Adapter 리팩토링 (`crawl.py`)

#### ✅ Extractor Property 추가
```python
@property
def extractor(self):
    """Lazy extractor creation"""
    if self._extractor is None:
        from ..services.sync_extractor import SyncExtractorFactory
        factory = SyncExtractorFactory(self.adapter, self.policy)
        self._extractor = factory.create()
    return self._extractor
```

#### ✅ 메서드 브랜칭 리팩토링
**Before**:
```python
# Crawl Adapter 내부에 _crawl_product_detail(), _crawl_product_search() 직접 구현
if self.policy.method == "product_detail":
    results = self._crawl_product_detail(urls, runtime_context)
elif self.policy.method == "product_search":
    results = self._crawl_product_search(urls, runtime_context)
```

**After**:
```python
# 메서드별 서비스로 분리 + Factory 패턴
from ..services.crawl_methods import CrawlMethodFactory

crawl_service = CrawlMethodFactory.create(
    method=self.policy.method,
    navigator=self.navigator,
    extractor=self.extractor,
    policy=self.policy,
    logger=self.log
)

results = crawl_service.crawl(target_urls, runtime_context)
```

#### ✅ 기존 메서드 제거
- `_crawl_product_detail()` 제거 → `CrawlProductDetail`로 이동
- `_crawl_product_search()` 제거 → `CrawlProductSearch`로 이동

---

## 🏗️ 최종 아키텍처

```
Crawler (EntryPoint)
  └─► Crawl (Adapter)
       ├─► webdriver: FirefoxWebDriver
       ├─► adapter: SyncSeleniumAdapter
       ├─► navigator: SyncNavigator
       ├─► extractor: SyncDOMExtractor / SyncJSExtractor
       └─► run() → CrawlMethodFactory
            ├─► CrawlProductDetail (상품 상세)
            └─► CrawlProductSearch (상품 검색)
```

---

## 📊 데이터 흐름 (Product Detail)

```
1. Crawler.run(urls)
   ↓
2. Crawl.run(urls)
   ↓
   ├─► UrlAnalyzer.analyze(url) → site, method
   └─► CrawlMethodFactory.create(method)
       ↓
3. CrawlProductDetail.crawl(urls)
   ↓
   ├─► navigator.load(url)
   ├─► navigator.wait(hook, selector, timeout)
   ├─► navigator.get_dom() → dom
   └─► extractor.extract(dom) → data
       ↓
4. 결과 반환 → List[Dict]
```

---

## 💻 코드 예시

### 기본 사용법

```python
from cfg_utils import ConfigLoader
from crawl_utils.entry_point import Crawler

# ConfigLoader로 설정 로드
config = ConfigLoader("configs/loader/config_loader_crawl.yaml")
crawl_config = config.to_dict(section="crawl")

# Crawler 실행
with Crawler(crawl_config) as crawler:
    urls = ["https://aliexpress.com/item/123"]
    results = crawler.run(urls)
    
    for item in results:
        print(f"URL: {item['_url']}")
        print(f"Text: {item.get('text', 'N/A')}")
        print(f"HTML: {item.get('html', 'N/A')[:100]}")
```

### Crawl Adapter 직접 사용

```python
from crawl_utils.adapter import Crawl

crawl_config = {
    "site": "aliexpress",
    "source": {
        "method": "product_detail",
        "urls": ["https://aliexpress.com/item/123"]
    },
    "wait": {
        "hook": "css",
        "selector": ".product-title",
        "timeout_sec": 10.0,
        "condition": "presence"
    },
    "extractor": {
        "type": "dom",
        "item_selector": ".product-info"
    }
}

with Crawl(crawl_config) as crawl:
    results = crawl.run()
    print(results[0])
```

### 메서드 서비스 직접 사용

```python
from crawl_utils.services import (
    CrawlProductDetail,
    SyncNavigator,
    SyncDOMExtractor,
    SyncSeleniumAdapter
)

# Services 생성
adapter = SyncSeleniumAdapter(webdriver)
navigator = SyncNavigator(adapter, policy)
extractor = SyncDOMExtractor(adapter, policy)

# 크롤링 서비스
detail_service = CrawlProductDetail(
    navigator=navigator,
    extractor=extractor,
    policy=policy,
    logger=logger
)

# 크롤링 실행
urls = ["https://example.com/product/123"]
results = detail_service.crawl(urls, runtime_context={})
```

---

## 🎯 주요 개선사항

### 1. 관심사 분리 (Separation of Concerns)
**Before**: Crawl Adapter가 모든 메서드 로직 포함 (400+ lines)  
**After**: 메서드별 서비스로 분리 (각 100~ lines)

### 2. 단일 책임 원칙 (Single Responsibility)
- **Crawl Adapter**: URL 분석, Services 초기화, Factory 호출
- **CrawlProductDetail**: 상품 상세 크롤링 로직
- **CrawlProductSearch**: 상품 검색 크롤링 로직
- **SyncDOMExtractor**: DOM 데이터 추출
- **SyncJSExtractor**: JS snippet 실행

### 3. 확장성 (Extensibility)
**새로운 메서드 추가**:
```python
# 1. crawl_methods.py에 새로운 서비스 추가
class CrawlProductReview:
    def crawl(self, urls, runtime_context):
        # ...

# 2. Factory에 등록
class CrawlMethodFactory:
    @staticmethod
    def create(method, ...):
        if method == "product_review":
            return CrawlProductReview(...)
```

**새로운 Extractor 타입 추가**:
```python
# 1. sync_extractor.py에 새로운 Extractor 추가
class SyncAPIExtractor:
    def extract(self, dom):
        # ...

# 2. Factory에 등록
class SyncExtractorFactory:
    def create(self):
        if etype == ExtractorType.API:
            return SyncAPIExtractor(...)
```

### 4. 테스트 용이성 (Testability)
각 서비스를 독립적으로 테스트 가능:
```python
# 메서드 서비스만 테스트
def test_crawl_product_detail():
    mock_navigator = Mock()
    mock_extractor = Mock()
    
    service = CrawlProductDetail(
        navigator=mock_navigator,
        extractor=mock_extractor,
        policy=policy,
        logger=logger
    )
    
    results = service.crawl(["http://test.com"], {})
    assert len(results) == 1
```

### 5. 코드 재사용성 (Reusability)
- 메서드 서비스를 다른 Entry Point에서도 사용 가능
- Extractor를 독립적으로 사용 가능
- Navigator, Adapter를 조합하여 커스텀 파이프라인 구성 가능

---

## 📁 변경된 파일 구조

```
modules/crawl_utils/
├── adapter/
│   └── crawl.py                        # ✅ 메서드 브랜칭 리팩토링
├── services/
│   ├── crawl_methods.py                # ✅ NEW - 메서드별 크롤링 서비스
│   ├── sync_extractor.py               # ✅ NEW - Sync Extractor
│   └── __init__.py                     # ✅ 업데이트
├── entry_point/
│   └── crawler.py                      # (변경 없음)
└── docs/
    └── EXTRACTOR_INTEGRATION_COMPLETE.md  # ✅ NEW - 이 문서
```

---

## 🔍 Services 모듈 Export

```python
# modules/crawl_utils/services/__init__.py

# Sync Extractor
from .sync_extractor import (
    SyncDOMExtractor,
    SyncJSExtractor,
    SyncExtractorFactory,
)

# Crawl Methods
from .crawl_methods import (
    CrawlProductDetail,
    CrawlProductSearch,
    CrawlMethodFactory,
)

__all__ = [
    # ... (기존 exports)
    
    # Sync Extractor
    "SyncDOMExtractor",
    "SyncJSExtractor",
    "SyncExtractorFactory",
    
    # Crawl Methods
    "CrawlProductDetail",
    "CrawlProductSearch",
    "CrawlMethodFactory",
]
```

---

## ⏳ TODO - 향후 작업

### 1. BeautifulSoup 의존성 처리
**현재**: BeautifulSoup import 실패 시 graceful fallback  
**개선 필요**:
```python
# requirements.txt에 추가
beautifulsoup4==4.12.2
lxml==4.9.3  # parser
```

### 2. Extractor 기능 확장
**현재**: 기본 HTML, text, attrs만 추출  
**확장 필요**:
- 특정 필드 추출 (title, price, images 등)
- CSS selector 복수 지정
- XPath 지원
- 정규식 패턴 매칭

### 3. ConfigLoader YAML 작성
```yaml
# configs/crawl/crawl_aliexpress_detail.yaml
extractor:
  type: dom
  item_selector: ".product-main"
  fields:
    title: ".product-title::text"
    price: ".product-price::text"
    images: ".product-images img::attr(src)"
```

### 4. 실제 사이트 테스트
- AliExpress 상품 상세 크롤링
- Taobao 검색 결과 크롤링
- Extractor selector 최적화

### 5. API Extractor 구현
```python
class SyncAPIExtractor:
    """API 호출 기반 데이터 추출"""
    def extract(self, dom=None):
        endpoint = self.extractor_policy.api_endpoint
        response = requests.get(endpoint)
        return response.json()
```

---

## ✅ 완료 체크리스트

- [x] CrawlProductDetail 서비스 구현
- [x] CrawlProductSearch 서비스 구현
- [x] CrawlMethodFactory 구현
- [x] SyncDOMExtractor 구현
- [x] SyncJSExtractor 구현
- [x] SyncExtractorFactory 구현
- [x] Crawl Adapter 리팩토링
- [x] 메서드 브랜칭을 Factory 패턴으로 변경
- [x] 기존 _crawl_* 메서드 제거
- [x] services/__init__.py 업데이트
- [x] extractor property 추가
- [ ] BeautifulSoup 의존성 추가
- [ ] ConfigLoader YAML 작성
- [ ] 실제 사이트 테스트
- [ ] API Extractor 구현

---

## 🎉 완료 요약

> **✅ Extractor 통합 및 메서드 분리 완료!**
> 
> **구현된 기능:**
> - ✅ CrawlProductDetail, CrawlProductSearch 서비스
> - ✅ SyncDOMExtractor, SyncJSExtractor
> - ✅ CrawlMethodFactory, SyncExtractorFactory
> - ✅ Crawl Adapter 리팩토링
> - ✅ 메서드별 서비스로 관심사 분리
> 
> **아키텍처 개선:**
> - 단일 책임 원칙 (SRP)
> - 확장성 (새로운 메서드/Extractor 쉽게 추가)
> - 테스트 용이성 (독립적인 서비스 테스트)
> - 코드 재사용성 (서비스 조합 가능)
> 
> **다음 단계:**
> 1. ConfigLoader YAML 작성
> 2. 실제 사이트 테스트
> 3. Extractor 기능 확장

---

**완료일**: 2025-10-21  
**패턴**: Service Layer + Factory Pattern  
**상태**: ✅ **Extractor 통합 완료 - 실제 크롤링 테스트 준비 완료**
