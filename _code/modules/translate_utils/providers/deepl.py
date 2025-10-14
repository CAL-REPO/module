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
        self._client = deepl.Translator(api_key, timeout=timeout)

    def translate_text(
        self,
        texts: List[str],
        *,
        target_lang: str,
        source_lang: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[str]:
        # deepl.Translator.translate_text supports list input and returns a list-like
        # response where each element has `.text` attribute; normalize to List[str]
        if source_lang is None or (isinstance(source_lang, str) and source_lang.upper() == "AUTO"):
            src = None
        else:
            src = source_lang
        # Pass model_type if supported by installed deepl package (some versions accept it)
        kwargs = dict(target_lang=target_lang, source_lang=src)
        if model_type:
            try:
                resp = self._client.translate_text(texts, model_type=model_type, **kwargs)
            except TypeError:
                # Older deepl SDKs may not accept model_type param; fall back
                resp = self._client.translate_text(texts, **kwargs)
        else:
            resp = self._client.translate_text(texts, **kwargs)
        # resp may be a list-like; each item may be object with `.text` or str
        out: List[str] = []
        for item in resp:
            text = getattr(item, "text", item)
            out.append(text)
        return out

    def close(self) -> None:
        # deepl.Translator does not require explicit close, but keep API
        return None
