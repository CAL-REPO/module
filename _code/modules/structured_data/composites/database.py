"""Database composite classes using role-based mixins.

Combines I/O, ops, and other mixins to create database operations.
"""

from pathlib import Path
from typing import Optional

from ..core import BaseOperationsPolicy
from ..mixins.io import SQLiteConnectionMixin, SQLiteSchemaMixin, SQLiteCacheMixin
from ..mixins.ops import SQLiteKVOperationsMixin, KeyGenerationMixin


# Define DBPolicy here to replace the old db/base.py
from dataclasses import dataclass

@dataclass
class DBPolicy(BaseOperationsPolicy):
    """Policy for database operations."""
    table_name: str = "cache"
    auto_commit: bool = True
    create_if_missing: bool = True
    enforce_schema: bool = True
    connection_timeout: int = 5
    enable_wal: bool = True
    foreign_keys: bool = True


class SQLiteKVStore(
    SQLiteConnectionMixin,
    SQLiteSchemaMixin,
    SQLiteKVOperationsMixin,
    KeyGenerationMixin
):
    """SQLite-based key-value store using role-based mixin composition.
    
    Combines multiple mixins to provide a full-featured KV store:
    - SQLiteConnectionMixin: Connection management
    - SQLiteSchemaMixin: Schema management
    - SQLiteKVOperationsMixin: CRUD operations
    - KeyGenerationMixin: Cache key generation
    
    Example:
        >>> store = SQLiteKVStore("cache.db")
        >>> with store:
        ...     store.put("key1", "value1")
        ...     value = store.get("key1")
    """

    def __init__(
        self,
        path: Path | str,
        *,
        table: str = "cache",
        ddl: Optional[str] = None,
        policy: Optional[DBPolicy] = None
    ):
        """Initialize the key-value store.
        
        Args:
            path: Path to the SQLite database file.
            table: Name of the table to use. Defaults to ``"cache"``.
            ddl: Optional custom DDL statement for schema creation.
            policy: Optional database policy.
        """
        # Initialize all mixins
        super().__init__(path, policy or DBPolicy())
        self.table = table
        
        # Set up schema
        if ddl:
            self.set_schema(ddl)
        else:
            # Default key-value schema
            self.set_schema(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
    
    def open(self) -> "SQLiteKVStore":
        """Open database and ensure schema."""
        super().open()  # SQLiteConnectionMixin.open()
        self.ensure_schema(self.con, self.table)  # SQLiteSchemaMixin.ensure_schema()
        return self
    
    # Convenience methods that wrap mixin methods
    
    def get(self, key: str) -> Optional[str]:
        """Retrieve a value by key."""
        return super().get(self.con, self.table, key)
    
    def put(self, key: str, value: str) -> None:
        """Store or update a key-value pair."""
        return super().put(self.con, self.table, key, value)
    
    def delete(self, key: str) -> None:
        """Delete a key-value pair."""
        return super().delete(self.con, self.table, key)
    
    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return super().exists(self.con, self.table, key)


class TranslationCache(
    SQLiteConnectionMixin,
    SQLiteSchemaMixin,
    SQLiteCacheMixin,  # ← Added for put_cached/get_cached
    KeyGenerationMixin
):
    """Specialized cache for translation results.
    
    Uses a custom schema optimized for storing translation pairs with
    metadata (source text, target text, language, model).
    
    Combines:
    - SQLiteConnectionMixin: Connection management
    - SQLiteSchemaMixin: Schema management
    - SQLiteCacheMixin: Multi-field caching (put_cached/get_cached)
    - KeyGenerationMixin: Cache key generation
    
    Example:
        >>> cache = TranslationCache("translations.db")
        >>> with cache:
        ...     cache.put_translation(
        ...         src="Hello",
        ...         tgt="Bonjour",
        ...         target_lang="fr",
        ...         model="gpt-4"
        ...     )
        ...     result = cache.get_translation("Hello", "fr", "gpt-4")
    """
    
    def __init__(self, path: Path | str, policy: Optional[DBPolicy] = None):
        """Initialize the translation cache.
        
        Args:
            path: Path to the SQLite database file.
            policy: Optional database policy.
        """
        # Initialize connection mixin
        SQLiteConnectionMixin.__init__(self, path, policy or DBPolicy())
        
        # Set table name
        self.table = "cache"
        
        # Custom DDL for translation cache
        ddl = """
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            src TEXT NOT NULL,
            tgt TEXT NOT NULL,
            target_lang TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        # Set schema and ensure table exists
        self.set_schema(ddl)
        with self as conn:
            self.ensure_schema(conn.con, self.table)
    
    def get_translation(
        self,
        src: str,
        target_lang: str,
        model: str
    ) -> Optional[str]:
        """Retrieve a cached translation.
        
        Args:
            src: The source text that was translated.
            target_lang: The target language code.
            model: The model used for translation.
        
        Returns:
            The translated text, or ``None`` if not cached.
        """
        key = self.make_key(src, target_lang, model)
        result = self.get_cached(self.con, self.table, key, ["tgt"])
        return result["tgt"] if result else None
    
    def put_translation(
        self,
        src: str,
        tgt: str,
        target_lang: str,
        model: str
    ) -> None:
        """Store a translation in the cache.
        
        Args:
            src: The source text.
            tgt: The translated text.
            target_lang: The target language code.
            model: The model used for translation.
        """
        key = self.make_key(src, target_lang, model)
        self.put_cached(self.con, self.table, key, {
            "src": src,
            "tgt": tgt,
            "target_lang": target_lang,
            "model": model
        })
