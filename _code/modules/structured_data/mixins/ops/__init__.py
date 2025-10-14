"""Operation mixins for structured data.

Provides CRUD operations, key generation, and other data operations
that work across different storage backends.
"""

from .kv_ops import KVOperationsMixin, SQLiteKVOperationsMixin
from .key_gen import KeyGenerationMixin

__all__ = [
    # Generic mixins
    "KVOperationsMixin",
    "KeyGenerationMixin",
    
    # SQLite-specific mixins
    "SQLiteKVOperationsMixin",
]
