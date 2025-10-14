"""Provider abstraction for translation backends.

Defines a small, testable interface that concrete providers (DeepL,
Google, mocks) implement. The interface always returns a list of
translated strings for the provided input texts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class Provider(ABC):
    """Abstract translation provider interface."""

    @abstractmethod
    def translate_text(
        self,
        texts: List[str],
        *,
        target_lang: str,
        source_lang: Optional[str] = None,
        model_type: Optional[str] = None, # latency_optimized | quality_optimized | prefer_quality_optimized
    ) -> List[str]:
        """Translate a list of texts and return the list of translated strings.

        Implementations must return the translations in the same order as
        the input list.
        """

    def close(self) -> None:  # pragma: no cover - optional cleanup
        """Optional cleanup for providers holding resources (connections).
        """
        return None
