"""Composite DataFrame operations class.

This module defines :class:`DataFrameOps`, a high‑level composite class
that aggregates multiple mixins to provide a unified interface for
creating, normalizing, filtering, updating and cleaning pandas
``DataFrame`` objects.  It is conceptually similar to the prior
``dataframe_ops`` module, but renamed to ``df_ops`` for consistency.
"""

from typing import Optional
from .base import DataFramePolicy
from .mixin_create import DataFrameCreateMixin
from .mixin_normalize import DataFrameNormalizeMixin
from .mixin_filter import DataFrameFilterMixin
from .mixin_update import DataFrameUpdateMixin
from .mixin_clean import DataFrameCleanMixin


class DataFrameOps(
    DataFrameCreateMixin,
    DataFrameNormalizeMixin,
    DataFrameFilterMixin,
    DataFrameUpdateMixin,
    DataFrameCleanMixin,
):
    """High‑level composite for DataFrame operations.

    Inherits functionality from the various DataFrame mixins to provide a
    unified interface for creation, normalization, filtering, updating,
    and cleaning operations on pandas DataFrames.
    """

    def __init__(self, policy: Optional[DataFramePolicy] = None) -> None:
        """Initialize the composite with an optional policy."""
        super().__init__(policy)
