
# -*- coding: utf-8 -*-
"""
structured_data.mixin.transform.clean
-------------------------------------
Role-based mixin for cleaning operations in structured data transformation.
Supports DataFrame, dict, and list data types.
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from ...core import BaseOperationsMixin


class CleanMixin(BaseOperationsMixin):
    """Data cleaning mixin for removing empty/null values and duplicates.
    
    Works with:
    - pandas.DataFrame: drop empty rows/columns, remove duplicates
    - dict: remove None/empty values
    - list: remove None/empty items
    
    Attributes:
        policy: Policy instance controlling cleaning behavior.
    """
    
    def drop_empty_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop empty rows and columns from DataFrame.
        
        Args:
            df: Input DataFrame.
        
        Returns:
            Cleaned DataFrame with empty rows/columns removed.
        """
        import pandas as pd
        
        result = df.copy()
        
        if hasattr(self.policy, 'drop_empty_rows') and self.policy.drop_empty_rows:
            # Drop rows where all values are NaN/None
            result = result.dropna(how='all')
        
        if hasattr(self.policy, 'drop_empty_cols') and self.policy.drop_empty_cols:
            # Drop columns where all values are NaN/None
            result = result.dropna(axis=1, how='all')
        
        return result
    
    def drop_duplicates_df(self, df: pd.DataFrame, subset: Optional[list] = None) -> pd.DataFrame:
        """Remove duplicate rows from DataFrame.
        
        Args:
            df: Input DataFrame.
            subset: Column labels to consider for identifying duplicates.
        
        Returns:
            DataFrame with duplicates removed.
        """
        return df.drop_duplicates(subset=subset, keep='first')
    
    def strip_strings_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Strip whitespace from all string columns in DataFrame.
        
        Args:
            df: Input DataFrame.
        
        Returns:
            DataFrame with stripped strings.
        """
        import pandas as pd
        
        result = df.copy()
        
        # Apply strip to string columns
        for col in result.columns:
            if result[col].dtype == 'object':
                result[col] = result[col].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
        
        return result
    
    def drop_empty_dict(self, data: dict) -> dict:
        """Remove None/empty values from dictionary.
        
        Args:
            data: Input dictionary.
        
        Returns:
            Dictionary with None/empty values removed.
        """
        return {
            k: v for k, v in data.items()
            if v is not None and v != '' and v != []
        }
    
    def drop_empty_list(self, data: list) -> list:
        """Remove None/empty items from list.
        
        Args:
            data: Input list.
        
        Returns:
            List with None/empty items removed.
        """
        return [
            item for item in data
            if item is not None and item != '' and item != []
        ]
    
    def clean(self, data: Any) -> Any:
        """Auto-detect data type and apply appropriate cleaning.
        
        Args:
            data: DataFrame, dict, or list to clean.
        
        Returns:
            Cleaned data of the same type.
        
        Raises:
            TypeError: If data type is not supported.
        """
        import pandas as pd
        
        if isinstance(data, pd.DataFrame):
            result = self.drop_empty_df(data)
            result = self.strip_strings_df(result)
            return result
        elif isinstance(data, dict):
            return self.drop_empty_dict(data)
        elif isinstance(data, list):
            return self.drop_empty_list(data)
        else:
            raise TypeError(f"Unsupported data type for cleaning: {type(data)}")
