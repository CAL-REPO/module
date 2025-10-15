# -*- coding: utf-8 -*-
"""
structured_data.composite
-------------------------
Composite classes for structured data operations, including DataFrame, Database, and related policies.
Exports only intended API for use in higher-level modules.
"""

from .dataframe import DataFrameComposite, DFPolicy  # Ensure this matches the correct module
from .database import SQLiteKVStore
from .dataframe_ops import DataFrameOps  # Ensure this matches the correct module

__all__ = [
    "DataFrameComposite",
    "SQLiteKVStore",
    "DataFrameOps",
    "DFPolicy",
]
