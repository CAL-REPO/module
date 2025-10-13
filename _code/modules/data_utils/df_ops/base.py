from typing import Optional, Dict, Set
from dataclasses import dataclass, field
import pandas as pd

@dataclass
class DataFramePolicy:
    """Unified policy controlling DataFrame behaviors.

    This dataclass aggregates all configuration options used by the DataFrame
    mixins and the high‑level :class:`DataFrameOps` interface.

    Attributes:
        allow_empty: If ``False``, attempts to create an empty DataFrame will
            raise a :class:`ValueError`. Defaults to ``False``.
        normalize_columns: Whether column names should be normalized using
            alias mappings. Defaults to ``True``.
        drop_empty_rows: Whether to drop rows consisting entirely of missing
            values when cleaning a DataFrame. Defaults to ``True``.
        drop_empty_cols: Whether to drop columns consisting entirely of
            missing values when cleaning a DataFrame. Defaults to ``True``.
        warn_on_duplicate_cols: Whether to print a warning when duplicate
            columns are detected after normalization. Defaults to ``True``.
        default_aliases: A mapping of canonical column names to sets of
            alternative names that should be remapped to the canonical name
            during normalization. Defaults to an empty dictionary.
    """
    allow_empty: bool = False
    normalize_columns: bool = True
    drop_empty_rows: bool = True
    drop_empty_cols: bool = True
    warn_on_duplicate_cols: bool = True
    default_aliases: Dict[str, Set[str]] = field(default_factory=dict)


class BaseDFMixin:
    """Base class for all DataFrame mixins.

    Each mixin accepts an optional :class:`DataFramePolicy` instance to
    control its behavior. If no policy is provided, a default one is
    instantiated.
    """
    def __init__(self, policy: Optional[DataFramePolicy] = None) -> None:
        self.policy = policy or DataFramePolicy()
