from .base import BaseDFMixin

class DataFrameCleanMixin(BaseDFMixin):
    """Mixin for dropping empty rows or columns from a DataFrame.

    Uses ``pandas.DataFrame.dropna`` under the hood to remove rows or columns
    where all values are missing.
    """
    def drop_empty(self, df, axis=0):
        """Drop rows or columns from the DataFrame that contain only missing values.

        Args:
            df: The DataFrame to clean.
            axis: ``0`` to drop rows or ``1`` to drop columns. Defaults to ``0``.

        Returns:
            The DataFrame with empty rows or columns removed.
        """
        return df.dropna(axis=axis, how="all")
