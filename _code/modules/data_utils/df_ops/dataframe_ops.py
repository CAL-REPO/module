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
    """DataFrame 고수준 조작 인터페이스"""
    def __init__(self, policy: Optional[DataFramePolicy] = None):
        super().__init__(policy)
