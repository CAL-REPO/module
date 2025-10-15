# -*- coding: utf-8 -*-
"""
structured_data.composite.dataframe_ops
---------------------------------------
Composite class combining all DataFrame mixins for a unified interface.
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from ..composite.dataframe import DFPolicy
from ..mixin.transform.clean import CleanMixin
from ..mixin.transform.filter import FilterMixin
from ..mixin.transform.normalize import NormalizeMixin
from ..mixin.transform.update import UpdateMixin
from ..mixin.create.from_dict import FromDictMixin


class DataFrameOps(
    CleanMixin,
    FilterMixin,
    NormalizeMixin,
    UpdateMixin,
    FromDictMixin
):
    """Unified DataFrame operations composite combining all transform/create mixins.
    
    This class provides a fluent interface for DataFrame manipulation
    by combining multiple role-based mixins:
    
    - CleanMixin: drop_empty, drop_duplicates, strip_strings
    - FilterMixin: filter by query or callable
    - NormalizeMixin: normalize column names, apply transformations
    - UpdateMixin: update cells and values
    - FromDictMixin: create DataFrame from dictionaries
    
    Attributes:
        df: The working DataFrame (if initialized with one).
        policy: DFPolicy instance controlling behavior.
    
    Example:
        ```python
        from structured_data import DataFrameOps, DFPolicy
        import pandas as pd
        
        policy = DFPolicy(drop_empty_rows=True, normalize_columns=True)
        ops = DataFrameOps(policy=policy)
        
        # Create from dict
        df = ops.from_dict_records([
            {'Name': 'Alice', 'Age': 30},
            {'Name': 'Bob', 'Age': 25}
        ])
        
        # Chain operations
        df = ops.normalize(df)  # Normalize column names
        df = ops.clean(df)  # Clean data
        df = ops.filter(df, "Age > 25")  # Filter rows
        ```
    """
    
    def __init__(
        self,
        df: Optional[pd.DataFrame] = None,
        *,
        policy: Optional[DFPolicy] = None
    ):
        """Initialize DataFrameOps with optional DataFrame and policy.
        
        Args:
            df: Optional DataFrame to work with.
            policy: DFPolicy instance. If None, uses default DFPolicy().
        """
        # Initialize all mixins with policy
        policy = policy or DFPolicy()
        
        CleanMixin.__init__(self, policy)
        FilterMixin.__init__(self, policy)
        NormalizeMixin.__init__(self, policy)
        UpdateMixin.__init__(self, policy)
        FromDictMixin.__init__(self, policy)
        
        self.df = df
    
    def pipe(self, df: pd.DataFrame) -> DataFramePipeline:
        """Start a fluent pipeline with the given DataFrame.
        
        Args:
            df: DataFrame to process.
        
        Returns:
            DataFramePipeline instance for method chaining.
        
        Example:
            ```python
            result = ops.pipe(df) \\
                .clean() \\
                .normalize() \\
                .filter("age > 30") \\
                .get()
            ```
        """
        return DataFramePipeline(df, self)


class DataFramePipeline:
    """Fluent pipeline for chaining DataFrame operations.
    
    This class enables method chaining for cleaner syntax.
    """
    
    def __init__(self, df: pd.DataFrame, ops: DataFrameOps):
        """Initialize pipeline with DataFrame and operations instance.
        
        Args:
            df: DataFrame to process.
            ops: DataFrameOps instance providing methods.
        """
        self._df = df
        self._ops = ops
    
    def clean(self) -> DataFramePipeline:
        """Apply cleaning operations."""
        self._df = self._ops.clean(self._df)
        return self
    
    def normalize(self, **kwargs) -> DataFramePipeline:
        """Apply normalization operations."""
        self._df = self._ops.normalize(self._df, **kwargs)
        return self
    
    def filter(self, condition, **kwargs) -> DataFramePipeline:
        """Apply filtering operations."""
        self._df = self._ops.filter(self._df, condition, **kwargs)
        return self
    
    def update(self, **kwargs) -> DataFramePipeline:
        """Apply update operations."""
        self._df = self._ops.update(self._df, **kwargs)
        return self
    
    def get(self) -> pd.DataFrame:
        """Get the final DataFrame result."""
        return self._df
