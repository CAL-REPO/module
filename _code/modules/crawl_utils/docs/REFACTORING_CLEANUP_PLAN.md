# crawl_utils 구조 정리 방향성 분석

## 🔍 현재 상황 분석

### 1. PresetManager 도입으로 불필요해진 컴포넌트

#### ❌ 삭제 대상: services/url_analyzer.py
**이유:**
- PresetManager의 `analyze_url()`이 완전히 대체
- DOMAIN_MAPPING (presets/domains.py)로 site+region 추출
- METHOD_PATTERNS (presets/methods.py)로 method 추출
- 더 이상 사용되지 않음 (import만 __init__.py에 존재)

**확인:**
```bash
# 실제 사용처 없음
grep -r "UrlAnalyzer" --include="*.py" | grep -v "__init__.py" | grep -v "url_analyzer.py"
```

#### ❌ 삭제 대상: services/method_resolver.py
**이유:**
- PresetManager가 URL 패턴 매칭으로 method 해석
- METHOD_PATTERNS가 더 직관적이고 확장 가능
- 사용되지 않음

#### ❌ 삭제 대상: CrawlSourcePolicy (core/policy.py)
**이유:**
- CrawlPolicy에서 `source: CrawlSourcePolicy` 필드 사용
- 하지만 PresetManager 패턴에서는 URL을 run()에서 직접 전달
- `source.urls`, `source.method` 필드가 불필요
- CrawlPolicy에 `site`, `method` 필드가 직접 존재

**변경 방향:**
```python
# Before (불필요한 중첩)
class CrawlPolicy:
    source: CrawlSourcePolicy  # urls, method
    site: str
    method: str

# After (간소화)
class CrawlPolicy:
    site: str     # PresetManager.analyze_url()에서 자동 설정
    method: str   # PresetManager.analyze_url()에서 자동 설정
    # source 필드 제거
```

#### ❌ 삭제 대상: url_patterns 필드 (CrawlPolicy)
**이유:**
```python
class CrawlPolicy:
    url_patterns: Optional[Dict[str, Dict[str, List[str]]]] = None  # UrlAnalyzer용
```
- UrlAnalyzer가 삭제되면 불필요
- PresetManager의 presets/domains.py, presets/methods.py로 대체

---

### 2. 과거 Alias 패턴 정리

#### services/__init__.py 정리
**현재 문제:**
```python
# Async/Sync 혼재 + 하위 호환성 alias 과다
from .adapter import (
    AsyncSeleniumAdapter,
    SyncSeleniumAdapter,
    SeleniumAdapter,  # Alias for Async
)

from .navigator import (
    AsyncNavigator,
    SyncNavigator,
    SeleniumNavigator,  # = AsyncNavigator (deprecated)
    Navigator,          # = AsyncNavigator (deprecated)
)
```

**정리 방향:**
```python
# ✅ WebCrawl은 Sync만 사용하므로 Async 제거
from .adapter import SyncSeleniumAdapter
from .navigator import SyncNavigator
from .sync_extractor import SyncJSExtractor
# from .normalizer import DataNormalizer  # Rule 기반 (사용 안 함)
from .smart_normalizer import SmartNormalizer  # 자동 타입 추론 (사용)
from .saver import SyncFileSaver

# Async는 완전히 제거하거나 별도 모듈로 분리
```

---

### 3. 구조화 개선 방향

#### A. PresetManager 중심 구조로 통일

**현재:**
```
crawl_utils/
├── adapter/
│   ├── crawl.py            # WebCrawl
│   └── webdriver_manager.py
├── presets/                # NEW (잘 설계됨)
│   ├── __init__.py         # PresetManager
│   ├── domains.py
│   ├── methods.py
│   ├── sites/
│   └── webdrivers/
├── services/               # 혼재 상태 (정리 필요)
│   ├── adapter.py          # Async + Sync
│   ├── navigator.py        # Async + Sync
│   ├── sync_extractor.py   # Sync only
│   ├── extractor.py        # Async only
│   ├── url_analyzer.py     # ❌ 불필요
│   ├── method_resolver.py  # ❌ 불필요
│   └── ...
└── core/
    └── policy.py           # CrawlSourcePolicy ❌ 불필요
```

**개선 후:**
```
crawl_utils/
├── adapter/
│   ├── crawl.py            # WebCrawl (Sync only)
│   └── webdriver_manager.py
├── presets/                # URL 분석 + 정책 선택
│   ├── __init__.py         # PresetManager
│   ├── domains.py          # DOMAIN_MAPPING
│   ├── methods.py          # METHOD_PATTERNS
│   ├── sites/              # Site별 CrawlPolicy
│   └── webdrivers/         # Region별 Override
├── services/               # Sync only (WebCrawl 전용)
│   ├── adapter.py          # SyncSeleniumAdapter만
│   ├── navigator.py        # SyncNavigator만
│   ├── sync_extractor.py   # SyncJSExtractor
│   ├── smart_normalizer.py # SmartNormalizer
│   └── saver.py            # SyncFileSaver
└── core/
    └── policy.py           # CrawlPolicy (간소화)
```

#### B. Policy 간소화

**CrawlPolicy 리팩토링:**
```python
class CrawlPolicy(BaseModel):
    """Crawl Policy - PresetManager 기반 간소화"""
    
    # 1. 식별자 (PresetManager가 자동 설정)
    name: str = "crawl"
    site: str = ""          # e.g., "aliexpress", "taobao"
    method: str = ""        # e.g., "detail", "search"
    
    # 2. 크롤링 동작 (preset에서 설정)
    navigation: Optional[NavigationPolicy] = None  # 페이지네이션 (search 전용)
    scroll: Optional[ScrollPolicy] = None
    wait: Optional[WaitPolicy] = None
    extractor: ExtractorPolicy                     # JS snippet
    
    # 3. 후처리 (PostProcessor)
    post_processor: Optional[PostProcessorPolicy] = None
    
    # 4. HTTP 세션
    http_session: Optional[HttpSessionPolicy] = None
    
    # 5. 실행 설정
    execution_mode: ExecutionMode = "sync"
    concurrency: int = 1
    retries: int = 3
    retry_backoff_sec: float = 2.0
    
    # 6. 로깅
    log: Optional[Dict[str, Any]] = None
    
    # ❌ 제거할 필드들
    # source: CrawlSourcePolicy  # URLs는 run()에서 받음
    # url_patterns: Dict[...]    # PresetManager가 관리
```

#### C. WebCrawl 사용 패턴 표준화

```python
# 1. ConfigLoader로 webdriver_manager section 추출
from cfg_utils import ConfigLoader
config = ConfigLoader(config_loader_cfg_path="configs/loader/config_loader_crawl.yaml")
webdriver_config = config.to_dict(section="webdriver_manager")

# 2. WebCrawl 초기화 (ImageLoad 패턴)
from crawl_utils.adapter import WebCrawl
crawl = WebCrawl(cfg_like=webdriver_config)

# 3. run()에서 URL 전달 (source 역할)
results = crawl.run(
    urls=["https://aliexpress.com/item/123.html"],
    provider="firefox"
)

# 4. PresetManager가 자동으로:
#    - URL 분석 → (site, method, region)
#    - 정책 선택 → presets/sites/aliexpress_detail.py
#    - Override 적용 → presets/webdrivers/worldwide.py
```

---

### 4. 삭제/유지 판단

#### 🗑️ 즉시 삭제 가능
1. `services/url_analyzer.py` - PresetManager로 대체
2. `services/method_resolver.py` - PresetManager로 대체
3. `core/policy.py`의 `CrawlSourcePolicy` - source 필드 제거
4. `core/policy.py`의 `url_patterns` 필드 - PresetManager가 관리

#### 🔧 리팩토링 필요
1. `services/__init__.py` - Async 제거, Sync만 export
2. `services/adapter.py` - SyncSeleniumAdapter만 유지
3. `services/navigator.py` - SyncNavigator만 유지
4. `services/extractor.py` - Async 제거 또는 분리

#### ✅ 유지
1. `presets/` 전체 - 핵심 구조
2. `services/sync_extractor.py` - WebCrawl이 사용
3. `services/smart_normalizer.py` - PostProcessor가 사용
4. `services/saver.py` - PostProcessor가 사용
5. `adapter/crawl.py` - WebCrawl (ImageLoad 패턴)
6. `adapter/webdriver_manager.py` - WebDriver 관리

---

### 5. 우선순위 정리 순서

**Phase 1: 불필요한 컴포넌트 삭제**
1. `services/url_analyzer.py` 삭제
2. `services/method_resolver.py` 삭제
3. `__init__.py`에서 import 제거
4. `CrawlSourcePolicy` 제거

**Phase 2: Policy 간소화**
1. `CrawlPolicy`에서 `source` 필드 제거
2. `CrawlPolicy`에서 `url_patterns` 필드 제거
3. PresetManager 기반 동작 검증

**Phase 3: Async/Sync 정리**
1. `services/__init__.py`에서 Async 관련 export 제거
2. Async 컴포넌트를 별도 모듈로 분리 또는 완전 삭제
3. WebCrawl이 사용하는 Sync 컴포넌트만 남김

**Phase 4: 문서화**
1. README 업데이트 (PresetManager 중심)
2. 각 preset 파일 주석 개선
3. 사용 예시 통일

---

## 📋 최종 구조 (목표)

```
crawl_utils/
├── adapter/
│   ├── __init__.py         # WebCrawl, WebDriverManager
│   ├── crawl.py            # WebCrawl (Sync, ImageLoad 패턴)
│   └── webdriver_manager.py
│
├── presets/                # URL 분석 + 정책 관리
│   ├── __init__.py         # PresetManager
│   ├── domains.py          # DOMAIN_MAPPING (site → region)
│   ├── methods.py          # METHOD_PATTERNS (URL → method)
│   ├── sites/              # Site별 CrawlPolicy
│   │   ├── aliexpress_detail.py
│   │   └── taobao_detail.py
│   └── webdrivers/         # Region별 WebDriver Override
│       ├── china.py
│       └── worldwide.py
│
├── services/               # Sync Services only
│   ├── __init__.py         # Sync exports
│   ├── adapter.py          # SyncSeleniumAdapter
│   ├── navigator.py        # SyncNavigator
│   ├── sync_extractor.py   # SyncJSExtractor
│   ├── smart_normalizer.py # SmartNormalizer
│   └── saver.py            # SyncFileSaver
│
├── provider/               # WebDriver Providers
│   ├── policy.py           # WebDriverManagerPolicy
│   └── firefox.py          # FirefoxWebDriver
│
├── core/
│   ├── policy.py           # CrawlPolicy (간소화)
│   └── models.py           # NormalizedItem, etc.
│
├── entry_point/
│   └── crawler.py          # Crawler (WebCrawl wrapper)
│
└── __init__.py             # Public API
```

**핵심 원칙:**
1. **PresetManager 중심**: URL → (site, method, region) → 정책 선택
2. **ImageLoad 패턴**: WebCrawl이 cfg_like로 WebDriverManagerPolicy 로드
3. **Sync only**: WebCrawl은 동기 실행만 지원
4. **Policy 간소화**: source, url_patterns 제거, site+method 직접 관리
5. **불필요한 컴포넌트 제거**: UrlAnalyzer, MethodResolver 삭제
