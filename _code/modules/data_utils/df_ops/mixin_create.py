import pandas as pd
from typing import Any, List
from .base import BaseDFMixin

class DataFrameCreateMixin(BaseDFMixin):
    """Mixin providing DataFrame creation functionality.

    Provides a method to construct a DataFrame from a list of record
    dictionaries and validates emptiness according to the configured policy.
    """
    def to_dataframe(self, records: List[dict[str, Any]], columns: List[str] | None = None) -> pd.DataFrame:
        """Create a DataFrame from records, enforcing policy around emptiness.

        Args:
            records: A list of dictionaries representing rows.
            columns: Optional list of columns to enforce order and include missing columns.

        Raises:
            ValueError: If the resulting DataFrame is empty and the policy does not allow it.

        Returns:
            A ``pandas.DataFrame`` constructed from the given records.
        """
        df = pd.DataFrame.from_records(records, columns=columns)
        if not self.policy.allow_empty and df.empty:
            raise ValueError("Empty DataFrame not allowed by policy.")
        return df
