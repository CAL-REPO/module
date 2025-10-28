# -*- coding: utf-8 -*-
# crawl_utils/services/fetcher.py
# Fetcher: HTTP 리소스 가져오기 (Async + Sync 통합)

from __future__ import annotations

from typing import Any, Dict, Optional

import aiohttp
import requests

from ..core.interfaces import ResourceFetcher


# ============================================================================
# Sync Fetcher: requests 기반 동기 버전
# ============================================================================
class SyncHTTPFetcher:
    """Synchronous HTTP fetcher using requests library."""

    def __init__(
        self,
        *,
        timeout: Optional[int] = None,
        session: Optional[requests.Session] = None,
        default_headers: Optional[Dict[str, str]] = None,
        timeout_connect: Optional[float] = None,
        timeout_read: Optional[float] = None,
        allow_redirects: bool = True,
        stream_download: bool = False,
        reuse_session: bool = True,
    ):
        self._timeout = float(timeout or 30)
        self._timeout_connect = timeout_connect
        self._timeout_read = timeout_read
        self._allow_redirects = allow_redirects
        self._stream_download = stream_download
        self._reuse_session = reuse_session
        self._external_session = session
        self._session: Optional[requests.Session] = session
        self._default_headers = dict(default_headers or {})

    def _get_session(self) -> requests.Session:
        """Get or create requests Session."""
        if not self._reuse_session and self._external_session is None:
            session = requests.Session()
            if self._default_headers:
                session.headers.update(self._default_headers)
            return session
        
        if self._session is None:
            self._session = requests.Session()
            if self._default_headers:
                self._session.headers.update(self._default_headers)
        elif self._default_headers:
            # Update headers if not already set
            self._session.headers.update(
                {k: v for k, v in self._default_headers.items() if k not in self._session.headers}
            )
        return self._session

    def _build_timeout(self) -> float | tuple[float, float]:
        if self._timeout_connect is not None or self._timeout_read is not None:
            connect = self._timeout_connect if self._timeout_connect is not None else self._timeout
            read = self._timeout_read if self._timeout_read is not None else self._timeout
            return (connect, read)
        return self._timeout

    def fetch_json(
        self,
        url: str,
        *,
        method: str = "GET",
        params: Optional[Dict] = None,
        payload: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Fetch JSON synchronously."""
        session = self._get_session()
        close_after = not self._reuse_session and self._external_session is None
        resp = session.request(
            method,
            url,
            params=params,
            json=payload,
            timeout=self._build_timeout(),
            allow_redirects=self._allow_redirects,
        )
        resp.raise_for_status()
        try:
            result = resp.json()
        except Exception:
            result = {"status": resp.status_code, "text": resp.text}
        finally:
            if close_after:
                session.close()
        return result

    def fetch_bytes(self, url: str, *, method: str = "GET") -> bytes:
        """Fetch bytes synchronously."""
        session = self._get_session()
        close_after = not self._reuse_session and self._external_session is None
        resp = session.request(
            method,
            url,
            timeout=self._build_timeout(),
            allow_redirects=self._allow_redirects,
            stream=self._stream_download,
        )
        resp.raise_for_status()
        try:
            if self._stream_download:
                chunks = [chunk for chunk in resp.iter_content(chunk_size=8192) if chunk]
                data = b"".join(chunks)
            else:
                data = resp.content
        finally:
            if close_after:
                session.close()
        return data

    def close(self) -> None:
        """Close session."""
        if self._session and self._session is not self._external_session:
            self._session.close()
        self._session = self._external_session

    def __enter__(self) -> "SyncHTTPFetcher":
        """Context manager support."""
        self._get_session()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """Context manager cleanup."""
        self.close()

class AsyncDummyFetcher(ResourceFetcher):
    """Async dummy fetcher for testing."""
    
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


class AsyncHTTPFetcher(ResourceFetcher):
    """Asynchronous aiohttp-based HTTP fetcher."""

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

    async def __aenter__(self) -> "AsyncHTTPFetcher":
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()