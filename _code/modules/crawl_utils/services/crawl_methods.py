# -*- coding: utf-8 -*-
"""crawl_utils/services/crawl_methods.py

메서드별 크롤링 로직을 분리한 서비스 모듈.

책임:
1. product_detail - 상품 상세 페이지 크롤링
2. product_search - 상품 검색 결과 크롤링
3. 각 메서드는 Navigator, Extractor를 사용하여 데이터 추출

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

from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.policy import CrawlPolicy
    from .navigator import SyncNavigator


class CrawlProductDetail:
    """상품 상세 페이지 크롤링 서비스.
    
    Pipeline:
    1. Navigator로 페이지 로드
    2. Wait hook 실행 (policy 기반)
    3. Extractor로 데이터 추출
    4. 결과 반환
    """
    
    def __init__(
        self,
        navigator: Optional['SyncNavigator'],
        extractor: Optional[Any],  # SyncExtractor (TODO: 타입 정의)
        policy: 'CrawlPolicy',
        logger: Any  # loguru logger
    ):
        self.navigator = navigator
        self.extractor = extractor
        self.policy = policy
        self.log = logger
    
    def crawl(
        self,
        urls: List[str],
        runtime_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """상품 상세 페이지 크롤링.
        
        Args:
            urls: 크롤링할 URL 리스트
            runtime_context: 런타임 컨텍스트 (cas_no 등)
        
        Returns:
            추출된 데이터 리스트
        """
        results: List[Dict[str, Any]] = []
        
        for idx, url in enumerate(urls, 1):
            self.log.info(f"[Detail {idx}/{len(urls)}] Processing: {url}")
            
            try:
                data = self._crawl_single_url(url, idx, runtime_context)
                results.append(data)
                self.log.success(f"  Loaded: {data.get('page_title', 'Unknown')[:50]}")
                
            except Exception as e:
                self.log.error(f"  Failed to crawl {url}: {e}")
                import traceback
                self.log.debug(f"  Traceback: {traceback.format_exc()}")
                
                # 에러 데이터 추가
                results.append({
                    "_url": url,
                    "_index": idx,
                    "_method": "product_detail",
                    "_error": str(e),
                    **runtime_context
                })
                continue
        
        return results
    
    def _crawl_single_url(
        self,
        url: str,
        index: int,
        runtime_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """단일 URL 크롤링.
        
        Args:
            url: 크롤링할 URL
            index: URL 인덱스
            runtime_context: 런타임 컨텍스트
        
        Returns:
            추출된 데이터
        """
        # Navigator 확인
        if not self.navigator:
            raise ValueError("Navigator is required for product_detail crawling")
        
        # 1. 페이지 로드
        self.log.debug(f"[Detail] Loading URL with Navigator: {url}")
        self.navigator.load(url)
        
        # 2. Wait hook 실행 (policy 설정 기반)
        if hasattr(self.policy, 'wait') and self.policy.wait:
            wait_cfg = self.policy.wait
            timeout = getattr(wait_cfg, 'timeout_sec', 10.0)
            hook = getattr(wait_cfg, 'hook', None)
            selector = getattr(wait_cfg, 'selector', None)
            condition = getattr(wait_cfg, 'condition', 'presence')
            
            if hook:
                self.log.debug(f"[Detail] Waiting: hook={hook}, timeout={timeout}s")
                self.navigator.wait(hook, selector, timeout, condition)
        
        # 3. DOM 가져오기
        dom = self.navigator.get_dom()
        
        # 4. 기본 데이터 구성
        data = {
            "_url": url,
            "_index": index,
            "_method": "product_detail",
            "_site": self.policy.site,
            "dom_length": len(dom),
            "loaded_url": self.navigator._current_url or url,
        }
        
        # 5. Extractor로 데이터 추출
        if self.extractor:
            self.log.debug("[Detail] Extracting data with Extractor")
            try:
                extracted_data = self.extractor.extract(dom)
                data.update(extracted_data)
            except Exception as e:
                self.log.warning(f"[Detail] Extractor failed: {e}")
                data["_extractor_error"] = str(e)
        else:
            self.log.debug("[Detail] No extractor available - basic data only")
        
        # 6. Runtime context 추가
        data.update(runtime_context)
        
        return data


class CrawlProductSearch:
    """상품 검색 결과 페이지 크롤링 서비스.
    
    Pipeline:
    1. Navigator로 페이지 로드
    2. Scroll (선택사항)
    3. Extractor로 리스트 아이템 추출
    4. Pagination (선택사항)
    5. 결과 반환
    """
    
    def __init__(
        self,
        navigator: Optional['SyncNavigator'],
        extractor: Optional[Any],  # SyncExtractor
        policy: 'CrawlPolicy',
        logger: Any  # loguru logger
    ):
        self.navigator = navigator
        self.extractor = extractor
        self.policy = policy
        self.log = logger
    
    def crawl(
        self,
        urls: List[str],
        runtime_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """상품 검색 결과 페이지 크롤링.
        
        Args:
            urls: 크롤링할 URL 리스트
            runtime_context: 런타임 컨텍스트
        
        Returns:
            추출된 데이터 리스트 (각 URL당 여러 상품)
        """
        results: List[Dict[str, Any]] = []
        
        for idx, url in enumerate(urls, 1):
            self.log.info(f"[Search {idx}/{len(urls)}] Processing: {url}")
            
            try:
                items = self._crawl_single_url(url, idx, runtime_context)
                
                # Runtime context를 각 아이템에 추가
                for item in items:
                    item.update(runtime_context)
                    results.append(item)
                
                self.log.success(f"  Extracted: {len(items)} items")
                
            except Exception as e:
                self.log.error(f"  Failed to crawl {url}: {e}")
                import traceback
                self.log.debug(f"  Traceback: {traceback.format_exc()}")
                continue
        
        return results
    
    def _crawl_single_url(
        self,
        url: str,
        index: int,
        runtime_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """단일 URL 크롤링.
        
        Args:
            url: 크롤링할 URL
            index: URL 인덱스
            runtime_context: 런타임 컨텍스트
        
        Returns:
            추출된 아이템 리스트
        """
        # Navigator 확인
        if not self.navigator:
            raise ValueError("Navigator is required for product_search crawling")
        
        # 1. 페이지 로드
        self.log.debug(f"[Search] Loading URL with Navigator: {url}")
        self.navigator.load(url)
        
        # 2. Wait hook 실행
        if hasattr(self.policy, 'wait') and self.policy.wait:
            wait_cfg = self.policy.wait
            timeout = getattr(wait_cfg, 'timeout_sec', 10.0)
            hook = getattr(wait_cfg, 'hook', None)
            selector = getattr(wait_cfg, 'selector', None)
            condition = getattr(wait_cfg, 'condition', 'presence')
            
            if hook:
                self.log.debug(f"[Search] Waiting: hook={hook}, timeout={timeout}s")
                self.navigator.wait(hook, selector, timeout, condition)
        
        # 3. Scroll (선택사항)
        if hasattr(self.policy, 'scroll') and self.policy.scroll:
            scroll_cfg = self.policy.scroll
            strategy = getattr(scroll_cfg, 'strategy', 'none')
            max_scrolls = getattr(scroll_cfg, 'max_scrolls', 0)
            pause_sec = getattr(scroll_cfg, 'scroll_pause_sec', 0.5)
            
            if max_scrolls > 0:
                self.log.debug(f"[Search] Scrolling: {max_scrolls} times")
                self.navigator.scroll(strategy, max_scrolls, pause_sec)
        
        # 4. DOM 가져오기
        dom = self.navigator.get_dom()
        
        # 5. Extractor로 리스트 아이템 추출
        if self.extractor:
            self.log.debug("[Search] Extracting list items with Extractor")
            try:
                items = self.extractor.extract_list(dom)
                
                # 각 아이템에 메타 정보 추가
                for item_idx, item in enumerate(items, 1):
                    item["_url"] = url
                    item["_list_index"] = index
                    item["_item_index"] = item_idx
                    item["_method"] = "product_search"
                    item["_site"] = self.policy.site
                
                return items
                
            except Exception as e:
                self.log.warning(f"[Search] Extractor failed: {e}")
                # Placeholder 데이터 반환
                return [{
                    "_url": url,
                    "_list_index": index,
                    "_method": "product_search",
                    "_extractor_error": str(e)
                }]
        else:
            self.log.debug("[Search] No extractor available - placeholder data")
            # Placeholder 데이터 (3개 상품 시뮬레이션)
            return [
                {
                    "_url": url,
                    "_list_index": index,
                    "_item_index": i,
                    "_method": "product_search",
                    "_site": self.policy.site,
                    "title": f"Product {i}",
                    "price": 10.0 * i,
                }
                for i in range(1, 4)
            ]


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
