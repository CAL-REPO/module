# -*- coding: utf-8 -*-
# structured_io/core/__init__.py
"""structured_io.core
====================

Core interfaces and policy classes for structured I/O operations.
"""

from .interface import BaseParser, BaseDumper, Parser, Dumper
from .policy import (
    SourcePathPolicy,
    BaseParserPolicy,
    BaseDumperPolicy,
)

__all__ = [
    # Interfaces (Base prefix is primary)
    "BaseParser",
    "BaseDumper",
    # Policies
    "SourcePathPolicy",
    "BaseParserPolicy",
    "BaseDumperPolicy",
]

