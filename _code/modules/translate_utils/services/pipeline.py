# -*- coding: utf-8 -*-
"""
Translation pipeline orchestration.
"""

from __future__ import annotations

from typing import Any, List, Optional
from time import sleep

from ..providers.base import Provider

# Simple dummy logger for when no logger is provided
class DummyLogger:
    """No-op logger for pipeline when logger is not provided."""
    def debug(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def success(self, *args, **kwargs): pass

from ..core.policy import TranslatePolicy
from .preprocessor import TextPreprocessor
from .source_loader import SourcePayload
from .storage import TranslationCache, TranslationResultWriter


class TranslationPipeline:
    """Coordinate source loading, preprocessing, provider calls and persistence."""

    def __init__(
        self,
        *,
        policy: TranslatePolicy,
        provider: Provider,
        preprocessor: TextPreprocessor,
        cache: Optional[TranslationCache],
        writer: Optional[TranslationResultWriter],
        logger=None,
    ):
        self.policy = policy
        self.provider = provider
        self.preprocessor = preprocessor
        self.cache = cache if cache and cache.enabled else None
        self.writer = writer if writer and writer.enabled else None
        self.logger = logger or DummyLogger()

    def run(self, payload: SourcePayload) -> List[str]:
        texts = payload.texts
        if not texts:
            return []

        results: List[str] = []
        target_lang = self.policy.provider.target_lang
        source_lang = self.policy.provider.source_lang
        model_type = self.policy.provider.model_type

        try:
            for src in texts:
                segments = self.preprocessor.prepare(src)
                translated_segments: List[str] = []

                for segment in segments:
                    cached = self.cache.get(segment, target_lang, model_type) if self.cache else None
                    if cached is not None:
                        translated_segments.append(cached)
                        continue
                    # Call provider with a tiny retry loop (on cache miss)
                    attempts = 2
                    last_exc: Optional[Exception] = None
                    translated: Optional[str] = None
                    for attempt in range(attempts):
                        try:
                            resp = self.provider.translate_text(
                                [segment],
                                target_lang=target_lang,
                                source_lang=None if (source_lang or "").upper() == "AUTO" else source_lang,
                                model_type=model_type,
                            )
                            # Provider interface returns List[str]
                            if isinstance(resp, list) and resp:
                                translated = resp[0]
                            else:
                                translated = None
                            break
                        except Exception as exc:  # pragma: no cover - provider dependent
                            last_exc = exc
                            # small backoff
                            sleep(0.5 * (attempt + 1))
                    if translated is None and last_exc is not None:
                        raise last_exc

                    if self.cache:
                        # cache expects src/tgt/model tuple semantics
                        self.cache.put(segment, translated or "", target_lang, model_type)
                    translated_segments.append(translated or "")

                results.append("".join(translated_segments))

            if self.writer:
                path = self.writer.write(texts, results)
                if path:
                    self.logger.info("[translate] saved JSON: {}", path)

            return results
        finally:
            if self.cache:
                self.cache.close()
