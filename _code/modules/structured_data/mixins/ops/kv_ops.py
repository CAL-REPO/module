"""Key-value operations mixin for various storage backends.

Provides CRUD operations that work with databases, caches, dicts, etc.
"""

import sqlite3
from typing import Optional, Any

from ...core import BaseOperationsMixin, BaseOperationsPolicy


class KVOperationsMixin(BaseOperationsMixin):
    """Mixin for key-value operations across storage backends.
    
    Provides get, put, delete, and exists operations that can be
    adapted to different storage backends (SQLite, Redis, dict, file, etc.).
    """
    
    def _default_policy(self) -> BaseOperationsPolicy:
        """Return default policy."""
        return BaseOperationsPolicy()
    
    def get(self, resource: Any, location: str, key: str) -> Optional[str]:
        """Retrieve a value by key.
        
        Subclasses should override to implement backend-specific logic.
        
        Args:
            resource: The storage resource (connection, dict, etc.).
            location: Location identifier (table, file path, etc.).
            key: The key to look up.
        
        Returns:
            The value, or ``None`` if not found.
        
        Raises:
            NotImplementedError: If not overridden by subclass.
        """
        raise NotImplementedError("Subclass must implement get()")
    
    def put(self, resource: Any, location: str, key: str, value: str) -> None:
        """Store or update a key-value pair.
        
        Subclasses should override to implement backend-specific logic.
        
        Args:
            resource: The storage resource.
            location: Location identifier.
            key: The key to store.
            value: The value to associate with the key.
        
        Raises:
            NotImplementedError: If not overridden by subclass.
        """
        raise NotImplementedError("Subclass must implement put()")
    
    def delete(self, resource: Any, location: str, key: str) -> None:
        """Delete a key-value pair.
        
        Subclasses should override to implement backend-specific logic.
        
        Args:
            resource: The storage resource.
            location: Location identifier.
            key: The key to delete.
        
        Raises:
            NotImplementedError: If not overridden by subclass.
        """
        raise NotImplementedError("Subclass must implement delete()")
    
    def exists(self, resource: Any, location: str, key: str) -> bool:
        """Check if a key exists.
        
        Subclasses should override to implement backend-specific logic.
        
        Args:
            resource: The storage resource.
            location: Location identifier.
            key: The key to check.
        
        Returns:
            ``True`` if the key exists, ``False`` otherwise.
        
        Raises:
            NotImplementedError: If not overridden by subclass.
        """
        raise NotImplementedError("Subclass must implement exists()")


class SQLiteKVOperationsMixin(KVOperationsMixin):
    """SQLite-specific key-value operations mixin."""
    
    def get(self, con: sqlite3.Connection, table: str, key: str) -> Optional[str]:
        """Retrieve value from SQLite table."""
        cur = con.execute(
            f"SELECT value FROM {table} WHERE key=?",
            (key,)
        )
        row = cur.fetchone()
        return row[0] if row else None
    
    def put(self, con: sqlite3.Connection, table: str, key: str, value: str) -> None:
        """Store value in SQLite table."""
        con.execute(
            f"INSERT OR REPLACE INTO {table}(key, value) VALUES(?,?)",
            (key, value)
        )
        policy = self.policy
        if hasattr(policy, 'auto_commit') and policy.auto_commit:
            con.commit()
    
    def delete(self, con: sqlite3.Connection, table: str, key: str) -> None:
        """Delete from SQLite table."""
        con.execute(
            f"DELETE FROM {table} WHERE key=?",
            (key,)
        )
        policy = self.policy
        if hasattr(policy, 'auto_commit') and policy.auto_commit:
            con.commit()
    
    def exists(self, con: sqlite3.Connection, table: str, key: str) -> bool:
        """Check if key exists in SQLite table."""
        cur = con.execute(
            f"SELECT 1 FROM {table} WHERE key=? LIMIT 1",
            (key,)
        )
        return cur.fetchone() is not None
