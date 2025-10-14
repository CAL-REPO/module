"""Mock translation provider for testing.

Simple deterministic transformations so pipeline tests don't need network.
"""

from __future__ import annotations

from typing import List, Optional

from ..providers.base import Provider


class MockProvider(Provider):
    def __init__(self, prefix: str = "[tr]"):
        self.prefix = prefix

    def translate_text(
        self,
        texts: List[str],
        *,
        target_lang: str,
        source_lang: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[str]:
        # model_type is accepted for API compatibility; mock ignores it
        return [f"{self.prefix}:{target_lang}:{t}" for t in texts]

    def close(self) -> None:
        return None
