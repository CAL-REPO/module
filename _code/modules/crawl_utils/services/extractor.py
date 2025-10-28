# -*- coding: utf-8 -*-
# crawl_utils/services/extractor.py
# Extractor: 데이터 추출 (Async + Sync)

"""
Extractor Services - 데이터 추출
================================

책임:
1. DOM에서 CSS/XPath selector로 데이터 추출
2. JavaScript snippet 실행 결과 추출
3. API 엔드포인트에서 데이터 가져오기

Async 버전: AsyncDOMExtractor, AsyncJSExtractor, AsyncAPIExtractor
Sync 버전: SyncDOMExtractor, SyncJSExtractor
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

from ..core.policy import ExtractorType, ExtractorPolicy

if TYPE_CHECKING:
    from .adapter import SyncSeleniumAdapter

try:  # optional dependency for DOM parsing
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency
    BeautifulSoup = None  # type: ignore


# ============================================================================
# JS Executor (SRP: JavaScript 실행 전용)
# ============================================================================

class JSExecutor:
    """JavaScript 실행 전용 클래스.
    
    책임:
    - JS snippet을 안전하게 실행 가능한 형태로 래핑
    - 에러 핸들링
    - 재시도 로직
    """
    
    # JS wrapper template (에러 처리 포함)
    WRAPPER_TEMPLATE = (
        "try{"
        " var s = arguments[0];"
        " var f = new Function('s', 'return (function(){ ' + s + ' })();');"
        " var __r = f(s);"
        " return __r;"
        "}catch(e){"
        " return { '__js_error': String(e), '__stack': (e && e.stack) ? String(e.stack) : '' };"
        "}"
    )
    
    def __init__(
        self,
        adapter: 'SyncSeleniumAdapter',
        max_retries: int = 2,
        retry_delay: float = 0.5
    ):
        self.adapter = adapter
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def execute(self, snippet: str) -> Optional[Any]:
        """JS snippet 실행 (재시도 포함).
        
        Args:
            snippet: JavaScript 코드
        
        Returns:
            실행 결과 또는 None
        """
        result = self._execute_once(snippet)
        
        # 재시도 로직
        if result is None and self.max_retries > 0:
            import time
            for attempt in range(self.max_retries):
                # print(f"JS execution retry {attempt + 1}/{self.max_retries}")
                time.sleep(self.retry_delay)
                result = self._execute_once(snippet)
                if result is not None:
                    # print(f"JS execution succeeded on retry {attempt + 1}")
                    break
        
        return result
    
    def _execute_once(self, snippet: str) -> Optional[Any]:
        """JS snippet 1회 실행.
        
        Args:
            snippet: JavaScript 코드
        
        Returns:
            실행 결과 또는 None
        """
        try:
            result = self.adapter.execute_js(self.WRAPPER_TEMPLATE, snippet)
            
            # adapter가 None을 반환한 경우, 직접 driver 호출 시도
            if result is None:
                drv = getattr(self.adapter, "_drv", None)
                if drv is not None:
                    # print("Adapter returned None, trying direct driver call")
                    result = drv.execute_script(self.WRAPPER_TEMPLATE, snippet)
            
            return result
        except Exception as e:
            # printing(f"JS execution failed: {e}")
            return None

class Canonicalizer:

    def __init__(self) -> None:
        pass

    def canonicalize_result_to_list(self, result: Any, *, drop_errors: bool = True) -> List[Dict[str, Any]]:
        """
        Normalize JS executor result into List[Dict].

        - None -> []
        - dict with '__js_error' or '_js_error' -> return single error dict (keeps JS error info)
        - dict with 'items' (and items is list) -> return items (each item wrapped to dict if needed)
        - dict otherwise -> [dict]
        - list -> each element normalized to dict (primitive -> {'result': v})
        - primitive -> [{'result': primitive}]

        If drop_errors True, any dict containing '_error' or '_js_error' will be filtered out.
        """
        if result is None:
            return []

        # JS-level error object (as returned by wrapper) - expose as error record
        if isinstance(result, dict) and ("__js_error" in result or "_js_error" in result):
            # normalize key names to single form used elsewhere
            err = {}
            if "__js_error" in result:
                err["_js_error"] = result.get("__js_error")
                err["_js_stack"] = result.get("__stack")
            elif "_js_error" in result:
                err["_js_error"] = result.get("_js_error")
                err["_js_stack"] = result.get("_js_stack")
            return [err]

        records: List[Any] = []

        if isinstance(result, dict) and isinstance(result.get("items"), list):
            records = result["items"]
        elif isinstance(result, list):
            records = result
        elif isinstance(result, dict):
            records = [result]
        else:
            # primitive
            return [{"result": result}]

        out: List[Dict[str, Any]] = []
        for r in records:
            if isinstance(r, dict):
                if drop_errors and ("_error" in r or "_js_error" in r or "__js_error" in r):
                    # skip error records when drop_errors enabled
                    continue
                out.append(r)
            else:
                # wrap non-dict elements
                out.append({"result": r})

        return out

# ============================================================================
# Sync DOM Extractor
# ============================================================================

class SyncDOMExtractor:
    """Sync DOM 기반 데이터 추출기.
    
    책임:
    - CSS selector로 DOM 요소 추출
    - BeautifulSoup 파싱
    - 요소별 데이터 변환
    """
    
    def __init__(
        self,
        adapter: Optional['SyncSeleniumAdapter'],
        policy: ExtractorPolicy
    ):
        self.adapter = adapter
        self.policy = policy
    
    def extract_list(self, dom: str) -> List[Dict[str, Any]]:
        """DOM에서 리스트 아이템 추출.
        
        Args:
            dom: HTML DOM 문자열
        
        Returns:
            추출된 아이템 리스트
        """
        # 사전 검증
        if not self.policy:
            return [{"_error": "no_extractor_policy"}]
        selector = self.policy.item_selector
        
        if not selector:
            return [{"_error": "no_selector"}]
        
        if not BeautifulSoup:
            return [{"_error": "beautifulsoup_not_available"}]
        
        # BeautifulSoup 파싱
        try:
            soup = BeautifulSoup(dom, "html.parser")
            elements = soup.select(selector)
        except Exception as e:
            return [{"_error": f"parsing_failed: {e}"}]
        
        if not elements:
            return [{"selector": selector, "_warning": "no_elements_found"}]
        
        # 요소별 데이터 추출
        items = []
        for idx, el in enumerate(elements):
            try:
                item = self._extract_element_data(el)
                items.append(item)
            except Exception as e:
                items.append({"_error": f"element_{idx}_failed: {e}"})
        
        return items
    
    def _extract_element_data(self, element) -> Dict[str, Any]:
        """단일 요소에서 데이터 추출.
        
        Args:
            element: BeautifulSoup element
        
        Returns:
            추출된 데이터
        """
        return {
            "html": str(element)[:500],  # HTML 길이 제한
            "text": element.get_text(strip=True),
            "attrs": dict(element.attrs) if hasattr(element, 'attrs') else {}
        }


# ============================================================================
# Sync JS Extractor
# ============================================================================

class SyncJSExtractor:
    """Sync JavaScript 기반 데이터 추출기.
    
    책임:
    - JavaScript snippet 실행
    - 결과 정규화
    """
    
    def __init__(
        self,
        adapter: Optional['SyncSeleniumAdapter'],
        policy: ExtractorPolicy
    ):
        self.adapter = adapter
        self.policy = policy
        self.canonicalizer = Canonicalizer()

        if adapter:
            self.executor = JSExecutor(adapter)
        else:
            self.executor = None
    
    def extract(self, dom: Optional[str] = None) -> Dict[str, Any]:
        """JavaScript snippet 실행하여 단일 데이터 추출.
        
        Args:
            dom: 사용하지 않음 (signature 호환성)
        
        Returns:
            추출된 데이터 딕셔너리
        """
        # 사전 검증
        validation_error = self._validate()
        if validation_error:
            return validation_error
        
        snippet = self.policy.js_snippet or "return {};"
        
        # JS 실행
        result = self.executor.execute(snippet) if self.executor else None
        
        # 결과 처리
        return self._process_single_result(result)
    
    def extract_list(self, dom: Optional[str] = None) -> List[Dict[str, Any]]:
        """JavaScript snippet 실행하여 리스트 데이터 추출.
        
        Args:
            dom: 사용하지 않음
        
        Returns:
            추출된 아이템 리스트
        """
        # 사전 검증
        validation_error = self._validate()
        if validation_error:
            return [validation_error]
        
        snippet = self.policy.js_snippet or "return [];"
        
        # JS 실행
        result = self.executor.execute(snippet) if self.executor else None
        
        # 결과 처리
        return self._process_list_result(result)
    
    def _validate(self) -> Optional[Dict[str, Any]]:
        """실행 전 검증.
        
        Returns:
            에러 딕셔너리 또는 None
        """
        if not self.policy or not self.adapter:
            return {"_error": "no_policy_or_adapter"}
        
        if not self.executor:
            return {"_error": "executor_not_initialized"}
        
        return None
    
    def _process_single_result(self, result: Any) -> Dict[str, Any]:
        """단일 결과 처리.
        
        Args:
            result: JS 실행 결과
        
        Returns:
            정규화된 결과
        """
        if isinstance(result, dict):
            # JS 에러 확인
            if "__js_error" in result:
                return {
                    "_js_error": result.get("__js_error"),
                    "_js_stack": result.get("__stack")
                }
            # 정상 결과
            print("JS execution succeeded, returned dict")
            return result
        
        if isinstance(result, list):
            print(f"JS execution returned list with {len(result)} items")
            return {"items": result}
        
        print(f"JS execution returned: {type(result).__name__}")
        return {"result": result}
    
    def _process_list_result(self, result: Any) -> List[Dict[str, Any]]:
        """리스트 결과 처리 (canonicalized) - 항상 List[Dict].
        
        Note: Flattening은 SyncCrawl에서 수행 (책임 분리)
        """
        # Prefer not to print in library code; keep limited logs for debugging.
        recs = self.canonicalizer.canonicalize_result_to_list(result, drop_errors=True)
        # If canonicalization produced empty list but original result had an error dict, preserve it
        if not recs and isinstance(result, dict):
            # If original dict had error keys, return that error for upstream awareness
            if "__js_error" in result or "_js_error" in result or "_error" in result:
                # normalize error dict
                err = {}
                if "__js_error" in result:
                    err["_js_error"] = result.get("__js_error")
                    err["_js_stack"] = result.get("__stack")
                elif "_js_error" in result:
                    err["_js_error"] = result.get("_js_error")
                    err["_js_stack"] = result.get("_js_stack")
                elif "_error" in result:
                    err["_error"] = result.get("_error")
                return [err]
        
        return recs


# ============================================================================
# Extractor Factory
# ============================================================================

class SyncExtractorFactory:
    """Sync Extractor 팩토리.
    
    책임:
    - ExtractorType에 따른 적절한 Extractor 생성
    - Policy 검증
    """
    
    def __init__(
        self,
        adapter: Optional['SyncSeleniumAdapter'],
        policy: ExtractorPolicy
    ):
        self.adapter = adapter
        self.policy = policy
    
    def create(self) -> Union[SyncDOMExtractor, SyncJSExtractor]:
        """Extractor 생성.
        
        Returns:
            SyncDOMExtractor 또는 SyncJSExtractor
        
        Raises:
            ValueError: 지원하지 않는 extractor type
            NotImplementedError: API extractor 요청 시
        """
        etype = self.policy.type
        
        if etype == ExtractorType.DOM:
            print("Creating SyncDOMExtractor")
            return SyncDOMExtractor(self.adapter, self.policy)
        
        elif etype == ExtractorType.JS:
            print("Creating SyncJSExtractor")
            return SyncJSExtractor(self.adapter, self.policy)
        
        elif etype == ExtractorType.API:
            print("API extractor is not supported in sync version")
            raise NotImplementedError(
                "API extractor is not implemented in sync version. "
                "Use async version or implement ResourceFetcher integration."
            )
        
        else:
            print(f"Unsupported extractor type: {etype}")
            raise ValueError(f"Unsupported extractor type: {etype}")

# ============================================================================
# Async Extractors
# ============================================================================


# class AsyncDOMExtractor:
#     """Asynchronous DOM-based data extractor using BeautifulSoup."""
    
#     def __init__(self, navigator: Navigator, policy: CrawlPolicy):
#         self.navigator = navigator
#         self.policy = policy

#     async def extract(self) -> List[Dict[str, Any]]:
#         html = await self.navigator.get_dom()
#         selector = self.policy.extractor.item_selector
#         if selector and BeautifulSoup:
#             soup = BeautifulSouprint(html, "html.parser")
#             elements = soup.select(selector)
#             return [
#                 {
#                     "type": "dom",
#                     "selector": selector,
#                     "html": str(el),
#                     "text": el.get_text(strip=True),
#                     "attrs": dict(el.attrs),
#                 }
#                 for el in elements
#             ]
#         return [{"type": "dom", "html": html, "selector": selector}]


# class AsyncJSExtractor:
#     """Asynchronous JavaScript-based data extractor."""
    
#     def __init__(self, navigator: Navigator, policy: CrawlPolicy):
#         self.navigator = navigator
#         self.policy = policy

#     async def extract(self) -> List[Dict[str, Any]]:
#         snippet = self.policy.extractor.js_snippet or "return [];"
#         result = await self.navigator.execute_js(snippet)
#         if not isinstance(result, list):
#             result = [result]
#         return [{"type": "js", "payload": item} for item in result]


# class AsyncAPIExtractor:
#     """Asynchronous API-based data extractor."""
    
#     def __init__(self, fetcher: ResourceFetcher, policy: CrawlPolicy):
#         self.fetcher = fetcher
#         self.policy = policy

#     async def extract(self) -> List[Dict[str, Any]]:
#         endpoint = self.policy.extractor.api_endpoint
#         if not endpoint:
#             return []
#         payload = await self.fetcher.fetch_json(
#             endpoint,
#             method=self.policy.extractor.api_method,
#             payload=self.policy.extractor.payload,
#         )
#         return [{"type": "api", "payload": payload}]


# class AsyncExtractorFactory:
#     """Factory for creating async extractors based on policy."""
    
#     def __init__(self, policy: CrawlPolicy, navigator: Navigator, fetcher: Optional[ResourceFetcher] = None):
#         self.policy = policy
#         self.navigator = navigator
#         self.fetcher = fetcher

#     def create(self):
#         etype = self.policy.extractor.type
#         if etype == ExtractorType.DOM:
#             return AsyncDOMExtractor(self.navigator, self.policy)
#         if etype == ExtractorType.JS:
#             return AsyncJSExtractor(self.navigator, self.policy)
#         if etype == ExtractorType.API:
#             if not self.fetcher:
#                 raise ValueError("API extractor requires a ResourceFetcher instance.")
#             return AsyncAPIExtractor(self.fetcher, self.policy)
#         raise ValueError(f"Unsupported extractor type: {etype}")
