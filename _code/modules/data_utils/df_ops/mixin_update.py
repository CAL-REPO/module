from .base import BaseDFMixin

class DataFrameUpdateMixin(BaseDFMixin):
    """행 업데이트 기능"""
    def update_rows(self, df, where, updates: dict):
        mask = df.eval(where) if isinstance(where, str) else where
        for k, v in updates.items():
            df.loc[mask, k] = v
        return df
