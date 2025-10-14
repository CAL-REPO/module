"""Data filtering mixin for various data structures.

Provides filtering operations across DataFrames, dicts, lists, etc.
"""

import pandas as pd
from typing import Dict, List, Any, Callable

from ...core import BaseOperationsMixin, BaseOperationsPolicy


class FilterMixin(BaseOperationsMixin):
    """Mixin for filtering data across different structures.
    
    Provides methods to filter rows, entries, or elements based on
    various conditions.
    """
    
    def _default_policy(self) -> BaseOperationsPolicy:
        """Return default policy."""
        return BaseOperationsPolicy()
    
    def filter_df(
        self,
        df: pd.DataFrame,
        condition: str | pd.Series
    ) -> pd.DataFrame:
        """Filter DataFrame rows using query or boolean mask.
        
        Args:
            df: The DataFrame to filter.
            condition: Either a string query or boolean mask.
        
        Returns:
            Filtered DataFrame.
        
        Example:
            >>> mixin = FilterMixin()
            >>> df = pd.DataFrame({'A': [1, 2, 3]})
            >>> mixin.filter_df(df, 'A > 1')
            # Returns rows where A > 1
        """
        if isinstance(condition, str):
            return df.query(condition)
        else:
            return df.loc[condition]
    
    def filter_dict(
        self,
        d: Dict[str, Any],
        predicate: Callable[[str, Any], bool]
    ) -> Dict[str, Any]:
        """Filter dictionary entries using predicate function.
        
        Args:
            d: The dictionary to filter.
            predicate: Function that takes (key, value) and returns bool.
        
        Returns:
            Filtered dictionary.
        
        Example:
            >>> mixin = FilterMixin()
            >>> mixin.filter_dict(
            ...     {'a': 1, 'b': 2, 'c': 3},
            ...     lambda k, v: v > 1
            ... )
            {'b': 2, 'c': 3}
        """
        return {k: v for k, v in d.items() if predicate(k, v)}
    
    def filter_list(
        self,
        lst: List[Any],
        predicate: Callable[[Any], bool]
    ) -> List[Any]:
        """Filter list elements using predicate function.
        
        Args:
            lst: The list to filter.
            predicate: Function that takes an element and returns bool.
        
        Returns:
            Filtered list.
        
        Example:
            >>> mixin = FilterMixin()
            >>> mixin.filter_list([1, 2, 3, 4], lambda x: x > 2)
            [3, 4]
        """
        return [x for x in lst if predicate(x)]
