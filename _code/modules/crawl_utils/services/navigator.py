# -*- coding: utf-8 -*-
# crawl_utils/services/navigator.py
# Navigator: 페이지 네비게이션 (Async + Sync 통합)

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from ..core.interfaces import BrowserController
from ..core.policy import CrawlPolicy, ScrollStrategy, WaitHook, WaitCondition

if TYPE_CHECKING:
    from .adapter import SyncSeleniumAdapter


class SeleniumNavigator:
    def __init__(self, driver: BrowserController, policy: CrawlPolicy):
        self._driver = driver
        self._policy = policy
        self._current_url: str | None = None

    def _build_url(self, page: int | None = None, query: str | None = None, extra: dict | None = None) -> str:
        nav = self._policy.navigation
        if nav.url_template:
            base = dict(nav.params)
            if page is not None:
                base[nav.page_param] = page
            if query is not None:
                base["query"] = query
            if extra:
                base.update(extra)
            return nav.url_template.format(**base)
        suffix = []
        if query is not None:
            suffix.append(f"q={query}")
        if page is not None:
            suffix.append(f"{nav.page_param}={page}")
        return str(nav.base_url) + ("?" + "&".join(suffix) if suffix else "")

    async def load(self, base_url: str, query: str | None = None, params: dict | None = None) -> str:
        url = base_url or str(self._policy.navigation.base_url)
        url = self._build_url(page=self._policy.navigation.start_page, query=query, extra=params)
        await self._driver.get(url)
        self._current_url = url
        return url

    async def paginate(self, page: int) -> str:
        url = self._build_url(page=page)
        await self._driver.get(url)
        self._current_url = url
        return url

    async def scroll(self, strategy: ScrollStrategy | str, max_scrolls: int, pause_sec: float) -> None:
        strategy_value = strategy.value if isinstance(strategy, ScrollStrategy) else str(strategy)
        if strategy_value == ScrollStrategy.INFINITE.value:
            for _ in range(max_scrolls):
                await self._driver.scroll_bottom()
                await asyncio.sleep(pause_sec)

    async def wait(self, hook: WaitHook | str, selector: str | None, timeout: float, condition: str) -> None:
        hook_value = hook.value if isinstance(hook, WaitHook) else str(hook)
        condition_value = condition if isinstance(condition, str) else str(condition)
        require_visible = condition_value == WaitCondition.VISIBILITY.value

        if hook_value == WaitHook.CSS.value:
            await self._driver.wait_css(selector or "html", timeout, visible=require_visible)
        elif hook_value == WaitHook.XPATH.value:
            await self._driver.wait_xpath(selector or "//html", timeout, visible=require_visible)
        else:
            await asyncio.sleep(max(timeout, 0))

    async def get_dom(self) -> str:
        return await self._driver.get_dom()

    async def execute_js(self, script: str):
        return await self._driver.execute_js(script)


# ============================================================================
# Sync Navigator: 동기 버전
# ============================================================================


class SyncNavigator:
    """Synchronous Navigator using SyncSeleniumAdapter."""

    def __init__(self, driver: 'SyncSeleniumAdapter', policy: CrawlPolicy):
        self._driver = driver
        self._policy = policy
        self._current_url: str | None = None

    def _build_url(self, page: int | None = None, query: str | None = None, extra: dict | None = None) -> str:
        nav = self._policy.navigation
        if nav.url_template:
            base = dict(nav.params)
            if page is not None:
                base[nav.page_param] = page
            if query is not None:
                base["query"] = query
            if extra:
                base.update(extra)
            return nav.url_template.format(**base)
        suffix = []
        if query is not None:
            suffix.append(f"q={query}")
        if page is not None:
            suffix.append(f"{nav.page_param}={page}")
        return str(nav.base_url) + ("?" + "&".join(suffix) if suffix else "")

    def load(self, base_url: str, query: str | None = None, params: dict | None = None) -> str:
        """Navigate to URL (sync version)."""
        url = base_url or str(self._policy.navigation.base_url)
        url = self._build_url(page=self._policy.navigation.start_page, query=query, extra=params)
        self._driver.get(url)  # Direct call
        self._current_url = url
        return url

    def paginate(self, page: int) -> str:
        """Navigate to specific page (sync version)."""
        url = self._build_url(page=page)
        self._driver.get(url)  # Direct call
        self._current_url = url
        return url

    def scroll(self, strategy: ScrollStrategy | str, max_scrolls: int, pause_sec: float) -> None:
        """Scroll page (sync version)."""
        strategy_value = strategy.value if isinstance(strategy, ScrollStrategy) else str(strategy)
        if strategy_value == ScrollStrategy.INFINITE.value:
            for _ in range(max_scrolls):
                self._driver.scroll_bottom()  # Direct call
                time.sleep(pause_sec)  # Use time.sleep instead of asyncio.sleep

    def wait(self, hook: WaitHook | str, selector: str | None, timeout: float, condition: str) -> None:
        """Wait for condition (sync version)."""
        hook_value = hook.value if isinstance(hook, WaitHook) else str(hook)
        condition_value = condition if isinstance(condition, str) else str(condition)
        require_visible = condition_value == WaitCondition.VISIBILITY.value

        if hook_value == WaitHook.CSS.value:
            self._driver.wait_css(selector or "html", timeout, visible=require_visible)  # Direct call
        elif hook_value == WaitHook.XPATH.value:
            self._driver.wait_xpath(selector or "//html", timeout, visible=require_visible)  # Direct call
        else:
            time.sleep(max(timeout, 0))  # Use time.sleep

    def get_dom(self) -> str:
        """Get page DOM (sync version)."""
        return self._driver.get_dom()  # Direct call

    def execute_js(self, script: str):
        """Execute JavaScript (sync version)."""
        return self._driver.execute_js(script)  # Direct call


# Backward compatibility alias
Navigator = SeleniumNavigator
