# -*- coding: utf-8 -*-
# structured_io/core/__init__.py
"""structured_io.core
====================

Core interfaces and policy classes for structured I/O operations.
"""

from .interface import BaseParser, BaseDumper
from .policy import (
    BaseParserPolicy,
    BaseDumperPolicy,
)

__all__ = [
    # Interfaces
    "BaseParser",
    "BaseDumper",
    # Policies
    "BaseParserPolicy",
    "BaseDumperPolicy",
]

