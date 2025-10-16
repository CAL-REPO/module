# -*- coding: utf-8 -*-
# crawl_utils/services/__init__.py
# Crawl Utils Services - 크롤링 서비스 컴포넌트

"""
Crawl Utils Services
====================

크롤링 파이프라인의 핵심 서비스 컴포넌트들을 제공합니다.
각 서비스는 Async/Sync 버전을 모두 지원합니다.

파일 구조:
----------
- adapter.py: AsyncSeleniumAdapter, SyncSeleniumAdapter
- navigator.py: SeleniumNavigator (Async), SyncNavigator (Sync)
- extractor.py: DOMExtractor, JSExtractor, APIExtractor, ExtractorFactory (Async Only)
- fetcher.py: HTTPFetcher (Async), SyncHTTPFetcher (Sync), DummyFetcher
- saver.py: FileSaver (Async), SyncFileSaver (Sync)
- normalizer.py: DataNormalizer (Sync, Rule 기반)
- smart_normalizer.py: SmartNormalizer (Sync, 자동 타입 추론)

네이밍 규칙:
-----------
✅ Async 버전: AsyncXxx 또는 Xxx (접두사 없음, Async가 기본)
✅ Sync 버전: SyncXxx (명시적 Sync 접두사)
✅ Alias: Xxx = AsyncXxx (하위 호환성)

예시:
- AsyncSeleniumAdapter / SyncSeleniumAdapter
- SeleniumNavigator (Async) / SyncNavigator (Sync)
- HTTPFetcher (Async) / SyncHTTPFetcher (Sync)
- FileSaver (Async) / SyncFileSaver (Sync)

사용 가이드:
-----------
**Async 사용 (비동기 파이프라인)**:
```python
from crawl_utils.services import AsyncSeleniumAdapter, SeleniumNavigator, HTTPFetcher, FileSaver

async with AsyncSeleniumAdapter(driver) as browser:
    navigator = SeleniumNavigator(browser, policy)
    fetcher = HTTPFetcher()
    saver = FileSaver(policy.storage)
    # ... async operations
```

**Sync 사용 (동기 스크립트)**:
```python
from crawl_utils.services import SyncSeleniumAdapter, SyncNavigator, SyncHTTPFetcher, SyncFileSaver

with SyncSeleniumAdapter(driver) as browser:
    navigator = SyncNavigator(browser, policy)
    fetcher = SyncHTTPFetcher()
    saver = SyncFileSaver(policy.storage)
    # ... sync operations
```

Note: 고수준 오케스트레이션(CrawlPipeline/SyncCrawlRunner)은 현재 패키지에서 제공하지 않습니다.
      이들은 별도의 entry_points나 상위 레벨에서 구현됩니다.
"""

from __future__ import annotations

# ============================================================================
# Adapter: Selenium WebDriver 어댑터
# ============================================================================
from .adapter import (
    AsyncSeleniumAdapter,  # Async 버전 (asyncio.to_thread 사용)
    SyncSeleniumAdapter,   # Sync 버전 (직접 Selenium API 호출)
    SeleniumAdapter,       # Alias for AsyncSeleniumAdapter (하위 호환성)
)

# ============================================================================
# Navigator: 페이지 네비게이션 (로드, 스크롤, 대기)
# ============================================================================
from .navigator import (
    AsyncNavigator,      # Async 네비게이터
    SyncNavigator,       # Sync 네비게이터
    # Backward compatibility aliases
    SeleniumNavigator,   # = AsyncNavigator
    Navigator,           # = AsyncNavigator
)

# ============================================================================
# Extractor: 데이터 추출 (Async Only - DOM 파싱/JS 실행/API 호출)
# ============================================================================
from .extractor import (
    AsyncExtractorFactory,  # Extractor 생성 팩토리 (Async)
    AsyncDOMExtractor,      # DOM 기반 추출 (BeautifulSoup)
    AsyncJSExtractor,       # JavaScript 실행 기반 추출
    AsyncAPIExtractor,      # API 호출 기반 추출
    # Backward compatibility aliases
    ExtractorFactory,       # = AsyncExtractorFactory
    DOMExtractor,          # = AsyncDOMExtractor
    JSExtractor,           # = AsyncJSExtractor
    APIExtractor,          # = AsyncAPIExtractor
)

# ============================================================================
# Fetcher: HTTP 리소스 가져오기
# ============================================================================
from .fetcher import (
    AsyncHTTPFetcher,    # Async HTTP fetcher (aiohttp 기반)
    AsyncDummyFetcher,   # Async 테스트용 더미 Fetcher
    SyncHTTPFetcher,     # Sync HTTP fetcher (requests 기반)
    # Backward compatibility aliases
    HTTPFetcher,         # = AsyncHTTPFetcher
    DummyFetcher,        # = AsyncDummyFetcher
)

# ============================================================================
# Saver: 파일 저장
# ============================================================================
from .saver import (
    AsyncFileSaver,  # Async 파일 저장 (asyncio.to_thread 사용)
    SyncFileSaver,   # Sync 파일 저장 (직접 파일 I/O)
    # Backward compatibility alias
    FileSaver,       # = AsyncFileSaver
)

# ============================================================================
# Normalizer: 데이터 정규화 (Sync Only - 순수 데이터 변환)
# ============================================================================
from .normalizer import (
    DataNormalizer,  # Rule 기반 정규화 (NormalizationPolicy 사용)
)

from .smart_normalizer import (
    SmartNormalizer,  # 자동 타입 추론 정규화 (TypeInferencer 사용)
)


__all__ = [
    # ========================================
    # Adapter
    # ========================================
    "AsyncSeleniumAdapter",
    "SyncSeleniumAdapter",
    "SeleniumAdapter",  # Alias for AsyncSeleniumAdapter
    
    # ========================================
    # Navigator
    # ========================================
    "AsyncNavigator",
    "SyncNavigator",
    "SeleniumNavigator",  # Alias for AsyncNavigator
    "Navigator",          # Alias for AsyncNavigator
    
    # ========================================
    # Extractor (Async Only)
    # ========================================
    "AsyncExtractorFactory",
    "AsyncDOMExtractor",
    "AsyncJSExtractor",
    "AsyncAPIExtractor",
    "ExtractorFactory",   # Alias for AsyncExtractorFactory
    "DOMExtractor",       # Alias for AsyncDOMExtractor
    "JSExtractor",        # Alias for AsyncJSExtractor
    "APIExtractor",       # Alias for AsyncAPIExtractor
    
    # ========================================
    # Fetcher
    # ========================================
    "AsyncHTTPFetcher",
    "AsyncDummyFetcher",
    "SyncHTTPFetcher",
    "HTTPFetcher",        # Alias for AsyncHTTPFetcher
    "DummyFetcher",       # Alias for AsyncDummyFetcher
    
    # ========================================
    # Saver
    # ========================================
    "AsyncFileSaver",
    "SyncFileSaver",
    "FileSaver",          # Alias for AsyncFileSaver
    
    # ========================================
    # Normalizer (Sync Only)
    # ========================================
    "DataNormalizer",
    "SmartNormalizer",
]



