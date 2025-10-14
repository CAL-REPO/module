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
