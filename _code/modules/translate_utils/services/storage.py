# -*- coding: utf-8 -*-
"""
Caching and persistence helpers for translation outputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

# Import structured_data composites lazily to avoid heavy import-time side effects
SQLiteKVStore = None
StructuredTranslationCache = None
from modules.fso_utils import ExistencePolicy, FSOOps, FSOOpsPolicy
from modules.structured_io import json_fileio

from ..core.policy import StorePolicy


class TranslationCache:
    """SQLite-backed translation cache."""

    def __init__(self, policy: StorePolicy, *, default_dir: Path):
        self.policy = policy
        self._store: Optional[SQLiteKVStore] = None
        self.path: Optional[Path] = None

        if policy.save_db:
            # Lazy import to avoid pulling heavy deps during module import
            from modules.structured_data.composites import TranslationCache as StructuredTranslationCache

            base_dir = Path(policy.db_dir).expanduser() if policy.db_dir else default_dir
            self.path = base_dir / policy.db_name
            # Use the structured_data composite TranslationCache which provides
            # get_translation/put_translation helpers for the schema used by the
            # translation pipeline.
            self._store = StructuredTranslationCache(self.path).open()
        else:
            # Use an in-memory dict based cache for testing or when DB disabled
            class _InMemory:
                def __init__(self):
                    self._d = {}

                def get(self, key):
                    return self._d.get(key)

                def put(self, key, value):
                    self._d[key] = value

                def close(self):
                    self._d.clear()

            self._inmem = _InMemory()

    @property
    def enabled(self) -> bool:
        return self._store is not None

    def get(self, src: str, target_lang: str, model: str) -> Optional[str]:
        if not self._store:
            # in-memory cache
            if hasattr(self, "_inmem"):
                key = f"{src}\x1f{target_lang}\x1f{model}"
                return self._inmem.get(key)
            return None
        return self._store.get_translation(src, target_lang, model)

    def put(self, src: str, tgt: str, target_lang: str, model: str) -> None:
        if not self._store:
            if hasattr(self, "_inmem"):
                key = f"{src}\x1f{target_lang}\x1f{model}"
                self._inmem.put(key, tgt)
            return
        self._store.put_translation(src, tgt, target_lang, model)

    def close(self) -> None:
        if getattr(self, "_store", None):
            self._store.close()
            self._store = None
        if hasattr(self, "_inmem"):
            self._inmem.close()
            delattr(self, "_inmem")


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
