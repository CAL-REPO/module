# -*- coding: utf-8 -*-
"""
translater/provider/deepl.py — DeepL client wrapper (object + policy aware)
----------------------------------------------------------------------------

Encapsulates the official `deepl` SDK usage behind a small object interface,
so call sites stay clean. API key is resolved from arguments or environment.
"""

from __future__ import annotations

import os
from typing import Iterable, List

try:
    import deepl  # type: ignore
except Exception:  # pragma: no cover
    deepl = None  # type: ignore


class DeepLClient:
    def __init__(self, *, api_key: str | None = None, timeout: int = 30, model_type: str = "prefer_quality_optimized"):
        self.api_key = api_key or os.environ.get("DEEPL_API_KEY") or os.environ.get("DEEP_L_API_KEY")
        self.timeout = timeout
        self.model_type = model_type
        if deepl is None:
            raise ImportError("deepl package not installed. Please `pip install deepl`.")
        if not self.api_key:
            raise RuntimeError("DEEPL_API_KEY not set")
        self._client = deepl.Translator(self.api_key, timeout=self.timeout)

    def translate(self, texts: Iterable[str], *, target_lang: str, source_lang: str | None = None) -> List[str]:
        items = list(texts)
        if not items:
            return []
        res = self._client.translate_text(
            items,
            target_lang=target_lang,
            source_lang=None if (source_lang or "").upper() == "AUTO" else source_lang,
        )
        if isinstance(res, list):
            return [r.text for r in res]
        return [res.text]
