from .base import BaseDFMixin

class DataFrameUpdateMixin(BaseDFMixin):
    """Mixin for updating rows in a DataFrame.

    Provides a method to modify column values where a given condition is met.
    """
    def update_rows(self, df, where, updates: dict):
        """Update values in the DataFrame according to a condition.

        Args:
            df: The DataFrame to update.
            where: Either a string evaluated via ``DataFrame.eval`` or a boolean mask.
            updates: A mapping of column names to new values.

        Returns:
            The modified DataFrame with updates applied.
        """
        mask = df.eval(where) if isinstance(where, str) else where
        for k, v in updates.items():
            df.loc[mask, k] = v
        return df
