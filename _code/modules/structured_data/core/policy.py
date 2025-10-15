"""Common policy base classes for structured data operations.

This module defines the base policy protocol and dataclass that all
specific policies (DFPolicy, DBPolicy, etc.) should inherit from.
"""

from typing import Protocol
from dataclasses import dataclass


class OperationsPolicy(Protocol):
    """Protocol that all operation policies must follow.
    
    This defines the minimal interface for any policy object used
    by structured data operations.
    """
    verbose: bool
    strict_mode: bool
    auto_validate: bool


@dataclass
class BaseOperationsPolicy:
    """Base policy class for all structured data operations.
    
    Provides common configuration options shared across different
    operation types (DataFrame, Database, etc.).
    
    Attributes:
        verbose: If ``True``, operations will log detailed information
            about their execution. Defaults to ``False``.
        strict_mode: If ``True``, operations will raise errors on
            validation failures. If ``False``, warnings may be issued
            instead. Defaults to ``True``.
        auto_validate: If ``True``, operations will automatically
            validate their inputs and state. Defaults to ``True``.
    """
    verbose: bool = False
    strict_mode: bool = True
    auto_validate: bool = True


@dataclass
class DBPolicy(BaseOperationsPolicy):
    """Policy class for database operations (SQLite).
    
    Extends BaseOperationsPolicy with database-specific configuration
    options for connection management, transactions, and optimization.
    
    Attributes:
        table_name: Default table name for operations. Defaults to ``"cache"``.
        auto_commit: If ``True``, automatically commit after each write
            operation. If ``False``, manual commit is required. Defaults to ``True``.
        create_if_missing: If ``True``, create database and table if they
            don't exist. Defaults to ``True``.
        enforce_schema: If ``True``, validate DDL schema on table creation.
            Defaults to ``True``.
        connection_timeout: Connection timeout in seconds. Defaults to ``5``.
        enable_wal: If ``True``, enable Write-Ahead Logging for better
            concurrency. Defaults to ``True``.
        foreign_keys: If ``True``, enable foreign key constraints.
            Defaults to ``True``.
    """
    table_name: str = "cache"
    auto_commit: bool = True
    create_if_missing: bool = True
    enforce_schema: bool = True
    connection_timeout: int = 5
    enable_wal: bool = True
    foreign_keys: bool = True
