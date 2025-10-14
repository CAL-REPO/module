# -*- coding: utf-8 -*-
"""
Text preprocessing utilities (phrase map, chunking).
"""

from __future__ import annotations

from typing import List, Tuple

from modules.data_utils import ListOps, StringOps

from ..core.policy import ZhChunkPolicy


class TextPreprocessor:
    """Apply phrase mappings and optional clause chunking."""

    def __init__(self, policy: ZhChunkPolicy):
        self.policy = policy

    def prepare(self, text: str) -> List[str]:
        transformed = self._apply_phrase_map(text)
        return self._chunk(transformed)

    def _apply_phrase_map(self, text: str) -> str:
        tuples: List[Tuple[str, str]] = []
        for pair in self.policy.phrase_map:
            try:
                src, dst = pair[0], pair[1]
            except (IndexError, TypeError):
                continue
            tuples.append((str(src), str(dst)))

        for src, dst in ListOps.dedupe_keep_order(tuples):
            if src:
                text = text.replace(src, dst)
        return text

    def _chunk(self, text: str) -> List[str]:
        if self.policy.mode != "clause":
            return [text]
        if len(text) < self.policy.min_len:
            return [text]
        if not StringOps.mostly_zh(text):
            return [text]

        chunks = StringOps.chunk_clauses(text, max_len=self.policy.max_len)
        return chunks or [text]
