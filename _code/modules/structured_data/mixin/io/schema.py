# -*- coding: utf-8 -*-
"""
structured_data.mixin.io.schema
-------------------------------
Schema management mixin for SQLite database operations.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from ...core import DBPolicy, BaseOperationsMixin


class SchemaMixin(BaseOperationsMixin):
    """Schema management mixin for SQLite databases.
    
    Provides methods to create tables with DDL and ensure table existence
    before operations.
    
    Attributes:
        policy: DBPolicy instance controlling schema behavior.
        _ddl: Custom DDL string for table creation (optional).
    """
    
    def __init__(self, policy: Optional[DBPolicy] = None):
        """Initialize schema mixin with policy.
        
        Args:
            policy: DBPolicy instance. If None, uses default DBPolicy().
        """
        super().__init__(policy or DBPolicy())
        self._ddl: Optional[str] = None
    
    def set_ddl(self, ddl: str) -> SchemaMixin:
        """Set custom DDL for table creation.
        
        Args:
            ddl: SQL CREATE TABLE statement.
        
        Returns:
            Self for method chaining.
        """
        self._ddl = ddl
        return self
    
    def ensure_table(
        self, 
        con: sqlite3.Connection, 
        table_name: str,
        ddl: Optional[str] = None
    ) -> None:
        """Ensure table exists, creating it if necessary.
        
        Args:
            con: Active SQLite connection.
            table_name: Name of the table to create/check.
            ddl: Optional DDL override. If None, uses self._ddl or default schema.
        
        Raises:
            ValueError: If enforce_schema=True and DDL validation fails.
        """
        if not self.policy.create_if_missing:
            return
        
        # Use provided DDL > instance DDL > default KV schema
        schema = ddl or self._ddl or self._default_kv_schema(table_name)
        
        if self.policy.enforce_schema and self.policy.auto_validate:
            self._validate_ddl(schema, table_name)
        
        con.execute(schema)
        
        if self.policy.auto_commit:
            con.commit()
    
    def _default_kv_schema(self, table_name: str) -> str:
        """Generate default key-value table schema.
        
        Args:
            table_name: Name of the table.
        
        Returns:
            SQL CREATE TABLE statement for basic KV store.
        """
        return f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
    
    def _validate_ddl(self, ddl: str, table_name: str) -> None:
        """Validate DDL string (basic checks).
        
        Args:
            ddl: SQL DDL statement to validate.
            table_name: Expected table name in DDL.
        
        Raises:
            ValueError: If DDL is invalid or doesn't contain table_name.
        """
        if not ddl or not isinstance(ddl, str):
            raise ValueError(f"DDL must be non-empty string, got: {type(ddl)}")
        
        ddl_upper = ddl.upper()
        if "CREATE TABLE" not in ddl_upper:
            raise ValueError(f"DDL must contain 'CREATE TABLE', got: {ddl[:50]}...")
        
        if table_name.upper() not in ddl_upper:
            raise ValueError(f"DDL must reference table '{table_name}'")
