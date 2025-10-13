import pandas as pd
from typing import Any, List
from .base import BaseDFMixin

class DataFrameCreateMixin(BaseDFMixin):
    """DataFrame 생성 관련 기능"""
    def to_dataframe(self, records: List[dict[str, Any]], columns: List[str] | None = None) -> pd.DataFrame:
        df = pd.DataFrame.from_records(records, columns=columns)
        if not self.policy.allow_empty and df.empty:
            raise ValueError("Empty DataFrame not allowed by policy.")
        return df
