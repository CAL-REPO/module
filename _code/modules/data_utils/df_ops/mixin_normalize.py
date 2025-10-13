from .base import BaseDFMixin

class DataFrameNormalizeMixin(BaseDFMixin):
    """Mixin for column normalization and alias handling.

    This mixin provides a method to rename columns based on a provided alias
    mapping. It does not alter the DataFrame if no aliases are given.
    """
    def normalize_columns(self, df, aliases: dict[str, str] | None = None):
        """Rename DataFrame columns using a simple alias mapping.

        Args:
            df: The DataFrame to operate on.
            aliases: A mapping from existing column names to new column names.

        Returns:
            The DataFrame with columns renamed. If ``aliases`` is ``None`` or empty,
            the DataFrame is returned unchanged.
        """
        if aliases:
            df = df.rename(columns=aliases)
        return df
