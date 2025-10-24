# Interface 설계 vs Sync/Async 분기 비교 분석

## 🎯 두 가지 접근 방식

### Option A: Sync/Async 별도 클래스 (현재 Services 패턴)

```python
# adapter/sync_web_crawl.py
class SyncWebCrawl:
    """Sync WebCrawl - 동기 실행"""
    
    def _execute(self, url: str, policy: CrawlPolicy, wd_config: Dict) -> Dict:
        # Sync services 직접 import
        from ..services.adapter import SyncSeleniumAdapter
        from ..services.navigator import SyncNavigator
        from ..services.sync_extractor import SyncJSExtractor
        
        adapter = SyncSeleniumAdapter(driver)
        navigator = SyncNavigator(adapter, policy)
        extractor = SyncJSExtractor(adapter, policy)
        
        navigator.load(url)
        data = extractor.extract()
        return {"data": data}


# adapter/async_web_crawl.py
class AsyncWebCrawl:
    """Async WebCrawl - 비동기 실행"""
    
    async def _execute(self, url: str, policy: CrawlPolicy, wd_config: Dict) -> Dict:
        # Async services 직접 import
        from ..services.adapter import AsyncSeleniumAdapter
        from ..services.navigator import AsyncNavigator
        from ..services.extractor import AsyncJSExtractor
        
        adapter = AsyncSeleniumAdapter(driver)
        navigator = AsyncNavigator(adapter, policy)
        extractor = AsyncJSExtractor(adapter, policy)
        
        await navigator.load(url)
        data = await extractor.extract()
        return {"data": data}
```

**특징:**
- 각 클래스가 직접 해당 services import
- 메서드 시그니처가 다름 (def vs async def)
- 코드 중복 많음 (로직은 동일, async/await만 차이)

---

### Option B: Interface 기반 Generic 설계

```python
# core/interfaces.py
from typing import Protocol, Any

class BrowserController(Protocol):
    """Browser 제어 인터페이스 (Sync/Async 공통)"""
    def get(self, url: str) -> Any: ...
    def scroll_bottom(self, step: int, delay: float, max_scrolls: int) -> Any: ...
    def execute_js(self, script: str) -> Any: ...

class Navigator(Protocol):
    """Navigator 인터페이스"""
    def load(self, base_url: str) -> Any: ...
    def scroll(self, strategy: str, max_scrolls: int, pause_sec: float) -> Any: ...

class Extractor(Protocol):
    """Extractor 인터페이스"""
    def extract(self) -> Any: ...


# adapter/web_crawl.py (Generic)
from typing import TypeVar, Generic, Type
from ..core.interfaces import BrowserController, Navigator, Extractor

BrowserT = TypeVar('BrowserT', bound=BrowserController)
NavigatorT = TypeVar('NavigatorT', bound=Navigator)
ExtractorT = TypeVar('ExtractorT', bound=Extractor)

class WebCrawl(Generic[BrowserT, NavigatorT, ExtractorT]):
    """Generic WebCrawl - Sync/Async 모두 지원"""
    
    def __init__(
        self,
        browser_cls: Type[BrowserT],
        navigator_cls: Type[NavigatorT],
        extractor_cls: Type[ExtractorT],
        ...
    ):
        self.browser_cls = browser_cls
        self.navigator_cls = navigator_cls
        self.extractor_cls = extractor_cls
    
    def _execute(self, url: str, policy: CrawlPolicy, wd_config: Dict) -> Any:
        # Generic하게 사용
        adapter = self.browser_cls(driver)
        navigator = self.navigator_cls(adapter, policy)
        extractor = self.extractor_cls(adapter, policy)
        
        navigator.load(url)  # Sync면 바로 실행, Async면 coroutine 반환
        data = extractor.extract()
        return {"data": data}


# 사용 예시
from ..services.adapter import SyncSeleniumAdapter
from ..services.navigator import SyncNavigator
from ..services.sync_extractor import SyncJSExtractor

sync_crawl = WebCrawl(
    browser_cls=SyncSeleniumAdapter,
    navigator_cls=SyncNavigator,
    extractor_cls=SyncJSExtractor
)

# 또는 Async
from ..services.adapter import AsyncSeleniumAdapter
from ..services.navigator import AsyncNavigator
from ..services.extractor import AsyncJSExtractor

async_crawl = WebCrawl(
    browser_cls=AsyncSeleniumAdapter,
    navigator_cls=AsyncNavigator,
    extractor_cls=AsyncJSExtractor
)
```

**특징:**
- 한 클래스로 Sync/Async 모두 처리
- Type parameter로 services 주입
- 코드 중복 없음

---

## 📊 장단점 비교표

| 항목 | Option A: Sync/Async 별도 | Option B: Interface Generic |
|------|---------------------------|----------------------------|
| **코드 중복** | ❌ 높음 (로직 중복) | ✅ 낮음 (한 번만 작성) |
| **타입 안정성** | ✅ 명확 (SyncWebCrawl vs AsyncWebCrawl) | ⚠️ 복잡 (Generic[T, U, V]) |
| **가독성** | ✅ 직관적 (Sync/Async 구분 명확) | ⚠️ 추상적 (Protocol 이해 필요) |
| **유지보수** | ❌ 어려움 (양쪽 모두 수정) | ✅ 쉬움 (한 곳만 수정) |
| **확장성** | ⚠️ 보통 (새 클래스 추가) | ✅ 높음 (Type만 변경) |
| **테스트** | ✅ 간단 (각각 독립 테스트) | ⚠️ 복잡 (Generic 테스트) |
| **런타임 오버헤드** | ✅ 없음 | ⚠️ 약간 (Type checking) |
| **IDE 지원** | ✅ 완벽 (자동완성 정확) | ⚠️ 제한적 (Generic 추론) |
| **Learning Curve** | ✅ 낮음 (직관적) | ❌ 높음 (Protocol/Generic 학습) |
| **Python 관례** | ✅ 일반적 패턴 | ⚠️ 고급 패턴 (드물게 사용) |

---

## 🔍 현재 Services 구조와의 호환성

### Services 현재 상태
```python
# services/adapter.py
class AsyncSeleniumAdapter: ...
class SyncSeleniumAdapter: ...

# services/navigator.py
class AsyncNavigator: ...
class SyncNavigator: ...

# services/sync_extractor.py
class SyncJSExtractor: ...

# services/extractor.py
class AsyncJSExtractor: ...
```

**특징:**
- 각 파일 내에서 Async/Sync 구분 유지
- 별도 클래스로 명확히 분리
- import 경로가 명확

---

## 🎯 권장 방향: **Option A (Sync/Async 별도)**

### 이유

**1. Services 패턴과 일관성**
```
services/adapter.py → SyncSeleniumAdapter, AsyncSeleniumAdapter
services/navigator.py → SyncNavigator, AsyncNavigator
adapter/sync_web_crawl.py → SyncWebCrawl
adapter/async_web_crawl.py → AsyncWebCrawl  (미래)
```
모든 계층에서 동일한 패턴 사용

**2. Python 생태계 관례**
- Django: `sync_to_async()`, `async_to_sync()` - 별도 처리
- FastAPI: sync/async 라우터 별도
- aiohttp vs requests - 완전히 다른 라이브러리

**3. 명확한 타입 안정성**
```python
# ✅ 명확함
crawl: SyncWebCrawl = SyncWebCrawl(...)
result: Dict = crawl.run(urls)

# ⚠️ 복잡함
crawl: WebCrawl[SyncSeleniumAdapter, SyncNavigator, SyncJSExtractor] = ...
```

**4. 현실적 사용 패턴**
- 대부분 프로젝트는 Sync **또는** Async 중 하나만 사용
- 둘을 혼용하는 경우는 매우 드묾
- Generic으로 추상화할 필요성 낮음

**5. 코드 중복은 오히려 장점**
```python
# Sync와 Async는 근본적으로 다른 실행 모델
# 중복 코드여도 독립적으로 진화 가능
class SyncWebCrawl:
    def _execute(self): 
        # Sync 특화 최적화 (스레드풀, 캐싱 등)
        pass

class AsyncWebCrawl:
    async def _execute(self): 
        # Async 특화 최적화 (이벤트루프, concurrent 등)
        pass
```

---

## 📋 최종 구조 (권장)

```
crawl_utils/
├── core/
│   ├── policy.py
│   └── models.py
│
├── services/               # 각 파일 내에서 Sync/Async 구분
│   ├── adapter.py          # AsyncSeleniumAdapter, SyncSeleniumAdapter
│   ├── navigator.py        # AsyncNavigator, SyncNavigator
│   ├── sync_extractor.py   # SyncJSExtractor
│   ├── extractor.py        # AsyncJSExtractor
│   └── ...
│
├── adapter/
│   ├── sync_web_crawl.py   # SyncWebCrawl (현재)
│   ├── async_web_crawl.py  # AsyncWebCrawl (미래)
│   └── webdriver_manager.py
│
├── presets/                # PresetManager (공통)
│   ├── __init__.py
│   ├── domains.py
│   └── ...
│
└── __init__.py
    # 현재 기본 export
    from .adapter.sync_web_crawl import SyncWebCrawl as WebCrawl
    
    # 명시적 import 지원
    from .adapter.sync_web_crawl import SyncWebCrawl
    # from .adapter.async_web_crawl import AsyncWebCrawl  # 미래
```

---

## 🚀 구현 계획

### Step 1: 파일명/클래스명 변경
```bash
mv adapter/crawl.py adapter/sync_web_crawl.py
```

```python
# adapter/sync_web_crawl.py
class SyncWebCrawl:  # 기존 WebCrawl → SyncWebCrawl
    ...
```

### Step 2: __init__.py 업데이트
```python
# crawl_utils/__init__.py
from .adapter.sync_web_crawl import SyncWebCrawl

# 하위 호환성을 위한 alias
WebCrawl = SyncWebCrawl

__all__ = [
    "SyncWebCrawl",
    "WebCrawl",  # alias
]
```

### Step 3: 미래 AsyncWebCrawl 준비 (구조만)
```python
# adapter/async_web_crawl.py (스켈레톤)
class AsyncWebCrawl:
    """Async WebCrawl - 비동기 실행 (미래 구현)"""
    
    async def run(self, urls: List[str], provider: str) -> List[Dict]:
        raise NotImplementedError("AsyncWebCrawl not implemented yet")
```

---

## 🎓 결론

**Interface Generic 설계는 과도한 추상화입니다.**

현재 요구사항:
- ✅ Sync만 필요 (당장)
- ✅ Services가 이미 Sync/Async 별도 클래스
- ✅ Python 생태계 관례

따라서 **SyncWebCrawl/AsyncWebCrawl 별도 클래스**가 최선입니다.

**장점 요약:**
1. Services 패턴과 일관성
2. 명확한 타입 (SyncWebCrawl vs AsyncWebCrawl)
3. 독립적 진화 가능 (Sync/Async 특화 최적화)
4. Python 생태계 관례 준수
5. IDE 지원 완벽
6. 낮은 Learning Curve

**단점 (수용 가능):**
- 코드 중복 → 독립성 확보로 상쇄
- 유지보수 → 실제로는 Sync만 주로 사용
