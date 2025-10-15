
# -*- coding: utf-8 -*-
"""
structured_data.composite.database
----------------------------------
Composite classes for database operations in structured data (SQLite key-value store).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..core import DBPolicy
from ..mixin.io.connection import ConnectionMixin
from ..mixin.io.schema import SchemaMixin
from ..mixin.ops.kv_ops import KVOperationsMixin
from ..mixin.ops.key_gen import KeyGenerationMixin


class SQLiteKVStore(
    ConnectionMixin,
    SchemaMixin,
    KVOperationsMixin,
    KeyGenerationMixin
):
    """SQLite-based Key-Value store composed from role-based mixins.
    
    This composite class combines:
    - ConnectionMixin: SQLite connection management (open, close, context manager)
    - SchemaMixin: Table creation and DDL management
    - KVOperationsMixin: Basic KV operations (get, put, delete, exists)
    - KeyGenerationMixin: SHA256 key hashing for composite keys
    
    Attributes:
        path: Path to the SQLite database file.
        table: Table name for KV storage.
        policy: DBPolicy instance controlling behavior.
    
    Example:
        ```python
        from structured_data import SQLiteKVStore, DBPolicy
        
        policy = DBPolicy(auto_commit=True, enable_wal=True)
        
        with SQLiteKVStore("cache.db", table="translations", policy=policy) as store:
            store.put("key1", "value1")
            value = store.get("key1")
            
            # Use key generation for composite keys
            key = store.make_key("user", "123", "en")
            store.put(key, "cached_value")
        ```
    """
    
    def __init__(
        self,
        path: Path | str,
        *,
        table: str = "cache",
        ddl: Optional[str] = None,
        policy: Optional[DBPolicy] = None
    ):
        """Initialize SQLite KV store with path, table, and policy.
        
        Args:
            path: Path to the SQLite database file.
            table: Table name for KV storage. Defaults to "cache".
            ddl: Optional custom DDL for table creation. If None, uses default KV schema.
            policy: DBPolicy instance. If None, uses default DBPolicy().
        """
        # Initialize all mixins with policy
        ConnectionMixin.__init__(self, path, policy or DBPolicy())
        SchemaMixin.__init__(self, policy or DBPolicy())
        KVOperationsMixin.__init__(self, policy or DBPolicy())
        KeyGenerationMixin.__init__(self, policy or DBPolicy())
        
        self.table = table
        
        if ddl:
            self.set_ddl(ddl)
    
    def open(self) -> SQLiteKVStore:
        """Open database connection and ensure table exists.
        
        Returns:
            Self for method chaining.
        """
        ConnectionMixin.open(self)
        self.ensure_table(self.con, self.table)
        return self
    
    # Convenience methods that automatically pass `con` and `table`
    
    def get(self, key: str) -> Optional[str]:
        """Get value for key.
        
        Args:
            key: Key to retrieve.
        
        Returns:
            Value for key, or None if key doesn't exist.
        """
        return KVOperationsMixin.get(self, self.con, self.table, key)
    
    def put(self, key: str, value: str) -> None:
        """Put key-value pair.
        
        Args:
            key: Key to store.
            value: Value to store.
        """
        KVOperationsMixin.put(self, self.con, self.table, key, value)
    
    def delete(self, key: str) -> None:
        """Delete key.
        
        Args:
            key: Key to delete.
        """
        KVOperationsMixin.delete(self, self.con, self.table, key)
    
    def exists(self, key: str) -> bool:
        """Check if key exists.
        
        Args:
            key: Key to check.
        
        Returns:
            True if key exists, False otherwise.
        """
        return KVOperationsMixin.exists(self, self.con, self.table, key)

