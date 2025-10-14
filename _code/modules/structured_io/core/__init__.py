"""
structured_io.core
------------------
Core interfaces and base classes for structured I/O operations.
"""
from .base_dumper import *
from .base_parser import *
from .base_policy import *

__all__ = [
    "BaseDumper",
    "BaseParser",
    "BasePolicy",
]
