# -*- coding: utf-8 -*-
# crawl_utils/services/navigator.py
# Navigator: 페이지 네비게이션 (Async + Sync 통합)

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Optional

from ..core.interfaces import BrowserController
from ..core.policy import SyncCrawlPolicy, NavigationPolicy, ScrollStrategy, WaitHook, WaitCondition

if TYPE_CHECKING:
    from .adapter import SyncSeleniumAdapter


# class AsyncNavigator:
#     """Asynchronous Navigator for page navigation."""
    
#     def __init__(self, driver: BrowserController, policy: CrawlPolicy):
#         self._driver = driver
#         self._policy = policy
#         self._current_url: str | None = None

#     def _build_url(self, page: int | None = None, query: str | None = None, extra: dict | None = None) -> str:
#         """Build URL from navigation policy.
        
#         Note: Should only be called when self._policy.navigation is not None.
#         """
#         nav = self._policy.navigation
#         if not nav:
#             raise ValueError("Cannot build URL: navigation policy is None")
        
#         if nav.url_template:
#             base = dict(nav.params)
#             if page is not None:
#                 base[nav.page_param] = page
#             if query is not None:
#                 base["query"] = query
#             if extra:
#                 base.update(extra)
#             return nav.url_template.format(**base)
#         suffix = []
#         if query is not None:
#             suffix.append(f"q={query}")
#         if page is not None:
#             suffix.append(f"{nav.page_param}={page}")
#         return str(nav.base_url) + ("?" + "&".join(suffix) if suffix else "")

#     async def load(self, base_url: str, query: str | None = None, params: dict | None = None) -> str:
#         """Navigate to URL (async version).
        
#         Args:
#             base_url: Target URL to load
#             query: Search query (optional, for search method)
#             params: Additional URL parameters (optional)
        
#         Returns:
#             Final loaded URL
#         """
#         # Detail 크롤링: base_url을 직접 사용
#         if not self._policy.navigation:
#             await self._driver.get(base_url)
#             self._current_url = base_url
#             return base_url
        
#         # Search 크롤링: navigation policy로 URL 구성
#         url = self._build_url(page=self._policy.navigation.start_page, query=query, extra=params)
#         await self._driver.get(url)
#         self._current_url = url
#         return url

#     async def paginate(self, page: int) -> str:
#         url = self._build_url(page=page)
#         await self._driver.get(url)
#         self._current_url = url
#         return url

#     async def scroll(self, strategy: ScrollStrategy | str, max_scrolls: int, pause_sec: float) -> None:
#         strategy_value = strategy.value if isinstance(strategy, ScrollStrategy) else str(strategy)
#         if strategy_value == ScrollStrategy.INFINITE.value:
#             for _ in range(max_scrolls):
#                 await self._driver.scroll_bottom()
#                 await asyncio.sleep(pause_sec)

#     async def wait(self, hook: WaitHook | str, selector: str | None, timeout: float, condition: str) -> None:
#         hook_value = hook.value if isinstance(hook, WaitHook) else str(hook)
#         condition_value = condition if isinstance(condition, str) else str(condition)
#         require_visible = condition_value == WaitCondition.VISIBILITY.value

#         if hook_value == WaitHook.CSS.value:
#             await self._driver.wait_css(selector or "html", timeout, visible=require_visible)
#         elif hook_value == WaitHook.XPATH.value:
#             await self._driver.wait_xpath(selector or "//html", timeout, visible=require_visible)
#         else:
#             await asyncio.sleep(max(timeout, 0))

#     async def get_dom(self) -> str:
#         return await self._driver.get_dom()

#     async def execute_js(self, script: str):
#         return await self._driver.execute_js(script)


# ============================================================================
# Sync Navigator: 동기 버전
# ============================================================================


class SyncNavigator:
    """Synchronous Navigator using SyncSeleniumAdapter."""

    def __init__(self, driver: 'SyncSeleniumAdapter', policy: Optional[NavigationPolicy] = None):
        self._driver = driver
        self._policy = policy
        self._current_url: str | None = None

    def _build_url(self, page: int | None = None, query: str | None = None, extra: dict | None = None) -> str:
        """Build URL from navigation policy.
        
        Note: Should only be called when self._policy is not None.
        """
        nav = self._policy
        if not nav:
            raise ValueError("Cannot build URL: navigation policy is None")
        
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
        """Navigate to URL (sync version).
        
        Args:
            base_url: Target URL to load
            query: Search query (optional, for search method)
            params: Additional URL parameters (optional)
        
        Returns:
            Final loaded URL
        """
        # Detail 크롤링: base_url을 직접 사용
        if not self._policy:
            self._driver.get(base_url)
            self._current_url = base_url
            return base_url

        # If a concrete base_url (full URL) is provided, prefer it over navigation policy.
        # This preserves previous behavior where calling load(url) with an explicit
        # detail URL should load that page even if a navigation policy exists.
        try:
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            if parsed.scheme and parsed.netloc:
                self._driver.get(base_url)
                self._current_url = base_url
                return base_url
        except Exception:
            # If parsing fails, fall back to navigation policy behavior
            pass

        # Search 크롤링: navigation policy로 URL 구성
        url = self._build_url(page=self._policy.start_page, query=query, extra=params)
        self._driver.get(url)
        self._current_url = url
        return url

    def paginate(self, page: int) -> str:
        """Navigate to specific page (sync version)."""
        url = self._build_url(page=page)
        self._driver.get(url)  # Direct call
        self._current_url = url
        return url

    def scroll(
        self,
        strategy: ScrollStrategy | str,
        max_scrolls: int,
        pause_sec: float,
        *,
        scroll_count: int | None = None,
        step_px: int = 600,
        randomness: bool = True,
    ) -> None:
        """Scroll page (sync version) according to policy.
        
        Args:
            strategy: Scroll strategy (NONE, INFINITE, STEP)
            max_scrolls: Maximum number of scrolls
            pause_sec: Base pause duration between scrolls
            scroll_count: Optional explicit scroll count (overrides max_scrolls for STEP)
            step_px: Base step size in pixels for STEP strategy
            randomness: Enable human-like random variations (default: True)
                       - Distance: ±20% variation
                       - Pause: ±30% variation
                       - Extra pause: 15% probability, +0.5-2.0s
        """
        import random
        
        strategy_value = strategy.value if isinstance(strategy, ScrollStrategy) else str(strategy)
        if strategy_value == ScrollStrategy.NONE.value:
            return
        
        if strategy_value == ScrollStrategy.INFINITE.value:
            attempts = max(0, max_scrolls)
            for _ in range(attempts):
                self._driver.scroll_bottom()  # Direct call
                if pause_sec > 0:
                    if randomness:
                        # ±30% variation + 15% extra pause
                        actual_pause = pause_sec * random.uniform(0.7, 1.3)
                        if random.random() < 0.15:
                            actual_pause += random.uniform(0.5, 2.0)
                        time.sleep(actual_pause)
                    else:
                        time.sleep(pause_sec)
            return
        
        if strategy_value == ScrollStrategy.STEP.value:
            count = scroll_count if (scroll_count is not None and scroll_count > 0) else max_scrolls
            if count is None or count <= 0:
                count = 1
            scroll_step_fn = getattr(self._driver, "scroll_step", None)
            for _ in range(count):
                # ±20% distance variation
                actual_step = int(step_px * random.uniform(0.8, 1.2)) if randomness else step_px
                
                if callable(scroll_step_fn):
                    scroll_step_fn(actual_step)
                else:
                    self._driver.execute_js(f"window.scrollBy(0, {actual_step});")
                
                if pause_sec > 0:
                    if randomness:
                        # ±30% pause variation + 15% extra pause
                        actual_pause = pause_sec * random.uniform(0.7, 1.3)
                        if random.random() < 0.15:
                            actual_pause += random.uniform(0.5, 2.0)
                        time.sleep(actual_pause)
                    else:
                        time.sleep(pause_sec)
            return
        
        # Placeholder for future strategies (e.g., PAGINATE)

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


