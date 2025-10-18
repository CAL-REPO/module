# -*- coding: utf-8 -*-
"""
Translation pipeline orchestration.
"""

from __future__ import annotations

from typing import Any, List, Optional, Dict
from time import sleep

from logs_utils import LogManager

from ..providers.base import Provider
from ..core.policy import TranslatePolicy
from ..core.interfaces import CacheInterface, WriterInterface
from .preprocessor import TextPreprocessor
from .source_loader import SourcePayload


class TranslationPipeline:
    """Coordinate source loading, preprocessing, provider calls and persistence."""

    def __init__(
        self,
        *,
        policy: TranslatePolicy,
        provider: Provider,
        preprocessor: TextPreprocessor,
        cache: Optional[CacheInterface],
        writer: Optional[WriterInterface],
        log = None,
    ):
        self.policy = policy
        self.provider = provider
        self.preprocessor = preprocessor
        self.cache = cache if cache and cache.enabled else None
        self.writer = writer if writer and writer.enabled else None
        self.log = log or LogManager().logger

    def run(self, payload: SourcePayload) -> List[str]:
        """Execute translation with batch optimization and segment-level caching.
        
        배치 번역 최적화:
        1. 모든 텍스트의 세그먼트를 수집하면서 캐시 확인
        2. 캐시 미스된 세그먼트만 모아서 한 번에 번역 (bulk translation)
        3. 번역 결과를 캐시에 저장하고 원래 위치에 재배치
        
        효과:
        - API 호출 횟수 최소화: N개 세그먼트 → 1번 호출 (캐시 미스만)
        - 세그먼트 단위 캐싱 유지: 재사용률 극대화
        """
        texts = payload.texts
        if not texts:
            return []

        target_lang = self.policy.provider.target_lang
        source_lang = self.policy.provider.source_lang
        model_type = self.policy.provider.model_type

        try:
            # ================================================================
            # Phase 1: 세그먼트 수집 + 캐시 확인
            # ================================================================
            # 각 텍스트의 세그먼트 구조 저장 (복원용)
            text_segments_map: List[List[str]] = []
            
            # 캐시 미스 세그먼트 수집 (중복 제거)
            uncached_segments: List[str] = []
            seen_segments: set = set()
            
            for src in texts:
                segments = self.preprocessor.prepare(src)
                text_segments_map.append(segments)
                
                for segment in segments:
                    # 캐시 확인
                    if segment not in seen_segments:
                        cached = self.cache.get(segment, target_lang, model_type) if self.cache else None
                        if cached is None:
                            uncached_segments.append(segment)
                        seen_segments.add(segment)
            
            # ================================================================
            # Phase 2: 캐시 미스 세그먼트 bulk 번역
            # ================================================================
            translation_cache: Dict[str, str] = {}
            
            if uncached_segments:
                self.log.info(f"[Pipeline] Translating {len(uncached_segments)} uncached segments (bulk)")
                
                # Bulk translation with retry
                attempts = 2
                last_exc: Optional[Exception] = None
                translations: Optional[List[str]] = None
                
                for attempt in range(attempts):
                    try:
                        translations = self.provider.translate_text(
                            uncached_segments,
                            target_lang=target_lang,
                            source_lang=None if (source_lang or "").upper() == "AUTO" else source_lang,
                            model_type=model_type,
                        )
                        break
                    except Exception as exc:
                        last_exc = exc
                        self.log.warning(f"[Pipeline] Translation attempt {attempt + 1} failed: {exc}")
                        sleep(0.5 * (attempt + 1))
                
                if translations is None and last_exc is not None:
                    raise last_exc
                
                # 번역 결과를 translation_cache에 저장
                if translations:
                    for segment, translated in zip(uncached_segments, translations):
                        translation_cache[segment] = translated
                        
                        # DB 캐시에 저장
                        if self.cache:
                            self.cache.put(segment, translated, target_lang, model_type)
            
            # ================================================================
            # Phase 3: 결과 재구성 (원래 텍스트 순서대로)
            # ================================================================
            results: List[str] = []
            
            for segments in text_segments_map:
                translated_segments: List[str] = []
                
                for segment in segments:
                    # 캐시 또는 translation_cache에서 가져오기
                    if segment in translation_cache:
                        translated = translation_cache[segment]
                    else:
                        # 캐시에서 다시 읽기 (이미 캐시된 경우)
                        translated = self.cache.get(segment, target_lang, model_type) if self.cache else segment
                    
                    translated_segments.append(translated or segment)
                
                # 세그먼트 결합 (preprocessor가 구두점 포함하므로 단순 결합)
                results.append("".join(translated_segments))

            if self.writer:
                path = self.writer.write(texts, results)
                if path:
                    self.log.info(f"[translate] saved JSON: {path}")

            return results
        finally:
            if self.cache:
                self.cache.close()
