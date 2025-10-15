
# -*- coding: utf-8 -*-
"""
structured_data.mixin.transform.filter
-------------------------------------
Role-based mixin for filtering operations in structured data transformation.
Supports DataFrame, dict, and list data types.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from ...core import BaseOperationsMixin


class FilterMixin(BaseOperationsMixin):
    """Data filtering mixin for conditional row/item selection.
    
    Works with:
    - pandas.DataFrame: filter rows by query or callable
    - dict: filter items by predicate
    - list: filter items by predicate
    
    Attributes:
        policy: Policy instance controlling filtering behavior.
    """
    
    def filter_df_query(self, df: pd.DataFrame, query: str) -> pd.DataFrame:
        """Filter DataFrame rows using pandas query string.
        
        Args:
            df: Input DataFrame.
            query: Pandas query expression (e.g., "age > 30 and city == 'Seoul'").
        
        Returns:
            Filtered DataFrame.
        
        Example:
            >>> filter_df_query(df, "price > 1000 and category == 'Electronics'")
        """
        return df.query(query)
    
    def filter_df_callable(
        self, 
        df: pd.DataFrame, 
        func: Callable[[pd.Series], bool]
    ) -> pd.DataFrame:
        """Filter DataFrame rows using callable predicate.
        
        Args:
            df: Input DataFrame.
            func: Function that takes a row (Series) and returns True to keep.
        
        Returns:
            Filtered DataFrame.
        
        Example:
            >>> filter_df_callable(df, lambda row: row['price'] > 1000)
        """
        mask = df.apply(func, axis=1)
        return df[mask]
    
    def filter_df_columns(
        self, 
        df: pd.DataFrame, 
        columns: list[str],
        exclude: bool = False
    ) -> pd.DataFrame:
        """Filter DataFrame columns (select or exclude).
        
        Args:
            df: Input DataFrame.
            columns: List of column names.
            exclude: If True, exclude columns; if False, select only these columns.
        
        Returns:
            DataFrame with selected/excluded columns.
        """
        if exclude:
            return df.drop(columns=columns)
        else:
            return df[columns]
    
    def filter_dict(
        self, 
        data: dict, 
        predicate: Callable[[Any, Any], bool]
    ) -> dict:
        """Filter dictionary items by predicate.
        
        Args:
            data: Input dictionary.
            predicate: Function that takes (key, value) and returns True to keep.
        
        Returns:
            Filtered dictionary.
        
        Example:
            >>> filter_dict(data, lambda k, v: v > 100)
        """
        return {k: v for k, v in data.items() if predicate(k, v)}
    
    def filter_list(
        self, 
        data: list, 
        predicate: Callable[[Any], bool]
    ) -> list:
        """Filter list items by predicate.
        
        Args:
            data: Input list.
            predicate: Function that takes item and returns True to keep.
        
        Returns:
            Filtered list.
        
        Example:
            >>> filter_list(data, lambda x: x > 0)
        """
        return [item for item in data if predicate(item)]
    
    def filter(
        self, 
        data: Any, 
        condition: str | Callable | None = None,
        **kwargs
    ) -> Any:
        """Auto-detect data type and apply appropriate filtering.
        
        Args:
            data: DataFrame, dict, or list to filter.
            condition: Query string (for DataFrame) or callable predicate.
            **kwargs: Additional arguments (e.g., columns for DataFrame).
        
        Returns:
            Filtered data of the same type.
        
        Raises:
            TypeError: If data type is not supported.
            ValueError: If condition is invalid for data type.
        """
        import pandas as pd
        
        if isinstance(data, pd.DataFrame):
            if isinstance(condition, str):
                return self.filter_df_query(data, condition)
            elif callable(condition):
                return self.filter_df_callable(data, condition)
            elif 'columns' in kwargs:
                return self.filter_df_columns(
                    data, 
                    kwargs['columns'], 
                    exclude=kwargs.get('exclude', False)
                )
            else:
                raise ValueError("DataFrame filtering requires query string, callable, or columns")
        
        elif isinstance(data, dict):
            if callable(condition):
                return self.filter_dict(data, condition)
            else:
                raise ValueError("Dict filtering requires callable predicate")
        
        elif isinstance(data, list):
            if callable(condition):
                return self.filter_list(data, condition)
            else:
                raise ValueError("List filtering requires callable predicate")
        
        else:
            raise TypeError(f"Unsupported data type for filtering: {type(data)}")
