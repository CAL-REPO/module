"""I/O operation mixins.

Provides mixins for resource connection, schema management, and caching
that can be used across different data structures (databases, APIs, files, etc.).
"""

from .connection import ConnectionMixin, SQLiteConnectionMixin
from .schema import SchemaMixin, SQLiteSchemaMixin
from .cache import CacheMixin, SQLiteCacheMixin

__all__ = [
    # Generic mixins
    "ConnectionMixin",
    "SchemaMixin",
    "CacheMixin",
    
    # SQLite-specific mixins
    "SQLiteConnectionMixin",
    "SQLiteSchemaMixin",
    "SQLiteCacheMixin",
]
