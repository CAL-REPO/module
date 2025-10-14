

# -*- coding: utf-8 -*-
"""
structured_data.composite.dataframe
-----------------------------------
Composite class for DataFrame operations using role-based mixins (clean, normalize, filter, update, from dict).
"""

from typing import Optional, Dict, Set
from dataclasses import dataclass, field

from structured_data.core import BaseOperationsPolicy
from structured_data.mixin.transform import CleanMixin, NormalizeMixin, FilterMixin, UpdateMixin
from structured_data.mixin.create import FromDictMixin

@dataclass
class DFPolicy(BaseOperationsPolicy):
	"""Policy for DataFrame operations."""
	allow_empty: bool = False
	normalize_columns: bool = True
	drop_empty_rows: bool = True
	drop_empty_cols: bool = True
	warn_on_duplicate_cols: bool = True
	default_aliases: Dict[str, Set[str]] = field(default_factory=dict)


class DataFrameComposite(
	CleanMixin,
	NormalizeMixin,
	FilterMixin,
	UpdateMixin,
	FromDictMixin
):
	"""High-level composite for DataFrame operations using role-based mixins.
	Combines multiple transform and create mixins to provide a unified
	interface for DataFrame manipulation:
	- CleanMixin: Data cleaning (drop empty, remove nulls)
	- NormalizeMixin: Column/value normalization
	- FilterMixin: Row filtering
	- UpdateMixin: Value updates
	- FromDictMixin: Create DataFrame from dict
	"""
	pass
