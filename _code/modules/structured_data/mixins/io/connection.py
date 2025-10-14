"""Connection management mixin for various resources.

This mixin provides lifecycle management (open/close) for any resource
that requires connection management: databases, network sockets, file handles, etc.
"""

import sqlite3
from pathlib import Path
from typing import Optional, TYPE_CHECKING, Any

from ...core import BaseOperationsMixin, BaseOperationsPolicy

if TYPE_CHECKING:
    from modules.fso_utils.core.policy import FSOOpsPolicy, ExistencePolicy
    from modules.fso_utils.core.ops import FSOOps


class ConnectionMixin(BaseOperationsMixin):
    """Mixin for managing resource connections.
    
    Provides a standard interface for opening, closing, and managing
    connections to various resources. Can be used with databases, APIs,
    file systems, or any other resource requiring connection management.
    
    Attributes:
        path: Path to the resource (for file-based resources).
        _con: The active connection object, or ``None`` if not connected.
    
    Example:
        >>> class MyDB(ConnectionMixin):
        ...     def open(self):
        ...         self._con = some_db_library.connect(self.path)
        ...         return self
        ...
        >>> with MyDB("db.sqlite") as db:
        ...     # Use db
        ...     pass
    """
    
    def _default_policy(self) -> BaseOperationsPolicy:
        """Return default policy."""
        return BaseOperationsPolicy()
    
    def __init__(self, path: Path | str | None = None, policy=None):
        """Initialize the connection mixin.
        
        Args:
            path: Optional path to the resource.
            policy: Optional policy controlling behavior.
        """
        super().__init__(policy)
        self.path = Path(path) if path else None
        self._con: Optional[Any] = None
    
    def open(self) -> "ConnectionMixin":
        """Open the resource connection.
        
        Subclasses should override this to implement resource-specific
        connection logic.
        
        Returns:
            Self for method chaining.
        
        Raises:
            RuntimeError: If already connected.
            NotImplementedError: If not overridden by subclass.
        """
        if self._con is not None:
            raise RuntimeError("Connection already open")
        raise NotImplementedError("Subclass must implement open()")
    
    def close(self) -> None:
        """Close the resource connection.
        
        Subclasses can override this to add resource-specific cleanup.
        The default implementation sets ``_con`` to ``None``.
        """
        if self._con is not None:
            # Default: just clear the connection
            # Subclasses should add proper cleanup
            self._con = None
    
    def __enter__(self) -> "ConnectionMixin":
        """Context manager entry: open the connection.
        
        Returns:
            Self for use in ``with`` statements.
        """
        return self.open()
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit: close the connection.
        
        Args:
            exc_type: Exception type, if an exception occurred.
            exc_val: Exception value, if an exception occurred.
            exc_tb: Exception traceback, if an exception occurred.
        """
        self.close()
    
    @property
    def con(self) -> Any:
        """Get the active connection.
        
        Returns:
            The active connection object.
        
        Raises:
            RuntimeError: If not connected and policy requires it.
        """
        if self._con is None:
            if hasattr(self.policy, 'strict_mode') and self.policy.strict_mode:
                raise RuntimeError(
                    "Resource not connected. Call open() first or use "
                    "as context manager."
                )
        return self._con


class SQLiteConnectionMixin(ConnectionMixin):
    """SQLite-specific connection mixin.
    
    Extends :class:`ConnectionMixin` with SQLite-specific functionality
    such as file creation, WAL mode, and foreign keys.
    """
    
    def open(self) -> "SQLiteConnectionMixin":
        """Open SQLite database connection.
        
        Creates the database file if it doesn't exist (when policy allows),
        then establishes a connection and applies configuration.
        
        Returns:
            Self for method chaining.
        """
        if self._con is not None:
            raise RuntimeError("Database connection already open")
        
        # Ensure database file exists
        policy = self.policy
        if hasattr(policy, 'create_if_missing') and policy.create_if_missing:
            # Lazy import to avoid circular dependency
            from modules.fso_utils.core.policy import FSOOpsPolicy, ExistencePolicy
            from modules.fso_utils.core.ops import FSOOps
            
            ops = FSOOps(
                self.path,
                policy=FSOOpsPolicy(
                    as_type="file",
                    exist=ExistencePolicy(
                        must_exist=False,
                        create_if_missing=True,
                        overwrite=False
                    )
                )
            )
            db_path = ops.path
        else:
            db_path = self.path
        
        # Open connection
        timeout = getattr(policy, 'connection_timeout', 5)
        self._con = sqlite3.connect(str(db_path), timeout=timeout)
        
        # Apply policy-based configuration
        if hasattr(policy, 'enable_wal') and policy.enable_wal:
            self._con.execute("PRAGMA journal_mode=WAL")
        if hasattr(policy, 'foreign_keys') and policy.foreign_keys:
            self._con.execute("PRAGMA foreign_keys=ON")
        
        return self
    
    def close(self) -> None:
        """Close SQLite connection with commit if needed."""
        if self._con is not None:
            policy = self.policy
            if hasattr(policy, 'auto_commit') and policy.auto_commit:
                self._con.commit()
            self._con.close()
            self._con = None
