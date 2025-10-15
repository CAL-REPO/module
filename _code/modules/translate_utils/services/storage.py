# -*- coding: utf-8 -*-
"""
Caching and persistence helpers for translation outputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fso_utils import ExistencePolicy, FSOOps, FSOOpsPolicy
from structured_io import json_fileio

from ..core.policy import StorePolicy
from .cache import TranslationCache


class TranslationStorage:
    """Translation storage managing both database cache and JSON file output.
    
    This class now uses the refactored TranslationCache (which wraps SQLiteKVStore)
    instead of the old stub from structured_data.composite.database.
    """

    def __init__(self, policy: StorePolicy, *, default_dir: Path):
        self.policy = policy
        self._cache: Optional[TranslationCache] = None
        self.db_path: Optional[Path] = None

        if policy.save_db:
            # Use the new TranslationCache from translate_utils.services.cache
            base_dir = Path(policy.db_dir).expanduser() if policy.db_dir else default_dir
            self.db_path = base_dir / policy.db_name
            self._cache = TranslationCache(self.db_path)
            # Open cache connection
            self._cache.open()

    @property
    def enabled(self) -> bool:
        """Check if database cache is enabled."""
        return self._cache is not None

    def get(self, src: str, target_lang: str, model: str) -> Optional[str]:
        """Get cached translation.
        
        Args:
            src: Source text.
            target_lang: Target language code.
            model: Translation model name.
        
        Returns:
            Cached translation if found, None otherwise.
        """
        if not self._cache:
            return None
        return self._cache.get_translation(src, target_lang, model)

    def put(self, src: str, tgt: str, target_lang: str, model: str) -> None:
        """Store translation in cache.
        
        Args:
            src: Source text.
            tgt: Translated text.
            target_lang: Target language code.
            model: Translation model name.
        """
        if not self._cache:
            return
        self._cache.put_translation(src, tgt, target_lang, model)

    def close(self) -> None:
        """Close database cache connection."""
        if self._cache:
            self._cache.close()
            self._cache = None


class TranslationResultWriter:
    """Persist translated results to JSON."""

    def __init__(self, policy: StorePolicy, *, default_dir: Path):
        self.policy = policy
        self.path: Optional[Path] = None
        self._dir_path: Optional[Path] = None

        if policy.save_tr:
            base_dir = Path(policy.tr_dir).expanduser() if policy.tr_dir else default_dir
            dir_ops = FSOOps(
                base_dir,
                policy=FSOOpsPolicy(as_type="dir", exist=ExistencePolicy(create_if_missing=True)),
            )
            self._dir_path = dir_ops.path
            self.path = self._dir_path / policy.tr_name

    @property
    def enabled(self) -> bool:
        return self.path is not None

    def write(self, texts: List[str], translations: List[str]) -> Optional[Path]:
        if not self.path:
            return None

        payload = {src: tgt for src, tgt in zip(texts, translations)}
        json_fileio(str(self.path)).write(payload)
        return self.path
