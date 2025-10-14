"""Schema management mixin for structured data.

Provides schema creation and validation for databases, JSON schemas,
or any other structured data format.
"""

import sqlite3
from typing import Optional

from ...core import BaseOperationsMixin, BaseOperationsPolicy


class SchemaMixin(BaseOperationsMixin):
    """Mixin for managing data schemas.
    
    Provides methods for setting and enforcing schemas across different
    data structures. Can be used with databases, JSON, XML, or any format
    requiring schema validation.
    
    Attributes:
        _schema: The schema definition (DDL string, JSON schema, etc.).
    """
    
    def _default_policy(self) -> BaseOperationsPolicy:
        """Return default policy."""
        return BaseOperationsPolicy()
    
    def __init__(self, policy=None):
        """Initialize the schema mixin.
        
        Args:
            policy: Optional policy controlling schema behavior.
        """
        super().__init__(policy)
        self._schema: Optional[str] = None
    
    def set_schema(self, schema: str) -> "SchemaMixin":
        """Set the schema definition.
        
        Args:
            schema: Schema definition (format depends on use case).
        
        Returns:
            Self for method chaining.
        """
        self._schema = schema
        return self
    
    def ensure_schema(self, resource, name: str) -> None:
        """Ensure the schema exists, creating it if necessary.
        
        Subclasses should override this to implement format-specific
        schema enforcement.
        
        Args:
            resource: The resource to apply schema to (connection, file, etc.).
            name: Name of the schema/table/collection.
        
        Raises:
            NotImplementedError: If not overridden by subclass.
        """
        raise NotImplementedError("Subclass must implement ensure_schema()")


class SQLiteSchemaMixin(SchemaMixin):
    """SQLite-specific schema mixin.
    
    Extends :class:`SchemaMixin` with SQLite DDL execution.
    """
    
    def ensure_schema(self, con: sqlite3.Connection, table_name: str) -> None:
        """Ensure SQLite table exists.
        
        If a DDL statement has been set via :meth:`set_schema`, it will be
        executed. Otherwise, a default key-value schema is created if
        policy allows.
        
        Args:
            con: The SQLite connection.
            table_name: Name of the table to create.
        """
        if self._schema:
            con.execute(self._schema)
        elif hasattr(self.policy, 'enforce_schema') and self.policy.enforce_schema:
            # Default KV schema
            con.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
        
        con.commit()
