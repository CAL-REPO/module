# -*- coding: utf-8 -*-
"""
structured_data.mixin.io.connection
-----------------------------------
Connection management mixin for SQLite database operations.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from ...core import DBPolicy, BaseOperationsMixin


class ConnectionMixin(BaseOperationsMixin):
    """Connection management mixin for SQLite databases.
    
    Provides methods to open, close, and manage SQLite database connections
    with policy-driven configuration (WAL, foreign keys, timeout, etc.).
    
    Attributes:
        path: Path to the SQLite database file.
        policy: DBPolicy instance controlling connection behavior.
        _con: Internal SQLite connection object (None when closed).
    """
    
    def __init__(self, path: Path | str, policy: Optional[DBPolicy] = None):
        """Initialize connection mixin with path and policy.
        
        Args:
            path: Path to the SQLite database file.
            policy: DBPolicy instance. If None, uses default DBPolicy().
        """
        super().__init__(policy or DBPolicy())
        self.path = Path(path)
        self._con: Optional[sqlite3.Connection] = None
    
    def open(self) -> ConnectionMixin:
        """Open SQLite database connection with policy-driven configuration.
        
        Returns:
            Self for method chaining.
        
        Raises:
            RuntimeError: If connection already open (when strict_mode=True).
        """
        if self._con and self.policy.strict_mode:
            raise RuntimeError("Database connection already open")
        
        if self.policy.auto_validate:
            self.validate()
        
        # Open connection with timeout from policy
        self._con = sqlite3.connect(
            str(self.path),
            timeout=self.policy.connection_timeout
        )
        
        # Apply policy-driven SQLite pragmas
        if self.policy.enable_wal:
            self._con.execute("PRAGMA journal_mode=WAL")
        if self.policy.foreign_keys:
            self._con.execute("PRAGMA foreign_keys=ON")
        
        return self
    
    def close(self) -> None:
        """Close database connection and commit if auto_commit enabled."""
        if self._con:
            if self.policy.auto_commit:
                self._con.commit()
            self._con.close()
            self._con = None
    
    def __enter__(self) -> ConnectionMixin:
        """Context manager entry."""
        return self.open()
    
    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.close()
    
    @property
    def con(self) -> sqlite3.Connection:
        """Get current connection or raise error if not open.
        
        Returns:
            Active SQLite connection.
        
        Raises:
            RuntimeError: If connection is None and strict_mode=True.
        """
        if not self._con:
            if self.policy.strict_mode:
                raise RuntimeError("Database not open - call open() or use context manager")
            # Auto-open if strict_mode is False
            return self.open()._con
        return self._con
