# -*- coding: utf-8 -*-
"""Column Resolver Service.

DataFrame 컬럼명 해석 서비스:
- alias → 실제 컬럼명 매핑
- 대소문자 무시, strip 처리
- preset 또는 custom alias 지원

Example:
    >>> resolver = ColumnResolver({"cas": ["cas", "cas no", "상품코드"]})
    >>> actual_col = resolver.resolve(df, "cas")
    >>> print(actual_col)  # "CAS No"
"""

from __future__ import annotations
from typing import Dict, List, Optional
import pandas as pd


class ColumnResolver:
    """Column alias resolver for DataFrame.
    
    Attributes:
        aliases: Column alias mapping {key: [alias1, alias2, ...]}
    
    Example:
        >>> # From preset
        >>> from xl_utils.presets import get_preset
        >>> aliases = get_preset("PRODUCT_LIST")
        >>> resolver = ColumnResolver(aliases)
        
        >>> # Custom aliases
        >>> resolver = ColumnResolver({
        ...     "date": ["날짜", "date"],
        ...     "cas": ["cas", "cas no", "상품코드"]
        ... })
        
        >>> # Resolve column
        >>> actual_col = resolver.resolve(df, "cas")
        >>> if actual_col:
        ...     df[actual_col]  # Access actual column
    """
    
    def __init__(self, aliases: Optional[Dict[str, List[str]]] = None):
        """Initialize ColumnResolver.
        
        Args:
            aliases: Column alias mapping {key: [alias1, alias2, ...]}
        """
        self.aliases = aliases or {}
    
    def resolve(
        self,
        df: pd.DataFrame,
        key: str
    ) -> Optional[str]:
        """Resolve alias key to actual column name.
        
        Args:
            df: pandas DataFrame
            key: Alias key (e.g., "cas", "date")
        
        Returns:
            Actual column name if found, None otherwise
        
        Example:
            >>> resolver = ColumnResolver({"cas": ["cas", "cas no", "상품코드"]})
            >>> actual_col = resolver.resolve(df, "cas")
            >>> if actual_col:
            ...     print(df[actual_col])
        """
        alias_list = self.aliases.get(key, [])
        if not alias_list:
            return None
        
        # DataFrame 컬럼명 소문자 변환
        for col in df.columns:
            col_lower = str(col).lower().strip()
            
            # alias 목록과 비교
            for alias in alias_list:
                if col_lower == alias.lower().strip():
                    return col  # 원본 컬럼명 반환
        
        return None
    
    def resolve_all(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Optional[str]]:
        """Resolve all alias keys to actual column names.
        
        Args:
            df: pandas DataFrame
        
        Returns:
            Dictionary {key: actual_column_name}
        
        Example:
            >>> resolver = ColumnResolver(get_preset("PRODUCT_LIST"))
            >>> resolved = resolver.resolve_all(df)
            >>> print(resolved)
            {'date': '날짜', 'cas': 'CAS No', 'shop': 'Shop', ...}
        """
        result = {}
        for key in self.aliases.keys():
            result[key] = self.resolve(df, key)
        
        return result
    
    def get_column(
        self,
        df: pd.DataFrame,
        key: str,
        default: Any = None
    ) -> pd.Series:
        """Get DataFrame column by alias key.
        
        Args:
            df: pandas DataFrame
            key: Alias key (e.g., "cas")
            default: Default value if column not found
        
        Returns:
            pandas Series or default value
        
        Example:
            >>> resolver = ColumnResolver(get_preset("PRODUCT_LIST"))
            >>> cas_series = resolver.get_column(df, "cas")
            >>> print(cas_series)
        """
        actual_col = self.resolve(df, key)
        if actual_col is None:
            return default
        
        return df[actual_col]
    
    def has_column(
        self,
        df: pd.DataFrame,
        key: str
    ) -> bool:
        """Check if alias key exists in DataFrame.
        
        Args:
            df: pandas DataFrame
            key: Alias key
        
        Returns:
            True if column exists, False otherwise
        """
        return self.resolve(df, key) is not None


__all__ = ["ColumnResolver"]
