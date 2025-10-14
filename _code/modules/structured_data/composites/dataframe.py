"""DataFrame composite class using role-based mixins.

Combines transform, create, and other mixins for DataFrame operations.
"""

from typing import Optional
from dataclasses import dataclass, field
from typing import Dict, Set

from ..core import BaseOperationsPolicy
from ..mixins.transform import CleanMixin, NormalizeMixin, FilterMixin, UpdateMixin
from ..mixins.create import FromDictMixin


# Define DFPolicy here to replace the old df/base.py
@dataclass
class DFPolicy(BaseOperationsPolicy):
    """Policy for DataFrame operations."""
    allow_empty: bool = False
    normalize_columns: bool = True
    drop_empty_rows: bool = True
    drop_empty_cols: bool = True
    warn_on_duplicate_cols: bool = True
    default_aliases: Dict[str, Set[str]] = field(default_factory=dict)


class DataFrameOps(
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
    - FromDictMixin: DataFrame creation from dicts
    
    Example:
        >>> ops = DataFrameOps()
        >>> df = ops.dict_to_df({'A': [1, 2, None], 'B': [4, 5, 6]})
        >>> df = ops.drop_empty_df(df)
        >>> df = ops.normalize_df_columns(df, {'A': 'col_a'})
    """

    def __init__(self, policy: Optional[DFPolicy] = None) -> None:
        """Initialize the DataFrame operations composite.
        
        Args:
            policy: Optional DataFrame policy. If not provided, a default
                policy will be created.
        """
        super().__init__(policy or DFPolicy())
