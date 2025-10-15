
# -*- coding: utf-8 -*-
"""
structured_data.mixin.transform.normalize
----------------------------------------
Role-based mixin for normalization operations in structured data transformation.
Supports DataFrame and dict data types.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from ...core import BaseOperationsMixin


class NormalizeMixin(BaseOperationsMixin):
    """Data normalization mixin for column names and values.
    
    Works with:
    - pandas.DataFrame: normalize column names, apply transformations
    - dict: normalize keys, transform values
    
    Attributes:
        policy: Policy instance controlling normalization behavior.
    """
    
    def normalize_column_names_df(
        self, 
        df: pd.DataFrame,
        lowercase: bool = True,
        strip: bool = True,
        replace_spaces: bool = True
    ) -> pd.DataFrame:
        """Normalize DataFrame column names.
        
        Args:
            df: Input DataFrame.
            lowercase: Convert to lowercase.
            strip: Strip whitespace.
            replace_spaces: Replace spaces with underscores.
        
        Returns:
            DataFrame with normalized column names.
        """
        result = df.copy()
        columns = list(result.columns)
        
        for i, col in enumerate(columns):
            if isinstance(col, str):
                normalized = col
                if strip:
                    normalized = normalized.strip()
                if lowercase:
                    normalized = normalized.lower()
                if replace_spaces:
                    normalized = normalized.replace(' ', '_')
                columns[i] = normalized
        
        result.columns = columns
        return result
    
    def apply_to_column_df(
        self, 
        df: pd.DataFrame, 
        column: str, 
        func: Callable[[Any], Any]
    ) -> pd.DataFrame:
        """Apply transformation function to a specific column.
        
        Args:
            df: Input DataFrame.
            column: Column name.
            func: Transformation function.
        
        Returns:
            DataFrame with transformed column.
        """
        result = df.copy()
        result[column] = result[column].apply(func)
        return result
    
    def rename_columns_df(
        self, 
        df: pd.DataFrame, 
        mapping: dict[str, str]
    ) -> pd.DataFrame:
        """Rename DataFrame columns using mapping.
        
        Args:
            df: Input DataFrame.
            mapping: Dictionary mapping old names to new names.
        
        Returns:
            DataFrame with renamed columns.
        """
        return df.rename(columns=mapping)
    
    def normalize_dict_keys(
        self, 
        data: dict,
        lowercase: bool = True,
        strip: bool = True,
        replace_spaces: bool = True
    ) -> dict:
        """Normalize dictionary keys (similar to column normalization).
        
        Args:
            data: Input dictionary.
            lowercase: Convert to lowercase.
            strip: Strip whitespace.
            replace_spaces: Replace spaces with underscores.
        
        Returns:
            Dictionary with normalized keys.
        """
        result = {}
        for key, value in data.items():
            if isinstance(key, str):
                normalized_key = key
                if strip:
                    normalized_key = normalized_key.strip()
                if lowercase:
                    normalized_key = normalized_key.lower()
                if replace_spaces:
                    normalized_key = normalized_key.replace(' ', '_')
                result[normalized_key] = value
            else:
                result[key] = value
        return result
    
    def apply_to_values_dict(
        self, 
        data: dict, 
        func: Callable[[Any], Any]
    ) -> dict:
        """Apply transformation function to all dictionary values.
        
        Args:
            data: Input dictionary.
            func: Transformation function.
        
        Returns:
            Dictionary with transformed values.
        """
        return {k: func(v) for k, v in data.items()}
    
    def normalize(
        self, 
        data: Any,
        **kwargs
    ) -> Any:
        """Auto-detect data type and apply appropriate normalization.
        
        Args:
            data: DataFrame or dict to normalize.
            **kwargs: Normalization options (lowercase, strip, replace_spaces).
        
        Returns:
            Normalized data of the same type.
        
        Raises:
            TypeError: If data type is not supported.
        """
        import pandas as pd
        
        if isinstance(data, pd.DataFrame):
            if hasattr(self.policy, 'normalize_columns') and self.policy.normalize_columns:
                return self.normalize_column_names_df(
                    data,
                    lowercase=kwargs.get('lowercase', True),
                    strip=kwargs.get('strip', True),
                    replace_spaces=kwargs.get('replace_spaces', True)
                )
            return data
        
        elif isinstance(data, dict):
            return self.normalize_dict_keys(
                data,
                lowercase=kwargs.get('lowercase', True),
                strip=kwargs.get('strip', True),
                replace_spaces=kwargs.get('replace_spaces', True)
            )
        
        else:
            raise TypeError(f"Unsupported data type for normalization: {type(data)}")
