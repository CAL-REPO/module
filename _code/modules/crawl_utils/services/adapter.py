# -*- coding: utf-8 -*-
# crawl_utils/services/adapter.py
# Selenium Adapter: Async + Sync 통합

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException, WebDriverException

from crawl_utils.core.interfaces import BrowserController
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _to_thread(func: Callable, *args, **kwargs):
    return asyncio.to_thread(func, *args, **kwargs)


# ============================================================
# Async Adapter
# ============================================================

class AsyncSeleniumAdapter(BrowserController):
    """
    Selenium Adapter: Selenium WebDriver → BrowserController Protocol
    
    WebDriver 인스턴스를 주입받아 동기 API를 비동기로 변환합니다.
    Selenium의 동기 API를 asyncio.to_thread()로 비동기화하여 BrowserController Protocol을 구현합니다.
    
    Args:
        driver: WebDriver 호환 driver (duck typing)
    """

    def __init__(self, driver):
        """Initialize adapter with WebDriver-compatible driver.
        
        Note: driver는 duck typing으로 처리 (WebDriver 인터페이스 호환)
        FirefoxDriver, ChromeDriver 등 모든 Selenium WebDriver 호환 가능
        """
        self._fx = driver
        self.config = getattr(driver, 'config', None)

    # ------------------------------------------------------------
    # 내부 helper
    # ------------------------------------------------------------
    @property
    def _drv(self) -> WebDriver:
        # FirefoxDriver 내부에서 lazy-create됨
        # duck typing: driver 속성이 있으면 사용, 없으면 driver 자체가 WebDriver
        return getattr(self._fx, 'driver', self._fx)

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
    async def __aenter__(self) -> "SeleniumAdapter":
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


# ============================================================
# Sync Adapter
# ============================================================

class SyncSeleniumAdapter:
    """
    Sync Selenium Adapter: Selenium WebDriver 직접 사용 (동기)
    
    WebDriver의 동기 API를 그대로 사용합니다.
    asyncio.to_thread() 없이 직접 호출하므로 빠르고 간단합니다.
    
    Args:
        driver: WebDriver 호환 driver (duck typing)
    """

    def __init__(self, driver):
        """Initialize adapter with WebDriver-compatible driver."""
        self._fx = driver
        self.config = getattr(driver, 'config', None)

    @property
    def _drv(self) -> WebDriver:
        return getattr(self._fx, 'driver', self._fx)

    def get(self, url: str) -> None:
        """페이지 로드 (동기)"""
        self._drv.get(url)

    def scroll_bottom(
        self, step: int = 600, delay: float = 0.1, max_scrolls: int = 10
    ) -> None:
        """스크롤 (동기)"""
        for _ in range(max_scrolls):
            self._drv.execute_script(f"window.scrollBy(0, {step});")
            time.sleep(delay)

    def wait_css(self, selector: str, timeout: float = 10.0, *, visible: bool = False) -> bool:
        """CSS 선택자 대기 (동기)"""
        try:
            condition = EC.visibility_of_element_located if visible else EC.presence_of_element_located
            WebDriverWait(self._drv, timeout).until(
                condition((By.CSS_SELECTOR, selector))
            )
            return True
        except TimeoutException:
            return False

    def wait_xpath(self, xpath: str, timeout: float = 10.0, *, visible: bool = False) -> bool:
        """XPath 대기 (동기)"""
        try:
            condition = EC.visibility_of_element_located if visible else EC.presence_of_element_located
            WebDriverWait(self._drv, timeout).until(
                condition((By.XPATH, xpath))
            )
            return True
        except TimeoutException:
            return False

    def get_dom(self) -> str:
        """DOM 가져오기 (동기)"""
        return self._drv.page_source

    def execute_js(self, script: str) -> Any:
        """JavaScript 실행 (동기)"""
        try:
            return self._drv.execute_script(script)
        except WebDriverException:
            return None

    def quit(self) -> None:
        """브라우저 종료 (동기)"""
        self._fx.quit()

    def __enter__(self) -> "SyncSeleniumAdapter":
        """Context manager 진입 (동기)"""
        self._fx.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        """Context manager 종료 (동기)"""
        try:
            self._fx.__exit__(exc_type, exc, tb)
        except Exception:
            pass


# Backward compatibility alias
SeleniumAdapter = AsyncSeleniumAdapter
