# -*- coding: utf-8 -*-
"""
Lightweight pipeline test using dummy driver/fetcher.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import yaml

from crawl_refactor import (
    CrawlPolicy,
    CrawlPipeline,
    NavigationPolicy,
    ScrollPolicy,
    ExtractorPolicy,
    WaitPolicy,
    NormalizationPolicy,
    NormalizationRule,
    StoragePolicy,
    StorageTargetPolicy,
)
from crawl_refactor.fetcher import DummyFetcher
from crawl_refactor.navigator import SeleniumNavigator
from crawl_refactor.policy import WaitCondition, WaitHook, ScrollStrategy, ExtractorType


class DummyDriver:
    async def get(self, url: str) -> None:
        self.url = url

    async def scroll_bottom(self) -> None:
        return None

    async def wait_css(self, selector: str, timeout: float, *, visible: bool = False) -> None:
        return None

    async def wait_xpath(self, selector: str, timeout: float, *, visible: bool = False) -> None:
        return None

    async def get_dom(self) -> str:
        return "<html><body><div class='result-item'><img src='http://example.com/a.jpg' alt='Item A'></div></body></html>"

    async def execute_js(self, script: str):
        return [
            {"url": "http://example.com/a.jpg", "caption": "Item A"},
            {"url": "http://example.com/b.jpg", "caption": "Item B"},
        ]


async def load_policy_from_yaml(path: Path) -> CrawlPolicy:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    data = raw["crawl"]
    return CrawlPolicy.model_validate(data)


async def main() -> None:
    cfg_path = Path(__file__).resolve().parent.parent / "configs" / "crawl_refactor.yaml"
    policy = await load_policy_from_yaml(cfg_path)

    driver = DummyDriver()
    navigator = SeleniumNavigator(driver, policy)
    fetcher = DummyFetcher()

    pipeline = CrawlPipeline(policy, navigator, fetcher=fetcher)
    summary = await pipeline.run()

    print({kind: len(items) for kind, items in summary.artifacts.items()})
    for artifact in summary.flatten():
        print(artifact.status, artifact.path if artifact.path else "(no path)")


if __name__ == "__main__":
    asyncio.run(main())
