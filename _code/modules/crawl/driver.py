# -*- coding: utf-8 -*-
# crawl/driver.py
from __future__ import annotations
from typing import Optional
from crawl.policy import CrawlPolicy, DriverType
from firefox.driver import FirefoxDriver

class CrawlDriver:
    """브라우저 드라이버 어댑터 (Firefox/Chrome)"""
    def __init__(self, policy: CrawlPolicy):
        self.policy = policy
        self._drv = self._create()

    def _create(self):
        if self.policy.driver_type == DriverType.FIREFOX:
            cfg = self.policy.firefox or None
            return FirefoxDriver(cfg)
        elif self.policy.driver_type == DriverType.CHROME:
            raise NotImplementedError("ChromeDriver not implemented yet.")
        else:
            raise ValueError(f"Unsupported driver type: {self.policy.driver_type}")

    @property
    def driver(self):
        return self._drv.driver

    def quit(self):
        self._drv.quit()
