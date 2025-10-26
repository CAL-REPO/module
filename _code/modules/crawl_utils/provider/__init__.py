# -*- coding: utf-8 -*-
# crawl_utils/provider/__init__.py
"""Pure WebDriver logic providers (ImageLoad pattern)."""

from crawl_utils.provider.firefox import FirefoxWebDriver
from crawl_utils.provider.policy import (
    WebDriverManagerPolicy,
    FirefoxConfig,
    ChromeConfig,
    EdgeConfig,
    ProviderType,
)
from crawl_utils.provider.browser_version import (
    get_firefox_version,
    get_chrome_version,
    get_edge_version,
    get_browser_version,
    build_user_agent,
)

__all__ = [
    "FirefoxWebDriver",
    "WebDriverManagerPolicy",
    "FirefoxConfig",
    "ChromeConfig",
    "EdgeConfig",
    "ProviderType",
    # Browser version utilities
    "get_firefox_version",
    "get_chrome_version",
    "get_edge_version",
    "get_browser_version",
    "build_user_agent",
]