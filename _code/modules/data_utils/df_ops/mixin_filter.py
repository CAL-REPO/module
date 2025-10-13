from .base import BaseDFMixin

class DataFrameFilterMixin(BaseDFMixin):
    """Mixin for conditional selection and filtering of DataFrame rows.

    Allows selection via a pandas query string or a boolean mask.
    """
    def select(self, df, condition):
        """Select rows from a DataFrame using a query string or boolean mask.

        Args:
            df: The DataFrame to filter.
            condition: Either a string to be evaluated via ``DataFrame.query`` or a
                boolean mask indexable against ``df``.

        Returns:
            A subset of the original DataFrame with rows matching the condition.
        """
        return df.query(condition) if isinstance(condition, str) else df.loc[condition]
