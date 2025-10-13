from .base import BaseDFMixin

class DataFrameCleanMixin(BaseDFMixin):
    """비어있는 행/열 드롭"""
    def drop_empty(self, df, axis=0):
        return df.dropna(axis=axis, how="all")
