# -*- coding: utf-8 -*-
# crawl_refactor/fetcher.py

from __future__ import annotations

from typing import Any, Dict, Optional

import aiohttp

from ..core.interfaces import ResourceFetcher


class DummyFetcher(ResourceFetcher):
    async def fetch_json(
        self,
        url: str,
        *,
        method: str = "GET",
        params: Optional[Dict] = None,
        payload: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        return {"url": url, "method": method, "params": params, "payload": payload}

    async def fetch_bytes(self, url: str, *, method: str = "GET") -> bytes:
        return f"dummy:{method}:{url}".encode("utf-8")


class HTTPFetcher(ResourceFetcher):
    """Reusable aiohttp-based fetcher."""

    def __init__(self, *, timeout: Optional[int] = None, session: Optional[aiohttp.ClientSession] = None, default_headers: Optional[Dict[str, str]] = None):
        self._timeout = timeout or 30
        self._external_session = session
        self._session: Optional[aiohttp.ClientSession] = session
        self._default_headers = dict(default_headers or {})

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
            if self._default_headers:
                self._session.headers.update(self._default_headers)
        elif self._default_headers:
            self._session.headers.update({k: v for k, v in self._default_headers.items() if k not in self._session.headers})
        return self._session

    async def fetch_json(
        self,
        url: str,
        *,
        method: str = "GET",
        params: Optional[Dict] = None,
        payload: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        session = await self._get_session()
        async with session.request(method, url, params=params, json=payload) as resp:
            resp.raise_for_status()
            try:
                return await resp.json()
            except Exception:
                text = await resp.text()
                return {"status": resp.status, "text": text}

    async def fetch_bytes(self, url: str, *, method: str = "GET") -> bytes:
        session = await self._get_session()
        async with session.request(method, url) as resp:
            resp.raise_for_status()
            return await resp.read()

    async def close(self) -> None:
        if self._session and self._session is not self._external_session and not self._session.closed:
            await self._session.close()
        self._session = self._external_session

    async def __aenter__(self) -> "HTTPFetcher":
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

