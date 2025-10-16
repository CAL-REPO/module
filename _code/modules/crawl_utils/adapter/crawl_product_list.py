# -*- coding: utf-8 -*-
# crawl_utils/services/crawl.py
# Crawl Pipeline: 전체 크롤링 워크플로우 조율 (Async)

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
from typing import Dict, List, Optional

from ..services.extractor import ExtractorFactory
from ..services.fetcher import HTTPFetcher
from ..core.interfaces import Navigator, ResourceFetcher
from ..core.models import NormalizedItem, SaveSummary
from ..services.normalizer import DataNormalizer
from ..core.policy import CrawlPolicy
from ..services.saver import FileSaver


class CrawlProductList:
    """Coordinates navigation, extraction, normalization, and persistence."""

    def __init__(
        self,
        policy: CrawlPolicy,
        navigator: Navigator,
        *,
        fetcher: Optional[ResourceFetcher] = None,
    ) -> None:
        self.policy = policy
        self.navigator = navigator
        self._owns_fetcher = fetcher is None
        self.fetcher = fetcher or self._create_fetcher()
        self.extractor_factory = ExtractorFactory(policy, navigator, self.fetcher)
        self.normalizer = DataNormalizer(policy.normalization)
        self.saver = FileSaver(policy.storage)
        self._sem = asyncio.Semaphore(policy.concurrency)

    def _create_fetcher(self) -> HTTPFetcher:
        headers = self._load_session_headers()
        return HTTPFetcher(default_headers=headers)

    def _load_session_headers(self) -> Dict[str, str]:
        http_policy = self.policy.http_session
        headers: Dict[str, str] = dict(http_policy.headers)
        path = http_policy.session_json_path
        if http_policy.use_browser_headers and path:
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    source = data.get("headers") if isinstance(data.get("headers"), dict) else data
                    if isinstance(source, dict):
                        headers = {**{k: v for k, v in source.items() if isinstance(v, str)}, **headers}
            except FileNotFoundError:
                pass
            except Exception:
                pass
        return headers

    async def _run_page(self, page: int) -> List[dict]:
        await self.navigator.paginate(page)
        await self.navigator.wait(
            self.policy.wait.hook,
            self.policy.wait.selector,
            self.policy.wait.timeout_sec,
            self.policy.wait.condition.value,
        )
        await self.navigator.scroll(
            self.policy.scroll.strategy,
            self.policy.scroll.max_scrolls,
            self.policy.scroll.scroll_pause_sec,
        )
        extractor = self.extractor_factory.create()
        return await extractor.extract()

    async def run(self) -> SaveSummary:
        await self.navigator.load(str(self.policy.navigation.base_url))
        pages = range(
            self.policy.navigation.start_page,
            self.policy.navigation.start_page + self.policy.navigation.max_pages,
        )

        async def bounded(page: int):
            async with self._sem:
                return await self._run_page(page)

        raw_batches = await asyncio.gather(*[bounded(page) for page in pages])
        flattened = [record for batch in raw_batches for record in batch]
        normalized: List[NormalizedItem] = self.normalizer.normalize(flattened)
        summary = await self.saver.save_many(normalized, fetcher=self.fetcher)
        await self.close()
        return summary

    async def close(self) -> None:
        if self._owns_fetcher and hasattr(self.fetcher, "close"):
            close_fn = getattr(self.fetcher, "close")
            if inspect.iscoroutinefunction(close_fn):
                await close_fn()
            else:
                close_fn()

    async def __aenter__(self) -> "CrawlProductList":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
