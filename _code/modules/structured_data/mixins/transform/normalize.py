"""Data normalization mixin for various data structures.

Provides normalization operations (column/key renaming, value standardization)
across different data structures.
"""

import pandas as pd
from typing import Dict, Any, Optional

from ...core import BaseOperationsMixin, BaseOperationsPolicy


class NormalizeMixin(BaseOperationsMixin):
    """Mixin for normalizing data across different structures.
    
    Provides methods to normalize column names, dictionary keys,
    and values across various data types.
    """
    
    def _default_policy(self) -> BaseOperationsPolicy:
        """Return default policy."""
        return BaseOperationsPolicy()
    
    def normalize_df_columns(
        self,
        df: pd.DataFrame,
        aliases: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """Rename DataFrame columns using alias mapping.
        
        Args:
            df: The DataFrame to normalize.
            aliases: A mapping from existing column names to new names.
        
        Returns:
            The DataFrame with normalized columns.
        
        Example:
            >>> mixin = NormalizeMixin()
            >>> df = pd.DataFrame({'old_name': [1, 2]})
            >>> mixin.normalize_df_columns(df, {'old_name': 'new_name'})
            # Returns df with column renamed
        """
        if aliases:
            df = df.rename(columns=aliases)
        return df
    
    def normalize_dict_keys(
        self,
        d: Dict[str, Any],
        aliases: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Rename dictionary keys using alias mapping.
        
        Args:
            d: The dictionary to normalize.
            aliases: A mapping from existing keys to new keys.
        
        Returns:
            Dictionary with normalized keys.
        
        Example:
            >>> mixin = NormalizeMixin()
            >>> mixin.normalize_dict_keys(
            ...     {'old_key': 1},
            ...     {'old_key': 'new_key'}
            ... )
            {'new_key': 1}
        """
        if not aliases:
            return d
        return {aliases.get(k, k): v for k, v in d.items()}
    
    def normalize_string(self, s: str, lowercase: bool = True, strip: bool = True) -> str:
        """Normalize string value.
        
        Args:
            s: The string to normalize.
            lowercase: If True, convert to lowercase.
            strip: If True, strip whitespace.
        
        Returns:
            Normalized string.
        """
        if strip:
            s = s.strip()
        if lowercase:
            s = s.lower()
        return s
    
    def normalize_values(
        self,
        data: Any,
        normalizer: Optional[callable] = None
    ) -> Any:
        """Apply normalization function to all values in data structure.
        
        Args:
            data: Data to normalize (DataFrame, dict, list, etc.).
            normalizer: Function to apply to each value.
        
        Returns:
            Data with normalized values.
        """
        if normalizer is None:
            normalizer = lambda x: x
        
        if isinstance(data, pd.DataFrame):
            return data.applymap(normalizer)
        elif isinstance(data, dict):
            return {k: normalizer(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [normalizer(x) for x in data]
        else:
            return normalizer(data)
