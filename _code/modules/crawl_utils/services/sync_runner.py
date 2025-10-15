# -*- coding: utf-8 -*-
"""Synchronous wrapper for async crawl operations.

Provides a simple synchronous interface to run async crawl pipelines.
Useful for scripts, notebooks, and simple automation tasks.
"""

import asyncio
from typing import List, Optional, Union
from pathlib import Path

from crawl_utils.core.policy import CrawlPolicy, ExecutionMode
from crawl_utils.core.models import NormalizedItem
from crawl_utils.services.adapter import AsyncSeleniumAdapter
from crawl_utils.services.navigator import SeleniumNavigator
from crawl_utils.services.extractor import DOMExtractor, ExtractorFactory
from crawl_utils.services.normalizer import DataNormalizer
from crawl_utils.services.saver import FileSaver
from crawl_utils.services.fetcher import ResourceFetcher


class SyncCrawlRunner:
    """Synchronous wrapper for async crawl pipeline.
    
    이 클래스는 비동기 크롤링 파이프라인을 동기 방식으로 실행할 수 있게 해줍니다.
    내부적으로 asyncio.run()을 사용하여 이벤트 루프를 관리합니다.
    
    Attributes:
        policy: Crawl policy configuration
        
    Example:
        >>> policy = CrawlPolicy(...)
        >>> runner = SyncCrawlRunner(policy)
        >>> items = runner.run_crawl(driver)
        >>> print(f"Crawled {len(items)} items")
    """
    
    def __init__(self, policy: CrawlPolicy):
        """Initialize sync crawl runner.
        
        Args:
            policy: Crawl policy configuration
        """
        self.policy = policy
    
    def run_crawl(
        self,
        driver,
        *,
        max_pages: Optional[int] = None,
    ) -> List[NormalizedItem]:
        """Run complete crawl pipeline synchronously.
        
        페이지 순회 → 데이터 추출 → 정규화 → 저장을 동기 방식으로 실행합니다.
        
        Args:
            driver: WebDriver instance (FirefoxWebDriver 등)
            max_pages: Maximum pages to crawl (None = use policy value)
            
        Returns:
            List of normalized items
            
        Example:
            >>> from crawl_utils import FirefoxWebDriver, SyncCrawlRunner
            >>> with FirefoxWebDriver(config) as driver:
            ...     runner = SyncCrawlRunner(policy)
            ...     items = runner.run_crawl(driver, max_pages=5)
        """
        return asyncio.run(self._async_crawl(driver, max_pages=max_pages))
    
    def run_single_page(
        self,
        driver,
        url: str,
    ) -> List[NormalizedItem]:
        """Crawl single page synchronously.
        
        단일 페이지에서 데이터를 추출하고 저장합니다.
        
        Args:
            driver: WebDriver instance
            url: Target URL
            
        Returns:
            List of normalized items from the page
            
        Example:
            >>> runner = SyncCrawlRunner(policy)
            >>> items = runner.run_single_page(driver, "https://example.com/product/123")
        """
        return asyncio.run(self._async_single_page(driver, url))
    
    def extract_only(
        self,
        driver,
        url: str,
    ) -> List[NormalizedItem]:
        """Extract data without saving (synchronous).
        
        데이터를 추출하고 정규화만 하고 저장하지 않습니다.
        
        Args:
            driver: WebDriver instance
            url: Target URL
            
        Returns:
            List of normalized items (not saved)
        """
        return asyncio.run(self._async_extract_only(driver, url))
    
    # -------------------------------------------------------------------------
    # Async implementations (called by sync wrappers)
    # -------------------------------------------------------------------------
    
    async def _async_crawl(
        self,
        driver,
        max_pages: Optional[int] = None,
    ) -> List[NormalizedItem]:
        """Async implementation of full crawl."""
        async with AsyncSeleniumAdapter(driver) as browser:
            navigator = SeleniumNavigator(self.policy.navigation, browser)
            extractor = ExtractorFactory.create(self.policy.extractor, browser)
            normalizer = DataNormalizer(self.policy.normalization)
            saver = FileSaver(self.policy.storage)
            
            all_items: List[NormalizedItem] = []
            pages_to_crawl = max_pages or self.policy.navigation.max_pages
            
            for page_num in range(1, pages_to_crawl + 1):
                # Navigate to page
                url = navigator.build_url(page_num)
                await navigator.navigate(url, self.policy.wait, self.policy.scroll)
                
                # Extract and normalize
                records = await extractor.extract()
                items = normalizer.normalize(records, section=f"page{page_num}")
                
                # Save items
                if items:
                    fetcher = ResourceFetcher(session=None)  # TODO: Add session support
                    await saver.save_many(items, fetcher)
                    all_items.extend(items)
            
            return all_items
    
    async def _async_single_page(
        self,
        driver,
        url: str,
    ) -> List[NormalizedItem]:
        """Async implementation of single page crawl."""
        async with AsyncSeleniumAdapter(driver) as browser:
            navigator = SeleniumNavigator(self.policy.navigation, browser)
            extractor = ExtractorFactory.create(self.policy.extractor, browser)
            normalizer = DataNormalizer(self.policy.normalization)
            saver = FileSaver(self.policy.storage)
            
            # Navigate
            await navigator.navigate(url, self.policy.wait, self.policy.scroll)
            
            # Extract and normalize
            records = await extractor.extract()
            items = normalizer.normalize(records, section="single")
            
            # Save
            if items:
                fetcher = ResourceFetcher(session=None)
                await saver.save_many(items, fetcher)
            
            return items
    
    async def _async_extract_only(
        self,
        driver,
        url: str,
    ) -> List[NormalizedItem]:
        """Async implementation of extract-only."""
        async with AsyncSeleniumAdapter(driver) as browser:
            navigator = SeleniumNavigator(self.policy.navigation, browser)
            extractor = ExtractorFactory.create(self.policy.extractor, browser)
            normalizer = DataNormalizer(self.policy.normalization)
            
            # Navigate
            await navigator.navigate(url, self.policy.wait, self.policy.scroll)
            
            # Extract and normalize (no save)
            records = await extractor.extract()
            items = normalizer.normalize(records, section="extract")
            
            return items


# Convenience function
def run_sync_crawl(
    policy: Union[CrawlPolicy, str, Path, dict],
    driver,
    *,
    max_pages: Optional[int] = None,
) -> List[NormalizedItem]:
    """Run crawl synchronously with policy auto-loading.
    
    편의 함수: YAML/dict에서 policy를 로드하고 즉시 크롤링을 실행합니다.
    
    Args:
        policy: CrawlPolicy object, YAML path, or dict config
        driver: WebDriver instance
        max_pages: Maximum pages to crawl
        
    Returns:
        List of normalized items
        
    Example:
        >>> from crawl_utils import FirefoxWebDriver, run_sync_crawl
        >>> 
        >>> with FirefoxWebDriver(config) as driver:
        ...     items = run_sync_crawl("configs/crawl.yaml", driver, max_pages=10)
        ...     print(f"Got {len(items)} items")
    """
    # Load policy if needed
    if not isinstance(policy, CrawlPolicy):
        from cfg_utils import ConfigLoader
        loader = ConfigLoader(policy)
        policy = loader.as_model(CrawlPolicy)
    
    # Force sync mode
    policy.execution_mode = ExecutionMode.SYNC
    
    # Run
    runner = SyncCrawlRunner(policy)
    return runner.run_crawl(driver, max_pages=max_pages)
