"""Role-based mixins for structured data operations.

This package organizes mixins by their role/responsibility rather than
by data type, enabling free composition across different data structures.

Organization:
    io/         - I/O operations (connection, schema, caching)
    transform/  - Data transformation (clean, normalize, filter)
    create/     - Data creation (from_dict, from_kv, etc.)
    ops/        - Data operations (CRUD, key generation, etc.)
"""

# Import all mixins for convenient access
from .io import ConnectionMixin, SchemaMixin, CacheMixin
from .transform import CleanMixin, NormalizeMixin, FilterMixin, UpdateMixin
from .create import FromDictMixin
from .ops import KVOperationsMixin, KeyGenerationMixin

__all__ = [
    # I/O mixins
    "ConnectionMixin",
    "SchemaMixin",
    "CacheMixin",
    
    # Transform mixins
    "CleanMixin",
    "NormalizeMixin",
    "FilterMixin",
    "UpdateMixin",
    
    # Create mixins
    "FromDictMixin",
    
    # Ops mixins
    "KVOperationsMixin",
    "KeyGenerationMixin",
]
