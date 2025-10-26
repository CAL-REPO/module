# -*- coding: utf-8 -*-
"""crawl_utils/services/pipeline.py

Pipeline Service - 크롤링 파이프라인 통합 (v5.3)

역할:
1. Navigator: 페이지 이동, 대기
2. Scroll: 무한 스크롤 처리 (선택사항)
3. Extractor: DOM/JS/API 방식으로 데이터 추출
4. Normalizer: ItemSaveMeta 생성 (Rule + Auto 통합)

**파일 저장 제외** - PostProcessor(Saver)로 위임

사용 예시:
```python
from crawl_utils.services.pipeline import SyncPipeline
from crawl_utils.core.policy import CrawlPolicy, NormalizationRule
from selenium.webdriver import Firefox

# Rule 생성 (Rule 모드 + Auto 모드 혼합 가능)
rules = [
    NormalizationRule(
        kind="image",
        source="product.images",  # Rule 모드
        directory="{{env.output_dir}}/images",
        name="{{runtime.cas_no}}_{{item.index}}"
    ),
    NormalizationRule(
        kind="text",
        source=None,  # Auto 모드
        auto_infer=True,
        directory="{{env.output_dir}}/texts",
        name="auto_{{item.index}}"
    )
]

# 정책 생성
policy = CrawlPolicy(
    normalization=NormalizationPolicy(rules=rules),
    extractor={"type": "js", "js_snippet": "..."}
)

# Pipeline 생성
driver = Firefox()
pipeline = SyncPipeline(policy, driver)

# 크롤링 실행
items = pipeline.execute(url="https://www.aliexpress.com/item/123.html")

print(f"Extracted {len(items)} items")
# → PostProcessor(Saver)로 전달하여 파일 저장
```
"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from pathlib import Path

from ..core.policy import ItemList, ItemKind
from ..core.policy import CrawlPolicy
from .adapter import SyncSeleniumAdapter
from .navigator import SyncNavigator
from .extractor import SyncExtractorFactory
from .Item_Post_Processor import ItemPostProcessor

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver


class SyncPipeline:
    """Synchronous Crawl Pipeline (v7.0)
    
    크롤링 파이프라인을 통합 관리합니다.
    Navigator → Scroll → Extractor → PostProcessor 순서로 실행.
    
    Attributes:
        policy: CrawlPolicy (PreProcessor에서 생성)
        adapter: SyncSeleniumAdapter (Selenium WebDriver 래퍼)
        navigator: SyncNavigator (페이지 네비게이션)
        extractor_factory: SyncExtractorFactory (추출기 생성)
        post_processor: ItemPostProcessor (v7.0 - Jinja2 제거)
    """
    
    def __init__(self, policy: CrawlPolicy, driver: 'WebDriver'):
        """Initialize Pipeline.
        
        Args:
            policy: CrawlPolicy (PreProcessor에서 생성된 최종 정책)
            driver: Selenium WebDriver
        """
        self.policy = policy
        self.driver = driver
        
        # Adapter 생성 (WebDriver → SyncSeleniumAdapter)
        self.adapter = SyncSeleniumAdapter(driver)
        
        # Navigator 생성
        self.navigator = SyncNavigator(self.adapter, policy)
        
        # Extractor Factory 생성
        self.extractor_factory = SyncExtractorFactory(self.adapter, policy)
        
        # PostProcessor 생성 (v7.0 - Jinja2 제거)
        self.post_processor = self._create_post_processor()
    
    def _create_post_processor(self):
        """ItemPostProcessor 생성 (v7.0)
        
        Returns:
            ItemPostProcessor
        
        Raises:
            ValueError: save가 없을 때
        """
        if not self.policy.save:
            raise ValueError(
                "CrawlPolicy.save is required. "
                "Please define at least one ItemPostProcessPolicy."
            )
        
        return ItemPostProcessor(rules=self.policy.save)
    
    def execute(
        self,
        url: str,
        *,
        query: Optional[str] = None,
        params: Optional[dict] = None
    ) -> List[ItemList]:
        """크롤링 파이프라인 실행
        
        처리 순서:
        1. Navigator: 페이지 로드 (url)
        2. Scroll: 무한 스크롤 처리 (policy.scroll)
        3. Extractor: 데이터 추출 (policy.extractor)
        4. PostProcessor: ItemList 생성 (policy.save)
        
        Args:
            url: 크롤링할 URL
            query: 검색 쿼리 (search 메서드용, 선택사항)
            params: 추가 URL 파라미터 (선택사항)
        
        Returns:
            List[ItemSaveMeta] (파일 저장은 PostProcessor로 위임)
        
        Example:
            >>> pipeline = SyncPipeline(policy, driver)
            >>> items = pipeline.execute("https://www.aliexpress.com/item/123.html")
            >>> print(f"Extracted {len(items)} items")
            100
        """
        # 1. Navigate: 페이지 로드
        final_url = self.navigator.load(url, query=query, params=params)
        
        # 2. Scroll: 무한 스크롤 처리 (선택사항)
        if self.policy.scroll and self.policy.scroll.strategy != "none":
            self.navigator.scroll(
                strategy=self.policy.scroll.strategy,
                max_scrolls=self.policy.scroll.max_scrolls,
                pause_sec=self.policy.scroll.scroll_pause_sec
            )
        
        # 3. Wait: 대기 (선택사항)
        if self.policy.wait and self.policy.wait.hook != "none":
            self.navigator.wait(
                hook=self.policy.wait.hook,
                selector=self.policy.wait.selector,
                timeout=self.policy.wait.timeout_sec,
                condition=self.policy.wait.condition
            )
        
        # 4. Extract: 데이터 추출
        extractor = self.extractor_factory.create()
        
        # SyncJSExtractor는 dom을 사용하지 않지만, signature 호환성을 위해 빈 문자열 전달
        # SyncDOMExtractor는 dom을 필요로 하므로 navigator에서 가져옴
        dom = self.navigator.get_dom() if hasattr(self.navigator, 'get_dom') else ""
        raw_data = extractor.extract(dom=dom)
        
        # 5. Process: ItemList 생성 (v7.0)
        items = self._process_data(raw_data)
        
        return items
    
    def _process_data(self, raw_data: dict) -> List[ItemList]:
        """데이터 후처리 (v7.0 - Jinja2 제거)
        
        Args:
            raw_data: Extractor에서 추출한 데이터
        
        Returns:
            List[ItemList]
        """
        # raw_data를 리스트로 감싸서 전달
        records = [raw_data] if isinstance(raw_data, dict) else raw_data
        return self.post_processor.process(records)


# =============================================================================
# Async Pipeline (향후 구현)
# =============================================================================

class AsyncPipeline:
    """Asynchronous Crawl Pipeline (TODO)
    
    Async 버전 Pipeline은 향후 구현 예정입니다.
    현재는 SyncPipeline만 제공합니다.
    """
    
    def __init__(self, policy: CrawlPolicy, driver: 'WebDriver'):
        raise NotImplementedError(
            "AsyncPipeline is not implemented yet. "
            "Please use SyncPipeline for now."
        )


__all__ = ["SyncPipeline", "AsyncPipeline"]
