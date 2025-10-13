from .base import BaseDFMixin

class DataFrameFilterMixin(BaseDFMixin):
    """조건 선택 및 필터링"""
    def select(self, df, condition):
        return df.query(condition) if isinstance(condition, str) else df.loc[condition]
