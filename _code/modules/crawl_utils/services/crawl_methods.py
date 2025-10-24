# -*- coding: utf-8 -*-
"""crawl_utils/services/crawl_methods.py

메서드별 크롤링 로직을 분리한 서비스 모듈.

책임:
1. product_detail - 상품 상세 페이지 크롤링
2. product_search - 상품 검색 결과 크롤링
3. 각 메서드는 Navigator, Extractor를 사용하여 데이터 추출

리팩토링:
- Template Method 패턴 적용 (BaseCrawlMethod)
- 타입 힌트 완성 (TYPE_CHECKING)
- 공통 로직 추출

사용 예시:
```python
from crawl_utils.services.crawl_methods import CrawlProductDetail

# Service 생성
detail_service = CrawlProductDetail(
    navigator=navigator,
    extractor=extractor,
    policy=policy,
    logger=logger
)

# 크롤링 실행
results = detail_service.crawl(urls, runtime_context)
```
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from loguru import Logger
    from ..core.policy import CrawlPolicy
    from .navigator import SyncNavigator
    from .extractor import SyncDOMExtractor, SyncJSExtractor


# ============================================================================
# Base Class (Template Method Pattern)
# ============================================================================

class BaseCrawlMethod(ABC):
    """크롤링 메서드 베이스 클래스 (Template Method 패턴).
    
    공통 크롤링 흐름을 정의하고, 서브클래스에서 세부 구현을 담당합니다.
    
    Template Method:
        1. crawl() - 전체 URL 리스트 순회
        2. _crawl_single_url() - 단일 URL 크롤링 (공통 흐름)
            - 페이지 로드
            - _pre_extract() Hook (서브클래스에서 오버라이드 가능)
            - DOM 가져오기
            - _extract() Abstract method (서브클래스에서 구현 필수)
        
    Hook Methods:
        - _pre_extract(): Wait, Scroll 등 추출 전 작업 (기본 구현 제공)
        
    Abstract Methods:
        - _extract(): 데이터 추출 로직 (서브클래스에서 구현 필수)
    """
    
    def __init__(
        self,
        navigator: Optional['SyncNavigator'],
        extractor: Optional[Union['SyncDOMExtractor', 'SyncJSExtractor']],
        policy: 'CrawlPolicy',
        logger: 'Logger'
    ):
        """Initialize base crawl method.
        
        Args:
            navigator: SyncNavigator 인스턴스
            extractor: SyncExtractor 인스턴스
            policy: CrawlPolicy
            logger: loguru Logger
        """
        self.navigator = navigator
        self.extractor = extractor
        self.policy = policy
        self.log = logger
    
    def crawl(
        self,
        urls: List[str],
        runtime_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """크롤링 실행 (Template Method).
        
        Args:
            urls: 크롤링할 URL 리스트
            runtime_context: 런타임 컨텍스트 (cas_no 등)
        
        Returns:
            추출된 데이터 리스트
        """
        results: List[Dict[str, Any]] = []
        
        for idx, url in enumerate(urls, 1):
            self.log.info(f"[{self._get_method_name()} {idx}/{len(urls)}] Processing: {url}")
            
            try:
                data = self._crawl_single_url(url, idx, runtime_context)
                results.extend(data if isinstance(data, list) else [data])
                
                count = len(data) if isinstance(data, list) else 1
                self.log.success(f"  Extracted: {count} items")
                
            except Exception as e:
                self.log.error(f"  Failed to crawl {url}: {e}")
                import traceback
                self.log.debug(f"  Traceback: {traceback.format_exc()}")
                
                # 에러 데이터 추가
                error_data = {
                    "_url": url,
                    "_index": idx,
                    "_method": self._get_method_name(),
                    "_error": str(e),
                    **runtime_context
                }
                results.append(error_data)
                continue
        
        return results
    
    def _crawl_single_url(
        self,
        url: str,
        index: int,
        runtime_context: Dict[str, Any]
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """단일 URL 크롤링 (Template Method - 공통 흐름).
        
        Args:
            url: 크롤링할 URL
            index: URL 인덱스
            runtime_context: 런타임 컨텍스트
        
        Returns:
            추출된 데이터 (단일 Dict 또는 List[Dict])
        """
        # Navigator 확인
        if not self.navigator:
            raise ValueError(f"Navigator is required for {self._get_method_name()} crawling")
        
        # 1. 페이지 로드
        self.log.debug(f"[{self._get_method_name()}] Loading URL: {url}")
        self.navigator.load(url)
        
        # 2. Pre-extract Hook (Wait, Scroll 등)
        self._pre_extract()
        
        # 3. DOM 가져오기
        dom = self.navigator.get_dom()
        
        # 4. 데이터 추출 (Abstract method - 서브클래스에서 구현)
        return self._extract(url, index, dom, runtime_context)
    
    def _pre_extract(self) -> None:
        """추출 전 Hook 메서드 (Wait, Scroll 등).
        
        기본 구현: Wait hook 실행
        서브클래스에서 오버라이드하여 추가 작업 수행 가능
        """
        # Navigator 확인
        if not self.navigator:
            return
        
        # Wait hook 실행
        if hasattr(self.policy, 'wait') and self.policy.wait:
            wait_cfg = self.policy.wait
            timeout = getattr(wait_cfg, 'timeout_sec', 10.0)
            hook = getattr(wait_cfg, 'hook', None)
            selector = getattr(wait_cfg, 'selector', None)
            condition = getattr(wait_cfg, 'condition', 'presence')
            
            if hook:
                self.log.debug(f"[{self._get_method_name()}] Waiting: hook={hook}, timeout={timeout}s")
                self.navigator.wait(hook, selector, timeout, condition)
    
    @abstractmethod
    def _extract(
        self,
        url: str,
        index: int,
        dom: str,
        runtime_context: Dict[str, Any]
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """데이터 추출 (Abstract method - 서브클래스에서 구현).
        
        Args:
            url: 크롤링한 URL
            index: URL 인덱스
            dom: HTML DOM
            runtime_context: 런타임 컨텍스트
        
        Returns:
            추출된 데이터 (단일 Dict 또는 List[Dict])
        """
        pass
    
    @abstractmethod
    def _get_method_name(self) -> str:
        """메서드 이름 반환 (Abstract method - 서브클래스에서 구현).
        
        Returns:
            메서드 이름 (예: "Detail", "Search")
        """
        pass


# ============================================================================
# Concrete Implementations
# ============================================================================

class CrawlProductDetail(BaseCrawlMethod):
    """상품 상세 페이지 크롤링 서비스.
    
    Template Method Pattern 적용:
    - crawl() 메서드는 BaseCrawlMethod에서 상속
    - _extract() 메서드로 데이터 추출 로직 구현
    """
    
    def _get_method_name(self) -> str:
        """메서드 이름 반환."""
        return "Detail"
    
    def _extract(
        self,
        url: str,
        index: int,
        dom: str,
        runtime_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """데이터 추출 (상세 페이지).
        
        Args:
            url: 크롤링한 URL
            index: URL 인덱스
            dom: HTML DOM
            runtime_context: 런타임 컨텍스트
        
        Returns:
            추출된 데이터
        """
        # Extractor 없으면 최소 데이터 반환
        if not self.extractor:
            return {
                "_url": url,
                "_index": index,
                "_method": "product_detail",
                **runtime_context
            }
        
        # Extractor로 데이터 추출
        self.log.debug(f"[Detail] Extracting data with Extractor")
        extracted = self.extractor.extract(dom)
        
        # 메타데이터 추가
        extracted["_url"] = url
        extracted["_index"] = index
        extracted["_method"] = "product_detail"
        extracted.update(runtime_context)
        
        return extracted


class CrawlProductSearch(BaseCrawlMethod):
    """상품 검색 결과 페이지 크롤링 서비스.
    
    Template Method Pattern 적용:
    - crawl() 메서드는 BaseCrawlMethod에서 상속
    - _pre_extract() Hook으로 Scroll 로직 구현
    - _extract() 메서드로 리스트 아이템 추출 구현
    """
    
    def _get_method_name(self) -> str:
        """메서드 이름 반환."""
        return "Search"
    
    def _pre_extract(self) -> None:
        """추출 전 Hook 메서드 (Wait, Scroll).
        
        BaseCrawlMethod의 Wait 로직 실행 후, Scroll 로직 추가 실행.
        """
        # 1. 부모 클래스의 Wait hook 실행
        super()._pre_extract()
        
        # 2. Scroll 로직 (선택사항)
        if hasattr(self.policy, 'scroll') and self.policy.scroll:
            scroll_cfg = self.policy.scroll
            strategy = getattr(scroll_cfg, 'strategy', 'none')
            max_scrolls = getattr(scroll_cfg, 'max_scrolls', 0)
            pause_sec = getattr(scroll_cfg, 'scroll_pause_sec', 0.5)
            
            if max_scrolls > 0 and self.navigator:
                self.log.debug(f"[Search] Scrolling: {max_scrolls} times")
                self.navigator.scroll(strategy, max_scrolls, pause_sec)
    
    def _extract(
        self,
        url: str,
        index: int,
        dom: str,
        runtime_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """데이터 추출 (검색 결과 리스트).
        
        Args:
            url: 크롤링한 URL
            index: URL 인덱스
            dom: HTML DOM
            runtime_context: 런타임 컨텍스트
        
        Returns:
            추출된 아이템 리스트
        """
        # Extractor 없으면 빈 리스트 반환
        if not self.extractor:
            self.log.debug("[Search] No extractor available - empty list")
            return []
        
        # Extractor로 리스트 아이템 추출
        self.log.debug("[Search] Extracting list items with Extractor")
        items = self.extractor.extract_list(dom)
        
        # 각 아이템에 메타 정보 추가
        for item_idx, item in enumerate(items, 1):
            item["_url"] = url
            item["_list_index"] = index
            item["_item_index"] = item_idx
            item["_method"] = "product_search"
            item.update(runtime_context)
        
        return items


# ============================================================================
# Factory
# ============================================================================

class CrawlMethodFactory:
    """크롤링 메서드 팩토리.
    
    메서드 타입에 따라 적절한 크롤링 서비스를 생성합니다.
    """
    
    @staticmethod
    def create(
        method: str,
        navigator: Optional['SyncNavigator'],
        extractor: Optional[Any],
        policy: 'CrawlPolicy',
        logger: Any
    ):
        """크롤링 서비스 생성.
        
        Args:
            method: 메서드 타입 ("product_detail", "product_search")
            navigator: SyncNavigator 인스턴스
            extractor: SyncExtractor 인스턴스
            policy: CrawlPolicy
            logger: loguru logger
        
        Returns:
            CrawlProductDetail 또는 CrawlProductSearch 인스턴스
        
        Raises:
            ValueError: 지원하지 않는 메서드 타입
        """
        if method == "product_detail":
            return CrawlProductDetail(
                navigator=navigator,
                extractor=extractor,
                policy=policy,
                logger=logger
            )
        elif method == "product_search":
            return CrawlProductSearch(
                navigator=navigator,
                extractor=extractor,
                policy=policy,
                logger=logger
            )
        else:
            raise ValueError(f"Unsupported crawl method: {method}")
