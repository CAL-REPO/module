"""Base classes and policies for structured data operations.

This module provides the common foundation for all structured data
operations (DataFrame, Database, etc.) through shared policy and mixin
base classes.
"""

from .policy import BaseOperationsPolicy, OperationsPolicy
from .mixin import BaseOperationsMixin

__all__ = [
    "BaseOperationsPolicy",
    "OperationsPolicy",
    "BaseOperationsMixin",
]
