# 🔍 crawl_utils Services 분석 보고서

## 📊 기존 vs 현재 Services 상세 비교

### 1. URL 분석 서비스 비교

#### A. 기존: UrlAnalyzer (services/url_analyzer.py)

**구조:**
```python
class UrlAnalyzer:
    def __init__(self, url_patterns: Dict):
        self.site_domains = url_patterns.get("site_domains", {})
        self.method_patterns = url_patterns.get("method_patterns", {})
    
    def analyze(self, url: str) -> Tuple[str, str]:
        return (site, method)  # 2-tuple 반환
```

**특징:**
- **설정 기반**: ConfigLoader에서 url_patterns 섹션을 주입받음
- **2-tuple 반환**: `(site, method)` 만 반환 (region 없음)
- **유연한 초기화**: url_patterns=None이면 빈 딕셔너리 사용
- **is_valid_url()**: URL 유효성 검증 메서드 포함

**장점:**
✅ 설정을 외부에서 주입받아 유연함 (YAML 수정만으로 변경 가능)
✅ is_valid_url() 같은 유틸리티 메서드 제공
✅ ConfigLoader와 독립적으로 사용 가능

**단점:**
❌ Region 정보 누락 (site만 반환, region은 별도 로직 필요)
❌ method 패턴 매칭이 단순 (substring 검색만)
❌ unknown 처리 로직이 약함

---

#### B. 현재: PresetManager.analyze_url() (presets/__init__.py)

**구조:**
```python
class PresetManager:
    def __init__(self):
        self.domain_mapping = DOMAIN_MAPPING      # presets/domains.py
        self.method_patterns = METHOD_PATTERNS    # presets/methods.py
    
    def analyze_url(self, url: str) -> Tuple[str, str, str]:
        return (site, method, region)  # 3-tuple 반환
```

**특징:**
- **Preset 기반**: Python dict로 하드코딩 (domains.py, methods.py)
- **3-tuple 반환**: `(site, method, region)` - region 정보 포함!
- **ValueError raise**: 매칭 실패 시 에러 발생 (unknown 처리 없음)
- **site + region 동시 추출**: DOMAIN_MAPPING에서 한 번에 추출

**장점:**
✅ **Region 정보 포함** - WebDriver override에 필수
✅ Python dict로 관리 - 타입 안정성, IDE 지원
✅ Site와 region을 한 번에 추출 - 효율적
✅ 명확한 실패 처리 - ValueError로 즉시 인지

**단점:**
❌ 설정이 하드코딩 (YAML 수정 불가)
❌ is_valid_url() 같은 유틸리티 없음
❌ 매칭 실패 시 unknown 대신 에러 발생

---

### 2. Method 해석 서비스 비교

#### A. 기존: MethodResolver (services/method_resolver.py)

**구조:**
```python
class MethodResolver:
    def __init__(self, config: ConfigLoader):
        self.config = config
    
    def resolve(self, site: str, method: str) -> Dict[str, Any]:
        section_name = f"crawl__{site}__{method_short}"
        return self.config.to_dict(section=section_name)
```

**특징:**
- **ConfigLoader 의존**: section 이름으로 설정 추출
- **Section 이름 규칙**: `crawl__aliexpress__detail` 형식
- **동적 로딩**: has_section(), list_sections() 제공
- **default_section**: fallback 지원

**장점:**
✅ ConfigLoader와 긴밀한 통합
✅ Section 존재 여부 확인 가능
✅ YAML 수정만으로 정책 변경 가능
✅ default_section으로 fallback 지원

**단점:**
❌ ConfigLoader 필수 의존성
❌ Section 이름 규칙이 경직됨 (crawl__{site}__{method})
❌ 실행 시점에 정책 로딩 (느릴 수 있음)

---

#### B. 현재: PresetManager.get_crawl_policy() (presets/__init__.py)

**구조:**
```python
class PresetManager:
    def __init__(self):
        self.crawl_policies = {
            ("aliexpress", "detail"): ALIEXPRESS_DETAIL_POLICY,
            ("taobao", "detail"): TAOBAO_DETAIL_POLICY,
        }
    
    def get_crawl_policy(self, site: str, method: str) -> Optional[Dict[str, Any]]:
        return self.crawl_policies.get((site, method))
```

**특징:**
- **Dict 기반 레지스트리**: (site, method) tuple을 key로 사용
- **Python 모듈 import**: presets/sites/*.py에서 정책 로드
- **None 반환**: 없으면 None (에러 발생 안 함)
- **초기화 시점 로딩**: __init__에서 모든 정책 로드

**장점:**
✅ O(1) 조회 속도 (dict lookup)
✅ Python dict로 타입 안정성
✅ presets/sites/ 디렉토리로 정책 구조화
✅ Import 시점에 syntax 에러 발견

**단점:**
❌ 동적 정책 추가 불가 (재시작 필요)
❌ YAML로 정책 관리 불가
❌ None 반환 시 에러 처리 필요

---

### 3. WebDriver Override 비교

#### A. 기존: 없음 (ConfigLoader만 사용)

**문제점:**
- Region별 WebDriver 설정 변경을 위해 별도 YAML 파일 필요
- China/Global 구분 없이 단일 설정만 가능
- Override 개념 없음

---

#### B. 현재: PresetManager.get_webdriver_override()

**구조:**
```python
class PresetManager:
    def __init__(self):
        self.webdriver_overrides = {
            "china": WEBDRIVER_CHINA,      # presets/webdrivers/china.py
            "global": WEBDRIVER_GLOBAL,    # presets/webdrivers/worldwide.py
        }
    
    def get_webdriver_override(self, region: str, provider: str) -> Optional[Dict]:
        override_dict = self.webdriver_overrides.get(region)
        return override_dict.get(provider) if override_dict else None
```

**특징:**
- **Region 기반**: china/global 구분
- **Provider 별 설정**: firefox/chrome 각각 override
- **기본값 + Override 병합**: WebCrawl에서 policy.model_dump() + override

**장점:**
✅ Region별 WebDriver 설정 분리 (china=중국어, global=영어)
✅ Profile path, accept-languages 등 세밀한 제어
✅ 기본값 유지하면서 일부만 override

**단점:**
❌ 하드코딩 (YAML 불가)

---

## 🔄 Services 사용 현황 분석

### WebCrawl Adapter가 사용하는 Services

```python
# crawl_utils/adapter/crawl.py
from ..services.adapter import SyncSeleniumAdapter      # ✅ 사용 중
from ..services.navigator import SyncNavigator          # ✅ 사용 중
from ..services.sync_extractor import SyncJSExtractor   # ✅ 사용 중

# PostProcessor에서 사용 (미래)
from ..services.smart_normalizer import SmartNormalizer # ⏳ 예정
from ..services.saver import SyncFileSaver              # ⏳ 예정
```

### 사용하지 않는 Services

```python
# ❌ 전혀 사용 안 함
from ..services.url_analyzer import UrlAnalyzer         # PresetManager로 대체
from ..services.method_resolver import MethodResolver   # PresetManager로 대체
from ..services.normalizer import DataNormalizer        # SmartNormalizer 사용

# ❌ Async 버전 (WebCrawl은 Sync만)
from ..services.adapter import AsyncSeleniumAdapter
from ..services.navigator import AsyncNavigator
from ..services.extractor import AsyncJSExtractor, AsyncDOMExtractor
from ..services.fetcher import AsyncHTTPFetcher
from ..services.saver import AsyncFileSaver

# ⚠️ Alias (혼란 야기)
SeleniumAdapter = AsyncSeleniumAdapter
Navigator = AsyncNavigator
ExtractorFactory = AsyncExtractorFactory
```

---

## 🏗️ Async/Sync 확장 가능 설계 제안

### 현재 문제점

1. **Async/Sync 혼재**: services/__init__.py에 모두 export
2. **Alias 과다**: SeleniumAdapter, Navigator 등 3-4개 이름으로 같은 것 지칭
3. **WebCrawl은 Sync만 사용**: Async 불필요

### 제안: Interface 기반 분리

#### A. Core Interface 정의 (core/interfaces.py)

```python
# core/interfaces.py
from typing import Protocol, Tuple, Any, Dict, Optional

class BrowserController(Protocol):
    """Browser 제어 인터페이스 (Async/Sync 공통)"""
    def get(self, url: str) -> Any: ...
    def scroll_bottom(self, step: int, delay: float, max_scrolls: int) -> Any: ...
    def wait_css(self, selector: str, timeout: float, visible: bool) -> Any: ...
    def execute_js(self, script: str) -> Any: ...
    def get_dom(self) -> str: ...
    def quit(self) -> Any: ...

class Navigator(Protocol):
    """Navigator 인터페이스 (Async/Sync 공통)"""
    def load(self, base_url: str) -> Any: ...
    def scroll(self, strategy: str, max_scrolls: int, pause_sec: float) -> Any: ...
    def wait(self, hook: str, selector: str, timeout: float, condition: str) -> Any: ...

class Extractor(Protocol):
    """Extractor 인터페이스 (Async/Sync 공통)"""
    def extract(self) -> Any: ...

class UrlAnalyzer(Protocol):
    """URL 분석 인터페이스"""
    def analyze_url(self, url: str) -> Tuple[str, str, str]: ...

class PolicyResolver(Protocol):
    """정책 해석 인터페이스"""
    def get_crawl_policy(self, site: str, method: str) -> Optional[Dict[str, Any]]: ...
    def get_webdriver_override(self, region: str, provider: str) -> Optional[Dict[str, Any]]: ...
```

#### B. Services 재구조화

```
crawl_utils/
├── core/
│   └── interfaces.py           # Protocol 정의
│
├── services/
│   ├── sync/                   # Sync 전용
│   │   ├── __init__.py
│   │   ├── adapter.py          # SyncSeleniumAdapter
│   │   ├── navigator.py        # SyncNavigator
│   │   ├── extractor.py        # SyncJSExtractor
│   │   ├── normalizer.py       # SmartNormalizer
│   │   └── saver.py            # SyncFileSaver
│   │
│   ├── async_/                 # Async 전용 (미래)
│   │   ├── __init__.py
│   │   ├── adapter.py          # AsyncSeleniumAdapter
│   │   ├── navigator.py        # AsyncNavigator
│   │   └── extractor.py        # AsyncJSExtractor
│   │
│   └── __init__.py             # 통합 export (하위 호환성)
│
└── adapter/
    ├── crawl.py                # WebCrawl (Sync)
    └── async_crawl.py          # AsyncWebCrawl (미래)
```

#### C. WebCrawl 구조 (Generic 지원)

```python
# adapter/crawl.py
from typing import TypeVar, Generic
from ..core.interfaces import BrowserController, Navigator, Extractor, UrlAnalyzer, PolicyResolver

# 현재: Sync 전용
from ..services.sync import SyncSeleniumAdapter, SyncNavigator, SyncJSExtractor

class WebCrawl:
    """WebCrawl Adapter (Sync version)"""
    
    def __init__(
        self,
        cfg_like: ...,
        preset_manager: PolicyResolver,  # Interface 사용
        log_manager: ...,
    ):
        self.policy = self._load_config(cfg_like)
        self.preset_manager = preset_manager
    
    def _execute(self, url: str, policy: CrawlPolicy, wd_config: Dict) -> Dict:
        # Sync services 사용
        wd_manager = WebDriverManager(wd_config)
        wd_manager.start()
        
        adapter: BrowserController = SyncSeleniumAdapter(wd_manager._webdriver)
        navigator: Navigator = SyncNavigator(adapter, policy)
        extractor: Extractor = SyncJSExtractor(adapter, policy)
        
        navigator.load(url)
        if policy.scroll:
            navigator.scroll(...)
        data = extractor.extract()
        
        return {"data": data, "success": True}


# adapter/async_crawl.py (미래 확장)
from ..services.async_ import AsyncSeleniumAdapter, AsyncNavigator, AsyncJSExtractor

class AsyncWebCrawl:
    """WebCrawl Adapter (Async version)"""
    
    async def _execute(self, url: str, policy: CrawlPolicy, wd_config: Dict) -> Dict:
        # Async services 사용
        wd_manager = WebDriverManager(wd_config)
        await wd_manager.start()
        
        adapter: BrowserController = AsyncSeleniumAdapter(wd_manager._webdriver)
        navigator: Navigator = AsyncNavigator(adapter, policy)
        extractor: Extractor = AsyncJSExtractor(adapter, policy)
        
        await navigator.load(url)
        if policy.scroll:
            await navigator.scroll(...)
        data = await extractor.extract()
        
        return {"data": data, "success": True}
```

---

## 📋 최종 비교 요약표

| 항목 | 기존 (UrlAnalyzer + MethodResolver) | 현재 (PresetManager) |
|------|-------------------------------------|----------------------|
| **URL 분석** | `(site, method)` 2-tuple | `(site, method, region)` 3-tuple ✅ |
| **설정 방식** | YAML (ConfigLoader) | Python dict (하드코딩) |
| **유연성** | 높음 (YAML 수정만) | 낮음 (코드 수정 필요) |
| **타입 안정성** | 낮음 (런타임 dict) | 높음 (Python import) ✅ |
| **조회 속도** | O(n) section 탐색 | O(1) dict lookup ✅ |
| **Region 지원** | 없음 (별도 로직) | 내장 ✅ |
| **WebDriver Override** | 없음 | 있음 ✅ |
| **Fallback** | default_section 지원 | None 반환 (수동 처리) |
| **동적 추가** | 가능 (YAML 추가) | 불가 (재시작 필요) |

---

## 🎯 권장 방향

### Phase 1: 즉시 삭제 가능 (안전)
✅ **UrlAnalyzer**: PresetManager.analyze_url()이 완전 대체 + region 지원
✅ **MethodResolver**: PresetManager.get_crawl_policy()가 더 빠르고 간단
✅ **Async Services**: WebCrawl은 Sync만 사용

### Phase 2: 구조 개선 (중기)
📐 **Interface 기반 설계**: Protocol로 Async/Sync 공통 인터페이스 정의
📂 **services/ 재구조화**: sync/와 async_/ 분리
🔄 **Generic WebCrawl**: 미래 AsyncWebCrawl 확장 대비

### Phase 3: 하이브리드 접근 (장기)
🔀 **PresetManager + ConfigLoader**: Python dict (기본) + YAML override (선택)
```python
# presets/sites/aliexpress_detail.py
ALIEXPRESS_DETAIL_POLICY = {
    "site": "aliexpress",
    "method": "detail",
    # ... 기본값
}

# configs/sites/aliexpress_detail_override.yaml (선택적)
scroll:
  max_scrolls: 20  # 기본값 15 → 20으로 override

# PresetManager에서 병합
base = ALIEXPRESS_DETAIL_POLICY.copy()
if override_yaml_exists:
    base.update(load_yaml("aliexpress_detail_override.yaml"))
```

---

## 🚦 작업 진행 판단 기준

### ✅ 즉시 진행 가능 (안전)
1. UrlAnalyzer, MethodResolver 삭제
2. __init__.py에서 import 제거
3. Async alias 정리

### ⚠️ 신중히 진행 (영향도 검토)
1. CrawlSourcePolicy 제거 (CrawlPolicy 수정 필요)
2. services/ 재구조화 (import 경로 변경)

### 🔄 장기 계획 (설계 논의)
1. Interface 기반 설계
2. AsyncWebCrawl 구현
3. YAML override 지원

---

**결론**: PresetManager가 기존 UrlAnalyzer + MethodResolver를 **완전히 대체**하며, region 지원과 WebDriver override 기능까지 추가로 제공합니다. 삭제해도 안전합니다.
