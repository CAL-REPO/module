# -*- coding: utf-8 -*-
"""
translate_utils.services.cache
------------------------------
Translation-specific cache implementation using structured_data.SQLiteKVStore.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from structured_data import SQLiteKVStore, DBPolicy


class TranslationCache:
    """Translation cache wrapping SQLiteKVStore with translation-specific schema.
    
    This is a business-logic adapter that uses the generic SQLiteKVStore
    from structured_data and provides translation-specific methods.
    
    The cache stores translations with composite keys generated from:
    (source_text, target_lang, model_name)
    
    Attributes:
        store: Underlying SQLiteKVStore instance.
    
    Example:
        ```python
        cache = TranslationCache(Path("translations.db"))
        
        with cache:
            # Store translation
            cache.put_translation(
                src="Hello",
                tgt="你好",
                target_lang="zh-CN",
                model="deepl"
            )
            
            # Retrieve translation
            result = cache.get_translation("Hello", "zh-CN", "deepl")
        ```
    """
    
    # DDL for translation cache table with explicit schema
    TRANSLATION_SCHEMA = """
        CREATE TABLE IF NOT EXISTS translations (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    
    def __init__(
        self,
        path: Path | str,
        *,
        policy: Optional[DBPolicy] = None
    ):
        """Initialize translation cache.
        
        Args:
            path: Path to the SQLite database file.
            policy: DBPolicy instance. If None, uses default with WAL enabled.
        """
        # Use default policy optimized for caching
        if policy is None:
            policy = DBPolicy(
                auto_commit=True,
                enable_wal=True,
                create_if_missing=True,
                enforce_schema=True
            )
        
        # Create SQLiteKVStore with translation-specific table
        self.store = SQLiteKVStore(
            path,
            table="translations",
            ddl=self.TRANSLATION_SCHEMA,
            policy=policy
        )
    
    def open(self) -> TranslationCache:
        """Open database connection."""
        self.store.open()
        return self
    
    def close(self) -> None:
        """Close database connection."""
        self.store.close()
    
    def __enter__(self) -> TranslationCache:
        """Context manager entry."""
        return self.open()
    
    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.close()
    
    def get_translation(
        self,
        src: str,
        target_lang: str,
        model: str
    ) -> Optional[str]:
        """Get cached translation for source text.
        
        Args:
            src: Source text.
            target_lang: Target language code (e.g., "zh-CN", "ko").
            model: Translation model/provider name (e.g., "deepl", "google").
        
        Returns:
            Cached translation if found, None otherwise.
        """
        key = self._make_translation_key(src, target_lang, model)
        return self.store.get(key)
    
    def put_translation(
        self,
        src: str,
        tgt: str,
        target_lang: str,
        model: str
    ) -> None:
        """Store translation in cache.
        
        Args:
            src: Source text.
            tgt: Translated text.
            target_lang: Target language code.
            model: Translation model/provider name.
        """
        key = self._make_translation_key(src, target_lang, model)
        self.store.put(key, tgt)
    
    def exists(
        self,
        src: str,
        target_lang: str,
        model: str
    ) -> bool:
        """Check if translation exists in cache.
        
        Args:
            src: Source text.
            target_lang: Target language code.
            model: Translation model/provider name.
        
        Returns:
            True if translation is cached, False otherwise.
        """
        key = self._make_translation_key(src, target_lang, model)
        return self.store.exists(key)
    
    def _make_translation_key(
        self,
        src: str,
        target_lang: str,
        model: str
    ) -> str:
        """Generate cache key from source, language, and model.
        
        Uses SQLiteKVStore.make_key for SHA256 hashing.
        
        Args:
            src: Source text.
            target_lang: Target language code.
            model: Translation model/provider name.
        
        Returns:
            64-character SHA256 hash key.
        """
        return self.store.make_key(src, target_lang, model)
