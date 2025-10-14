"""Data creation mixins for various sources.

Provides methods to create structured data from different sources
(dicts, KV stores, files, etc.).
"""

from .from_dict import FromDictMixin

__all__ = [
    "FromDictMixin",
]
