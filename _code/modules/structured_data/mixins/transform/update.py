"""Data update mixin for various data structures.

Provides update operations across DataFrames, dicts, lists, etc.
"""

import pandas as pd
from typing import Dict, List, Any, Callable

from ...core import BaseOperationsMixin, BaseOperationsPolicy


class UpdateMixin(BaseOperationsMixin):
    """Mixin for updating data across different structures.
    
    Provides methods to update values, apply transformations,
    and modify data in place or copy.
    """
    
    def _default_policy(self) -> BaseOperationsPolicy:
        """Return default policy."""
        return BaseOperationsPolicy()
    
    def update_df_column(
        self,
        df: pd.DataFrame,
        column: str,
        func: Callable[[Any], Any]
    ) -> pd.DataFrame:
        """Update DataFrame column by applying function.
        
        Args:
            df: The DataFrame to update.
            column: Name of the column to update.
            func: Function to apply to each value in the column.
        
        Returns:
            DataFrame with updated column.
        
        Example:
            >>> mixin = UpdateMixin()
            >>> df = pd.DataFrame({'A': [1, 2, 3]})
            >>> mixin.update_df_column(df, 'A', lambda x: x * 2)
            # Returns df with column A doubled
        """
        df = df.copy()
        df[column] = df[column].apply(func)
        return df
    
    def update_dict_values(
        self,
        d: Dict[str, Any],
        func: Callable[[Any], Any],
        keys: List[str] | None = None
    ) -> Dict[str, Any]:
        """Update dictionary values by applying function.
        
        Args:
            d: The dictionary to update.
            func: Function to apply to values.
            keys: Optional list of keys to update. If None, updates all.
        
        Returns:
            Dictionary with updated values.
        
        Example:
            >>> mixin = UpdateMixin()
            >>> mixin.update_dict_values(
            ...     {'a': 1, 'b': 2},
            ...     lambda x: x * 2,
            ...     keys=['a']
            ... )
            {'a': 2, 'b': 2}
        """
        result = d.copy()
        if keys is None:
            keys = list(d.keys())
        
        for k in keys:
            if k in result:
                result[k] = func(result[k])
        return result
    
    def update_list_elements(
        self,
        lst: List[Any],
        func: Callable[[Any], Any],
        indices: List[int] | None = None
    ) -> List[Any]:
        """Update list elements by applying function.
        
        Args:
            lst: The list to update.
            func: Function to apply to elements.
            indices: Optional list of indices to update. If None, updates all.
        
        Returns:
            List with updated elements.
        
        Example:
            >>> mixin = UpdateMixin()
            >>> mixin.update_list_elements([1, 2, 3], lambda x: x * 2)
            [2, 4, 6]
        """
        result = lst.copy()
        if indices is None:
            indices = range(len(lst))
        
        for i in indices:
            if 0 <= i < len(result):
                result[i] = func(result[i])
        return result
