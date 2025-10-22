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

__all__ = [
    "FirefoxWebDriver",
    "WebDriverManagerPolicy",
    "FirefoxConfig",
    "ChromeConfig",
    "EdgeConfig",
    "ProviderType",
]