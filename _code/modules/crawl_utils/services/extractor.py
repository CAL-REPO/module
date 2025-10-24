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

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..core.interfaces import Navigator, ResourceFetcher
from ..core.policy import CrawlPolicy, ExtractorType

if TYPE_CHECKING:
    from .adapter import SyncSeleniumAdapter

try:  # optional dependency for DOM parsing
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency
    BeautifulSoup = None  # type: ignore


# ============================================================================
# Async Extractors
# ============================================================================


class AsyncDOMExtractor:
    """Asynchronous DOM-based data extractor using BeautifulSoup."""
    
    def __init__(self, navigator: Navigator, policy: CrawlPolicy):
        self.navigator = navigator
        self.policy = policy

    async def extract(self) -> List[Dict[str, Any]]:
        html = await self.navigator.get_dom()
        selector = self.policy.extractor.item_selector
        if selector and BeautifulSoup:
            soup = BeautifulSoup(html, "html.parser")
            elements = soup.select(selector)
            return [
                {
                    "kind": "dom",
                    "selector": selector,
                    "html": str(el),
                    "text": el.get_text(strip=True),
                    "attrs": dict(el.attrs),
                }
                for el in elements
            ]
        return [{"kind": "dom", "html": html, "selector": selector}]


class AsyncJSExtractor:
    """Asynchronous JavaScript-based data extractor."""
    
    def __init__(self, navigator: Navigator, policy: CrawlPolicy):
        self.navigator = navigator
        self.policy = policy

    async def extract(self) -> List[Dict[str, Any]]:
        snippet = self.policy.extractor.js_snippet or "return [];"
        result = await self.navigator.execute_js(snippet)
        if not isinstance(result, list):
            result = [result]
        return [{"kind": "js", "payload": item} for item in result]


class AsyncAPIExtractor:
    """Asynchronous API-based data extractor."""
    
    def __init__(self, fetcher: ResourceFetcher, policy: CrawlPolicy):
        self.fetcher = fetcher
        self.policy = policy

    async def extract(self) -> List[Dict[str, Any]]:
        endpoint = self.policy.extractor.api_endpoint
        if not endpoint:
            return []
        payload = await self.fetcher.fetch_json(
            endpoint,
            method=self.policy.extractor.api_method,
            payload=self.policy.extractor.payload,
        )
        return [{"kind": "api", "payload": payload}]


class AsyncExtractorFactory:
    """Factory for creating async extractors based on policy."""
    
    def __init__(self, policy: CrawlPolicy, navigator: Navigator, fetcher: Optional[ResourceFetcher] = None):
        self.policy = policy
        self.navigator = navigator
        self.fetcher = fetcher

    def create(self):
        etype = self.policy.extractor.type
        if etype == ExtractorType.DOM:
            return AsyncDOMExtractor(self.navigator, self.policy)
        if etype == ExtractorType.JS:
            return AsyncJSExtractor(self.navigator, self.policy)
        if etype == ExtractorType.API:
            if not self.fetcher:
                raise ValueError("API extractor requires a ResourceFetcher instance.")
            return AsyncAPIExtractor(self.fetcher, self.policy)
        raise ValueError(f"Unsupported extractor type: {etype}")


# ============================================================================
# Sync Extractors
# ============================================================================

class SyncDOMExtractor:
    """Sync DOM-based data extractor using BeautifulSoup.
    
    DOM에서 CSS selector로 데이터를 추출합니다.
    """
    
    def __init__(
        self,
        adapter: Optional['SyncSeleniumAdapter'],
        policy: 'CrawlPolicy'
    ):
        self.adapter = adapter
        self.policy = policy
        self.extractor_policy = getattr(policy, 'extractor', None)
    
    def extract(self, dom: str) -> Dict[str, Any]:
        """DOM에서 단일 아이템 데이터 추출 (상품 상세).
        
        Args:
            dom: HTML DOM 문자열
        
        Returns:
            추출된 데이터 딕셔너리
        """
        if not self.extractor_policy:
            return {"_no_extractor_policy": True}
        
        selector = self.extractor_policy.item_selector
        
        if not selector or not BeautifulSoup:
            return {
                "dom_preview": dom[:200] if dom else "",
                "_no_selector": not selector,
                "_no_beautifulsoup": BeautifulSoup is None
            }
        
        # BeautifulSoup로 파싱
        soup = BeautifulSoup(dom, "html.parser")
        element = soup.select_one(selector)
        
        if not element:
            return {
                "selector": selector,
                "_element_not_found": True
            }
        
        # 데이터 추출
        data = {
            "selector": selector,
            "html": str(element)[:500],  # 너무 길면 잘라냄
            "text": element.get_text(strip=True),
            "attrs": dict(element.attrs) if hasattr(element, 'attrs') else {}
        }
        
        return data
    
    def extract_list(self, dom: str) -> List[Dict[str, Any]]:
        """DOM에서 리스트 아이템 추출 (상품 검색).
        
        Args:
            dom: HTML DOM 문자열
        
        Returns:
            추출된 아이템 리스트
        """
        if not self.extractor_policy:
            return [{"_no_extractor_policy": True}]
        
        selector = self.extractor_policy.item_selector
        
        if not selector or not BeautifulSoup:
            return [{
                "_no_selector": not selector,
                "_no_beautifulsoup": BeautifulSoup is None
            }]
        
        # BeautifulSoup로 파싱
        soup = BeautifulSoup(dom, "html.parser")
        elements = soup.select(selector)
        
        if not elements:
            return [{
                "selector": selector,
                "_elements_not_found": True
            }]
        
        # 각 element에서 데이터 추출
        items = []
        for el in elements:
            item = {
                "html": str(el)[:500],
                "text": el.get_text(strip=True),
                "attrs": dict(el.attrs) if hasattr(el, 'attrs') else {}
            }
            items.append(item)
        
        return items


class SyncJSExtractor:
    """Sync JavaScript-based data extractor.
    
    JavaScript snippet을 실행하여 데이터를 추출합니다.
    """
    
    def __init__(
        self,
        adapter: Optional['SyncSeleniumAdapter'],
        policy: 'CrawlPolicy'
    ):
        self.adapter = adapter
        self.policy = policy
        self.extractor_policy = getattr(policy, 'extractor', None)
    
    def extract(self, dom: Optional[str] = None) -> Dict[str, Any]:
        """JavaScript snippet 실행하여 데이터 추출.
        
        Args:
            dom: 사용하지 않음 (signature 호환성 위해)
        
        Returns:
            추출된 데이터
        """
        if not self.extractor_policy or not self.adapter:
            return {"_no_extractor_policy_or_adapter": True}
        
        snippet = self.extractor_policy.js_snippet or "return {};"
        
        try:
            result = self.adapter.execute_js(snippet)
            
            if isinstance(result, dict):
                return result
            elif isinstance(result, list):
                return {"items": result}
            else:
                return {"result": result}
                
        except Exception as e:
            return {"_js_error": str(e)}
    
    def extract_list(self, dom: Optional[str] = None) -> List[Dict[str, Any]]:
        """JavaScript snippet 실행하여 리스트 데이터 추출.
        
        Args:
            dom: 사용하지 않음
        
        Returns:
            추출된 아이템 리스트
        """
        if not self.extractor_policy or not self.adapter:
            return [{"_no_extractor_policy_or_adapter": True}]
        
        snippet = self.extractor_policy.js_snippet or "return [];"
        
        try:
            result = self.adapter.execute_js(snippet)
            
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                return [result]
            else:
                return [{"result": result}]
                
        except Exception as e:
            return [{"_js_error": str(e)}]


class SyncExtractorFactory:
    """Sync Extractor 팩토리.
    
    ExtractorType에 따라 적절한 Extractor를 생성합니다.
    """
    
    def __init__(
        self,
        adapter: Optional['SyncSeleniumAdapter'],
        policy: 'CrawlPolicy'
    ):
        self.adapter = adapter
        self.policy = policy
    
    def create(self):
        """Extractor 생성.
        
        Returns:
            SyncDOMExtractor 또는 SyncJSExtractor
        
        Raises:
            ValueError: 지원하지 않는 extractor type
        """
        extractor_policy = getattr(self.policy, 'extractor', None)
        
        if not extractor_policy:
            # 기본값: DOM Extractor
            return SyncDOMExtractor(self.adapter, self.policy)
        
        etype = extractor_policy.type
        
        if etype == ExtractorType.DOM:
            return SyncDOMExtractor(self.adapter, self.policy)
        elif etype == ExtractorType.JS:
            return SyncJSExtractor(self.adapter, self.policy)
        elif etype == ExtractorType.API:
            raise NotImplementedError("API extractor not implemented in sync version")
        else:
            raise ValueError(f"Unsupported extractor type: {etype}")
