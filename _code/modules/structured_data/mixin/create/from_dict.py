
# -*- coding: utf-8 -*-
"""
structured_data.mixin.create.from_dict
-------------------------------------
Role-based mixin for creating structured data from dict objects.
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from ...core import BaseOperationsMixin


class FromDictMixin(BaseOperationsMixin):
    """Create DataFrame from dict mixin.
    
    Provides methods to convert dictionaries to DataFrames
    with various orientations and configurations.
    
    Attributes:
        policy: Policy instance controlling creation behavior.
    """
    
    def from_dict_records(self, data: list[dict]) -> pd.DataFrame:
        """Create DataFrame from list of dictionaries (records orientation).
        
        Args:
            data: List of dictionaries where each dict is a row.
        
        Returns:
            DataFrame created from records.
        
        Example:
            >>> from_dict_records([
            ...     {'name': 'Alice', 'age': 30},
            ...     {'name': 'Bob', 'age': 25}
            ... ])
        """
        import pandas as pd
        return pd.DataFrame.from_records(data)
    
    def from_dict_dict(
        self, 
        data: dict, 
        orient: str = 'columns'
    ) -> pd.DataFrame:
        """Create DataFrame from dictionary of arrays/lists.
        
        Args:
            data: Dictionary where keys are column names.
            orient: Orientation - 'columns' (default) or 'index'.
        
        Returns:
            DataFrame created from dict.
        
        Example:
            >>> from_dict_dict({
            ...     'name': ['Alice', 'Bob'],
            ...     'age': [30, 25]
            ... })
        """
        import pandas as pd
        return pd.DataFrame.from_dict(data, orient=orient)
    
    def from_dict_auto(self, data: Any) -> pd.DataFrame:
        """Auto-detect dict structure and create DataFrame.
        
        Args:
            data: Dictionary or list of dictionaries.
        
        Returns:
            DataFrame created from data.
        
        Raises:
            TypeError: If data cannot be converted to DataFrame.
        """
        import pandas as pd
        
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # List of dicts -> records
            return self.from_dict_records(data)
        elif isinstance(data, dict):
            # Check if values are lists/arrays (columns orientation)
            first_value = next(iter(data.values()), None)
            if isinstance(first_value, (list, tuple)):
                return self.from_dict_dict(data, orient='columns')
            else:
                # Single record -> wrap in list
                return pd.DataFrame([data])
        else:
            raise TypeError(f"Cannot convert {type(data)} to DataFrame")
