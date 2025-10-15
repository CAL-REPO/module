
# -*- coding: utf-8 -*-
"""
structured_data.mixin.transform.update
-------------------------------------
Role-based mixin for update operations in structured data transformation.
Supports DataFrame and dict data types.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from ...core import BaseOperationsMixin


class UpdateMixin(BaseOperationsMixin):
    """Data update mixin for modifying values.
    
    Works with:
    - pandas.DataFrame: update cells, apply functions
    - dict: update values
    
    Attributes:
        policy: Policy instance controlling update behavior.
    """
    
    def update_cell_df(
        self, 
        df: pd.DataFrame, 
        row_index: Any, 
        column: str, 
        value: Any
    ) -> pd.DataFrame:
        """Update a single cell in DataFrame.
        
        Args:
            df: Input DataFrame.
            row_index: Row index (integer or label).
            column: Column name.
            value: New value.
        
        Returns:
            DataFrame with updated cell.
        """
        result = df.copy()
        result.loc[row_index, column] = value
        return result
    
    def update_where_df(
        self, 
        df: pd.DataFrame, 
        condition: Any, 
        value: Any,
        column: Optional[str] = None
    ) -> pd.DataFrame:
        """Update values where condition is True.
        
        Args:
            df: Input DataFrame.
            condition: Boolean mask or callable.
            value: New value or callable.
            column: Optional column name to update (None = all columns).
        
        Returns:
            DataFrame with updated values.
        """
        result = df.copy()
        
        if column:
            result.loc[condition, column] = value
        else:
            result.loc[condition] = value
        
        return result
    
    def update_dict(
        self, 
        data: dict, 
        updates: dict
    ) -> dict:
        """Update dictionary with new key-value pairs.
        
        Args:
            data: Input dictionary.
            updates: Dictionary of updates to apply.
        
        Returns:
            Updated dictionary.
        """
        result = data.copy()
        result.update(updates)
        return result
    
    def update(
        self, 
        data: Any,
        **kwargs
    ) -> Any:
        """Auto-detect data type and apply appropriate update.
        
        Args:
            data: DataFrame or dict to update.
            **kwargs: Update parameters.
        
        Returns:
            Updated data of the same type.
        
        Raises:
            TypeError: If data type is not supported.
        """
        import pandas as pd
        
        if isinstance(data, pd.DataFrame):
            if 'updates' in kwargs:
                return self.update_dict(data.to_dict(), kwargs['updates'])
            return data
        
        elif isinstance(data, dict):
            if 'updates' in kwargs:
                return self.update_dict(data, kwargs['updates'])
            return data
        
        else:
            raise TypeError(f"Unsupported data type for update: {type(data)}")
