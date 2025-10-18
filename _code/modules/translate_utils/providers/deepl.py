"""DeepL provider adapter.

Wraps the `deepl.Translator` into the Provider interface used by the
translation pipeline.
"""

from __future__ import annotations

import os
from typing import List, Optional

from ..providers.base import Provider

try:  # optional import to keep import-time safe when running tests
    import deepl  # type: ignore
except Exception:  # pragma: no cover
    deepl = None  # type: ignore


class DeepLProvider(Provider):
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        api_key = api_key or os.environ.get("DEEPL_API_KEY") or os.environ.get("DEEP_L_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPL_API_KEY not set for DeepL provider")
        if deepl is None:
            raise ImportError("deepl package not installed")
        
        # DeepL SDK v1.23.0+: deepl.DeepLClient (not Translator), no timeout param
        # Timeout is managed via deepl.http_client.min_connection_timeout (global)
        if timeout != 30:  # Only set if non-default
            try:
                deepl.http_client.min_connection_timeout = timeout
            except AttributeError:
                pass  # Older SDK versions may not have this
        
        # Try DeepLClient (v1.18+) first, fallback to Translator (older versions)
        if hasattr(deepl, 'DeepLClient'):
            self._client = deepl.DeepLClient(api_key)
        else:
            # Old SDK (< v1.18) - deepl.Translator with timeout param
            self._client = deepl.Translator(api_key, timeout=timeout)  # type: ignore

    def translate_text(
        self,
        texts: List[str],
        *,
        target_lang: str,
        source_lang: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[str]:
        # deepl.DeepLClient/Translator.translate_text supports list input and returns
        # a list-like response where each element has `.text` attribute
        if source_lang is None or (isinstance(source_lang, str) and source_lang.upper() == "AUTO"):
            src = None
        else:
            src = source_lang
        
        # Build kwargs (type: ignore for DeepL SDK external types)
        kwargs = dict(target_lang=target_lang, source_lang=src)
        
        # Pass model_type if supported by installed deepl package (some versions accept it)
        if model_type:
            try:
                resp = self._client.translate_text(texts, model_type=model_type, **kwargs)  # type: ignore
            except TypeError:
                # Older deepl SDKs may not accept model_type param; fall back
                resp = self._client.translate_text(texts, **kwargs)  # type: ignore
        else:
            resp = self._client.translate_text(texts, **kwargs)  # type: ignore
        
        # resp may be a list-like or single TextResult; each item has `.text` attribute
        out: List[str] = []
        # Handle both single TextResult and list of TextResult
        if hasattr(resp, '__iter__') and not isinstance(resp, str):
            for item in resp:  # type: ignore
                text = getattr(item, "text", item)
                out.append(str(text))
        else:
            # Single result
            text = getattr(resp, "text", resp)  # type: ignore
            out.append(str(text))
        
        return out

    def close(self) -> None:
        # deepl.Translator does not require explicit close, but keep API
        return None
