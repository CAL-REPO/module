# -*- coding: utf-8 -*-
"""crawl_utils/services/sync_extractor.py

Sync 버전 Extractor - DOM 기반 데이터 추출.

책임:
1. DOM에서 CSS/XPath selector로 데이터 추출
2. JavaScript snippet 실행 결과 추출
3. 추출된 데이터 정규화

사용 예시:
```python
from crawl_utils.services.sync_extractor import SyncDOMExtractor

extractor = SyncDOMExtractor(adapter, policy)
dom = navigator.get_dom()
data = extractor.extract(dom)
```
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.policy import CrawlPolicy, ExtractorPolicy
    from .adapter import SyncSeleniumAdapter

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore


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
        self.extractor_policy: Optional['ExtractorPolicy'] = getattr(policy, 'extractor', None)
    
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
        self.extractor_policy: Optional['ExtractorPolicy'] = getattr(policy, 'extractor', None)
    
    def extract(self, dom: str = None) -> Dict[str, Any]:
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
    
    def extract_list(self, dom: str = None) -> List[Dict[str, Any]]:
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


# ============================================================================
# Factory
# ============================================================================

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
        
        from ..core.policy import ExtractorType
        
        etype = extractor_policy.type
        
        if etype == ExtractorType.DOM:
            return SyncDOMExtractor(self.adapter, self.policy)
        elif etype == ExtractorType.JS:
            return SyncJSExtractor(self.adapter, self.policy)
        elif etype == ExtractorType.API:
            raise NotImplementedError("API extractor not implemented in sync version")
        else:
            raise ValueError(f"Unsupported extractor type: {etype}")
