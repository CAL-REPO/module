"""Structured data operations using role-based composable mixins.

This module provides policy-driven operations for structured data types
using a unified mixin-based architecture organized by role/responsibility.

Organization:
    base/        - Common base classes and policies
    mixin/       - Role-based mixins (io, transform, create, ops)
    composite/   - Pre-composed classes for common use cases

Architecture:
    Each mixin is focused on a specific role (I/O, transformation, etc.)
    and can work with multiple data types (DataFrame, dict, list, database).
    Composite classes combine multiple mixins for common use cases.
"""

# Base classes
from .core import (
    BaseOperationsPolicy,
    OperationsPolicy,
    BaseOperationsMixin,
    DBPolicy,
)

# Role-based mixins (NEW - organized by function)
from .mixin import (
    # I/O mixins
    ConnectionMixin,
    SchemaMixin,
    CacheMixin,
    
    # Transform mixins
    CleanMixin,
    NormalizeMixin,
    FilterMixin,
    UpdateMixin,
    
    # Create mixins
    FromDictMixin,
    
    # Ops mixins
    KVOperationsMixin,
    KeyGenerationMixin,
)

# Composite classes (Ready-to-use combinations)
from .composite import (
    SQLiteKVStore,
    DataFrameOps,
)

# Policies (moved from db/base.py and df/base.py)
from .composite.dataframe import DFPolicy

# Backward compatibility aliases
DataFrameOpsCompat = DataFrameOps  # For old code using "DataFrameOpsCompat"
SQLiteKVStoreCompat = SQLiteKVStore  # For old code using "SQLiteKVStoreCompat"

__all__ = [
    # Base
    "BaseOperationsPolicy",
    "OperationsPolicy",
    "BaseOperationsMixin",
    
    # Policies
    "DBPolicy",
    "DFPolicy",
    
    # Role-based mixins
    "ConnectionMixin",
    "SchemaMixin",
    "CacheMixin",
    "CleanMixin",
    "NormalizeMixin",
    "FilterMixin",
    "UpdateMixin",
    "FromDictMixin",
    "KVOperationsMixin",
    "KeyGenerationMixin",
    
    # Composites
    "SQLiteKVStore",
    "DataFrameOps",
    
    # Backward compatibility
    "DataFrameOpsCompat",
    "SQLiteKVStoreCompat",
]

