"""
structured_data.mixin
======================
Top-level exports for role-based mixins (io, transform, create, ops).

This module re-exports the specific mixin classes so consumers can import
them from ``structured_data.mixin`` (keeps a stable API during refactors).
"""
from .io import SchemaMixin, ConnectionMixin, CacheMixin
from .transform import CleanMixin, NormalizeMixin, FilterMixin, UpdateMixin
from .create import FromDictMixin
from .ops import KVOperationsMixin, KeyGenerationMixin

__all__ = [
    "SchemaMixin",
    "ConnectionMixin",
    "CacheMixin",
    "CleanMixin",
    "NormalizeMixin",
    "FilterMixin",
    "UpdateMixin",
    "FromDictMixin",
    "KVOperationsMixin",
    "KeyGenerationMixin",
]
