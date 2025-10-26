# crawl_utils/services/session_bridge.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import requests
from http.cookiejar import Cookie
from typing import Optional

class SessionBridge:
    """
    WebDriver ↔ requests.Session 브리지 (MVP)
    - UA/Accept-Language/Proxy 동기화
    - WebDriver 쿠키 → HTTP 세션 주입(sync)
    - 인증성 실패(401/302) 시 재동기화(resync)
    """
    def __init__(self, webdriver, user_agent: Optional[str], accept_language: Optional[str], proxy: Optional[str]):
        self.webdriver = webdriver
        self.http = requests.Session()

        # UA/AL: 정책값 우선, 없으면 WebDriver/기본 (삼항)
        ua = user_agent if user_agent else self._ua_from_webdriver()
        self.http.headers["User-Agent"] = ua
        self.http.headers["Accept-Language"] = accept_language if accept_language else "en-US"

        # Proxy
        if proxy:
            self.http.proxies.update({"http": proxy, "https": proxy})

    @classmethod
    def from_webdriver(cls, webdriver, user_agent: Optional[str], accept_language: Optional[str], proxy: Optional[str]):
        return cls(webdriver=webdriver, user_agent=user_agent, accept_language=accept_language, proxy=proxy)

    @property
    def http_session(self) -> requests.Session:
        return self.http

    def ensure_headers(self, referer: Optional[str], default_referer: Optional[str]) -> None:
        # per-request Referer: 요청마다 호출 가능
        self.http.headers["Referer"] = referer if referer else (default_referer if default_referer else "")

    def sync_cookies_from_webdriver(self, domain: str) -> None:
        # WebDriver의 런타임 쿠키를 HTTP 세션 CookieJar로 주입(도메인 매칭)
        for c in self.webdriver.get_cookies():
            dom = c.get("domain", "")
            if not dom:
                continue
            match = (domain.endswith(dom) or dom.endswith(domain))
            if not match:
                continue
            self.http.cookies.set_cookie(Cookie(
                version=0, name=c["name"], value=c["value"],
                port=None, port_specified=False,
                domain=dom, domain_specified=True, domain_initial_dot=dom.startswith("."),
                path=c.get("path", "/"), path_specified=True,
                secure=c.get("secure", False),
                expires=c.get("expiry", None),
                discard=False, comment=None, comment_url=None,
                rest={"HttpOnly": c.get("httpOnly", None)}, rfc2109=False
            ))

    def resync(self, domain: str) -> None:
        # 인증 오류 등 발생 시: 해당 도메인 쿠키 비우고 WebDriver에서 재수집
        try:
            if domain:
                self.http.cookies.clear(domain=domain)
        except Exception:
            pass
        self.sync_cookies_from_webdriver(domain)

    def _ua_from_webdriver(self) -> str:
        try:
            return self.webdriver.execute_script("return navigator.userAgent")
        except Exception:
            return "Mozilla/5.0"
