# -*- coding: utf-8 -*-
# crawl/session.py
from __future__ import annotations
from typing import Dict, Optional
import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from log_utils import LogManager
from .policy import SessionPolicy
from .driver import CrawlDriver

class CrawlSessionBuilder:
    """requests.Session 생성기 (헤더, 쿠키, 재시도 정책 포함)"""
    def __init__(self, driver: CrawlDriver, policy: SessionPolicy, logger: Optional[LogManager] = None):
        self.driver = driver
        self.policy = policy
        self.logger = logger or LogManager("crawl-session").setup()

    def build(self) -> Session:
        s = requests.Session()
        try:
            for ck in self.driver.driver.get_cookies():
                if ck.get("name") and ck.get("value"):
                    s.cookies.set(ck["name"], ck["value"], domain=ck.get("domain"), path=ck.get("path", "/"))
        except Exception:
            pass

        headers: Dict[str, str] = {}
        try:
            ua = self.driver.driver.execute_script("return navigator.userAgent")
            if ua:
                headers["User-Agent"] = ua
        except Exception:
            pass

        if self.policy.referer:
            headers["Referer"] = self.policy.referer
        if self.policy.accept_context:
            headers["Accept_context"] = self.policy.accept_context
        if self.policy.accept_encoding:
            headers["Accept_Encoding"] = self.policy.accept_encoding

        s.headers.update(headers)
        retry_cfg = Retry(
            total=self.policy.retries or 3,
            backoff_factor=self.policy.backoff or 1.0,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        s.mount("http://", HTTPAdapter(max_retries=retry_cfg))
        s.mount("https://", HTTPAdapter(max_retries=retry_cfg))
        return s
