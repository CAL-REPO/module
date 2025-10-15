
# -*- coding: utf-8 -*-
"""
structured_data.mixin.ops.kv_ops
--------------------------------
Role-based mixin for key-value operations in structured data.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from ...core import DBPolicy, BaseOperationsMixin


class KVOperationsMixin(BaseOperationsMixin):
    """Key-Value operations mixin for SQLite databases.
    
    Provides get, put, delete, exists methods for basic KV operations
    on SQLite tables with policy-driven auto-commit behavior.
    
    Attributes:
        policy: DBPolicy instance controlling commit behavior.
    """
    
    def __init__(self, policy: Optional[DBPolicy] = None):
        """Initialize KV operations mixin with policy.
        
        Args:
            policy: DBPolicy instance. If None, uses default DBPolicy().
        """
        super().__init__(policy or DBPolicy())
    
    def get(self, con: sqlite3.Connection, table: str, key: str) -> Optional[str]:
        """Get value for key from table.
        
        Args:
            con: Active SQLite connection.
            table: Table name.
            key: Key to retrieve.
        
        Returns:
            Value for key, or None if key doesn't exist.
        """
        cur = con.execute(f"SELECT value FROM {table} WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else None
    
    def put(self, con: sqlite3.Connection, table: str, key: str, value: str) -> None:
        """Put key-value pair into table (INSERT OR REPLACE).
        
        Args:
            con: Active SQLite connection.
            table: Table name.
            key: Key to store.
            value: Value to store.
        """
        con.execute(
            f"INSERT OR REPLACE INTO {table}(key, value) VALUES(?, ?)",
            (key, value)
        )
        if self.policy.auto_commit:
            con.commit()
    
    def delete(self, con: sqlite3.Connection, table: str, key: str) -> None:
        """Delete key from table.
        
        Args:
            con: Active SQLite connection.
            table: Table name.
            key: Key to delete.
        """
        con.execute(f"DELETE FROM {table} WHERE key=?", (key,))
        if self.policy.auto_commit:
            con.commit()
    
    def exists(self, con: sqlite3.Connection, table: str, key: str) -> bool:
        """Check if key exists in table.
        
        Args:
            con: Active SQLite connection.
            table: Table name.
            key: Key to check.
        
        Returns:
            True if key exists, False otherwise.
        """
        cur = con.execute(f"SELECT 1 FROM {table} WHERE key=? LIMIT 1", (key,))
        return cur.fetchone() is not None
