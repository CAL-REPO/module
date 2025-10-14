# -*- coding: utf-8 -*-
# crawl_utils/async_browser.py
# Selenium 기반 FirefoxDriver를 비동기로 감싼 BrowserController 구현체

from __future__ import annotations

import asyncio
from typing import Any, Callable
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException, WebDriverException

from firefox.driver import FirefoxDriver
from firefox.config import FirefoxConfig
from crawl_refactor.interfaces import BrowserController  # ✅ 변경된 인터페이스 사용

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _to_thread(func: Callable, *args, **kwargs):
    return asyncio.to_thread(func, *args, **kwargs)


class AsyncBrowser(BrowserController):
    """
    비동기 Selenium 기반 BrowserController.
    FirefoxDriver를 내부에 주입받아 동기 호출을 async wrapper로 감싼다.
    """

    def __init__(self, driver: FirefoxDriver):
        self._fx = driver
        self.config: FirefoxConfig = driver.config

    # ------------------------------------------------------------
    # 내부 helper
    # ------------------------------------------------------------
    @property
    def _drv(self) -> WebDriver:
        # FirefoxDriver 내부에서 lazy-create됨
        return self._fx.driver

    # ------------------------------------------------------------
    # BrowserController protocol 구현
    # ------------------------------------------------------------
    async def get(self, url: str) -> None:
        await _to_thread(self._drv.get, url)

    async def scroll_bottom(
        self, step: int = 600, delay: float = 0.1, max_scrolls: int = 10
    ) -> None:
        async def _scroll_once():
            await self.execute_js(f"window.scrollBy(0, {step});")

        for _ in range(max_scrolls):
            await _scroll_once()
            await asyncio.sleep(delay)

    async def wait_css(self, selector: str, timeout: float = 10.0) -> bool:
        try:
            def _wait():
                WebDriverWait(self._drv, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
            await _to_thread(_wait)
            return True
        except TimeoutException:
            return False

    async def wait_xpath(self, xpath: str, timeout: float = 10.0) -> bool:
        try:
            def _wait():
                WebDriverWait(self._drv, timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
            await _to_thread(_wait)
            return True
        except TimeoutException:
            return False

    async def get_dom(self) -> str:
        def _read() -> str:
            return self._drv.page_source
        return await _to_thread(_read)

    async def execute_js(self, script: str) -> Any:
        def _run():
            return self._drv.execute_script(script)
        try:
            return await _to_thread(_run)
        except WebDriverException:
            return None

    async def quit(self) -> None:
        def _quit():
            self._fx.quit()
        await _to_thread(_quit)

    # ------------------------------------------------------------
    # context 관리
    # ------------------------------------------------------------
    async def __aenter__(self) -> AsyncBrowser:
        def _enter():
            self._fx.__enter__()
            return self
        return await _to_thread(_enter)

    async def __aexit__(self, exc_type, exc, tb):
        def _exit():
            try:
                self._fx.__exit__(exc_type, exc, tb)
            except Exception:
                pass
        await _to_thread(_exit)
