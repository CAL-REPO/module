"""Caching mixin for multi-field data storage.

Provides caching operations that work with various storage backends
(databases, files, memory, etc.).
"""

import sqlite3
from typing import Optional, Dict, Any

from ...core import BaseOperationsMixin, BaseOperationsPolicy


class CacheMixin(BaseOperationsMixin):
    """Mixin for multi-field cache operations.
    
    Provides methods for caching data with multiple fields, suitable for
    translation caches, session storage, or any multi-value caching scenario.
    Can be adapted to different storage backends.
    """
    
    def _default_policy(self) -> BaseOperationsPolicy:
        """Return default policy."""
        return BaseOperationsPolicy()
    
    def get_cached(
        self,
        resource: Any,
        location: str,
        key: str,
        fields: list[str]
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a cached record with multiple fields.
        
        Subclasses should override this to implement backend-specific logic.
        
        Args:
            resource: The storage resource (connection, file handle, etc.).
            location: Location identifier (table, file path, etc.).
            key: The cache key to look up.
            fields: List of field names to retrieve.
        
        Returns:
            A dictionary mapping field names to values, or ``None`` if
            the key is not found.
        
        Raises:
            NotImplementedError: If not overridden by subclass.
        """
        raise NotImplementedError("Subclass must implement get_cached()")
    
    def put_cached(
        self,
        resource: Any,
        location: str,
        key: str,
        data: Dict[str, Any]
    ) -> None:
        """Store a cached record with multiple fields.
        
        Subclasses should override this to implement backend-specific logic.
        
        Args:
            resource: The storage resource.
            location: Location identifier.
            key: The cache key to store under.
            data: Dictionary of field names to values.
        
        Raises:
            NotImplementedError: If not overridden by subclass.
        """
        raise NotImplementedError("Subclass must implement put_cached()")


class SQLiteCacheMixin(CacheMixin):
    """SQLite-specific cache mixin.
    
    Extends :class:`CacheMixin` with SQLite-specific operations.
    """
    
    def get_cached(
        self,
        con: sqlite3.Connection,
        table: str,
        key: str,
        fields: list[str]
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a cached record from SQLite.
        
        Args:
            con: The SQLite connection.
            table: Name of the table to query.
            key: The cache key to look up.
            fields: List of field names to retrieve.
        
        Returns:
            A dictionary mapping field names to values, or ``None`` if not found.
        """
        fields_str = ", ".join(fields)
        cur = con.execute(
            f"SELECT {fields_str} FROM {table} WHERE key=?",
            (key,)
        )
        row = cur.fetchone()
        if row:
            return dict(zip(fields, row))
        return None
    
    def put_cached(
        self,
        con: sqlite3.Connection,
        table: str,
        key: str,
        data: Dict[str, Any]
    ) -> None:
        """Store a cached record in SQLite.
        
        Args:
            con: The SQLite connection.
            table: Name of the table to update.
            key: The cache key to store under.
            data: Dictionary of field names to values.
        """
        fields = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        
        con.execute(
            f"INSERT OR REPLACE INTO {table}(key, {fields}) VALUES(?, {placeholders})",
            (key, *data.values())
        )
        
        policy = self.policy
        if hasattr(policy, 'auto_commit') and policy.auto_commit:
            con.commit()
