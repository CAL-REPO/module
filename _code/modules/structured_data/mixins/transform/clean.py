"""Data cleaning mixin for various data structures.

Provides cleaning operations that work across DataFrames, dicts, lists, etc.
"""

import pandas as pd
from typing import Dict, List, Any

from ...core import BaseOperationsMixin, BaseOperationsPolicy


class CleanMixin(BaseOperationsMixin):
    """Mixin for cleaning data across different structures.
    
    Provides methods to remove empty/null values from DataFrames,
    dictionaries, lists, and other data structures.
    """
    
    def _default_policy(self) -> BaseOperationsPolicy:
        """Return default policy."""
        return BaseOperationsPolicy()
    
    def drop_empty_df(self, df: pd.DataFrame, axis=0) -> pd.DataFrame:
        """Drop rows or columns from DataFrame containing only missing values.
        
        Args:
            df: The DataFrame to clean.
            axis: ``0`` to drop rows or ``1`` to drop columns. Defaults to ``0``.
        
        Returns:
            The DataFrame with empty rows or columns removed.
        
        Example:
            >>> mixin = CleanMixin()
            >>> df = pd.DataFrame({'A': [1, None], 'B': [None, None]})
            >>> mixin.drop_empty_df(df, axis=1)
            # Returns df with column 'B' removed
        """
        return df.dropna(axis=axis, how="all")
    
    def drop_empty_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Remove entries with None or empty values from dictionary.
        
        Args:
            d: The dictionary to clean.
        
        Returns:
            Dictionary with empty values removed.
        
        Example:
            >>> mixin = CleanMixin()
            >>> mixin.drop_empty_dict({'a': 1, 'b': None, 'c': ''})
            {'a': 1}
        """
        return {k: v for k, v in d.items() if v not in (None, '', [])}
    
    def drop_empty_list(self, lst: List[Any]) -> List[Any]:
        """Remove None and empty values from list.
        
        Args:
            lst: The list to clean.
        
        Returns:
            List with empty values removed.
        
        Example:
            >>> mixin = CleanMixin()
            >>> mixin.drop_empty_list([1, None, '', 2, []])
            [1, 2]
        """
        return [x for x in lst if x not in (None, '', [])]
    
    def drop_null_values(self, data: Any) -> Any:
        """Remove null values from any data structure.
        
        Automatically detects the data type and applies appropriate cleaning.
        
        Args:
            data: Data to clean (DataFrame, dict, list, etc.).
        
        Returns:
            Cleaned data of the same type.
        """
        if isinstance(data, pd.DataFrame):
            return self.drop_empty_df(data)
        elif isinstance(data, dict):
            return self.drop_empty_dict(data)
        elif isinstance(data, list):
            return self.drop_empty_list(data)
        else:
            return data
