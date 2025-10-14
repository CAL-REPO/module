"""Data creation mixin from dictionaries.

Provides methods to create DataFrames and other structures from dict sources.
"""

import pandas as pd
from typing import Dict, List, Any

from ...core import BaseOperationsMixin, BaseOperationsPolicy


class FromDictMixin(BaseOperationsMixin):
    """Mixin for creating structured data from dictionaries.
    
    Provides methods to convert dictionaries into DataFrames or other
    structured formats with validation and normalization.
    """
    
    def _default_policy(self) -> BaseOperationsPolicy:
        """Return default policy."""
        return BaseOperationsPolicy()
    
    def dict_to_df(
        self,
        data: Dict[str, List[Any]] | List[Dict[str, Any]],
        validate: bool = True
    ) -> pd.DataFrame:
        """Create DataFrame from dictionary.
        
        Args:
            data: Dictionary of lists or list of dicts to convert.
            validate: If True, validate the resulting DataFrame.
        
        Returns:
            A pandas DataFrame.
        
        Raises:
            ValueError: If validation fails and policy requires it.
        
        Example:
            >>> mixin = FromDictMixin()
            >>> data = {'A': [1, 2, 3], 'B': [4, 5, 6]}
            >>> df = mixin.dict_to_df(data)
        """
        df = pd.DataFrame(data)
        
        if validate and hasattr(self, 'policy'):
            policy = self.policy
            if hasattr(policy, 'allow_empty') and not policy.allow_empty:
                if df.empty:
                    raise ValueError("Empty DataFrame not allowed by policy")
        
        return df
    
    def dicts_to_df(
        self,
        records: List[Dict[str, Any]],
        validate: bool = True
    ) -> pd.DataFrame:
        """Create DataFrame from list of dictionaries.
        
        Args:
            records: List of dictionaries, each representing a row.
            validate: If True, validate the resulting DataFrame.
        
        Returns:
            A pandas DataFrame.
        
        Example:
            >>> mixin = FromDictMixin()
            >>> records = [{'A': 1, 'B': 2}, {'A': 3, 'B': 4}]
            >>> df = mixin.dicts_to_df(records)
        """
        return self.dict_to_df(records, validate=validate)
