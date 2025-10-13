# -*- coding: utf-8 -*-
# crawl_refactor/extractor.py

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .interfaces import Navigator, ResourceFetcher
from .policy import CrawlPolicy, ExtractorType

try:  # optional dependency for DOM parsing
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency
    BeautifulSoup = None  # type: ignore


class DOMExtractor:
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


class JSExtractor:
    def __init__(self, navigator: Navigator, policy: CrawlPolicy):
        self.navigator = navigator
        self.policy = policy

    async def extract(self) -> List[Dict[str, Any]]:
        snippet = self.policy.extractor.js_snippet or "return [];"
        result = await self.navigator.execute_js(snippet)
        if not isinstance(result, list):
            result = [result]
        return [{"kind": "js", "payload": item} for item in result]


class APIExtractor:
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


class ExtractorFactory:
    def __init__(self, policy: CrawlPolicy, navigator: Navigator, fetcher: Optional[ResourceFetcher] = None):
        self.policy = policy
        self.navigator = navigator
        self.fetcher = fetcher

    def create(self):
        etype = self.policy.extractor.type
        if etype == ExtractorType.DOM:
            return DOMExtractor(self.navigator, self.policy)
        if etype == ExtractorType.JS:
            return JSExtractor(self.navigator, self.policy)
        if etype == ExtractorType.API:
            if not self.fetcher:
                raise ValueError("API extractor requires a ResourceFetcher instance.")
            return APIExtractor(self.fetcher, self.policy)
        raise ValueError(f"Unsupported extractor type: {etype}")
