# -*- coding: utf-8 -*-
# data_utils/df_ops.py (리팩토링 버전)
# pandas 중심 DataFrame 정책 및 조작 클래스 구조화

from __future__ import annotations
from typing import Any, Dict, Iterable, Optional, List, Set
import pandas as pd


# ---------------------------------------------------------
# ---------------------------------------------------------
# Unified policy is now defined in :mod:`data_utils.df_ops.base`.  Import it here
# for convenience.
from .df_ops.base import DataFramePolicy  # type: ignore



# ---------------------------------------------------------
# 2️⃣ 컬럼 정규화기
# ---------------------------------------------------------
class DataFrameNormalizer:
    """Normalizes DataFrame column names based on an alias mapping.

    This class lowercases, strips and deduplicates whitespace in column names and then
    maps known aliases back to their canonical names. If duplicate columns are
    detected after normalization, a warning will be printed.

    Args:
        alias_map: A mapping of canonical column names to a set of aliases that
            should be mapped back to the canonical name. The keys in this mapping
            are case-insensitive.
    """

    def __init__(self, alias_map: Optional[Dict[str, Set[str]]] = None):
        self.alias_map = alias_map or {}

    @staticmethod
    def _norm_col(name: Any) -> str:
        """Normalize a single column name by stripping whitespace and lowercasing."""
        s = str(name or "").strip().lower()
        return " ".join(s.split())

    def normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a new DataFrame with normalized column names.

        Column names are normalized and then, if found in the alias map, remapped to
        their canonical name. If duplicate columns exist after normalization and
        ``warn_on_duplicate_cols`` is enabled in the current policy, a warning is printed.

        Args:
            df: The DataFrame whose columns should be normalized.

        Returns:
            A new ``pandas.DataFrame`` with normalized column names.
        """
        reverse_map = {
            alias.lower().strip(): key
            for key, aliases in self.alias_map.items()
            for alias in aliases
        }
        mapper = {col: reverse_map.get(self._norm_col(col), col) for col in df.columns}
        df2 = df.rename(columns=mapper)
        # If duplicates appear after normalization, optionally emit a warning.
        if df2.columns.duplicated().any():
            dupes = df2.columns[df2.columns.duplicated()].tolist()
            print(f"[Warning] Duplicate columns found after normalization: {dupes}")
        return df2


# ---------------------------------------------------------
# 3️⃣ 조건/필터링 로직
# ---------------------------------------------------------
class DataFrameSelector:
    """Helper for building boolean masks to select rows in a DataFrame.

    Given an include/exclude specification, this class constructs a mask that can
    be used to filter a ``pandas.DataFrame``. Each condition is a mapping with
    keys ``"col"`` (column name), ``"op"`` (operation) and an optional value.
    Supported operations are:

    * ``eq``: case-insensitive equality comparison
    * ``in``: membership in a list of values (case-insensitive)
    * ``regex``: substring search using a regular expression (case-insensitive)

    Any other operation results in a ``ValueError`` being raised.
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def eligible_rows(self, spec: Dict[str, Any]) -> pd.DataFrame:
        """Return the subset of rows matching the given include/exclude spec."""
        mask = self._build_mask(spec)
        return self.df[mask]

    def _build_mask(self, spec: Dict[str, Any]) -> pd.Series:
        include = spec.get("include") or []
        exclude = spec.get("exclude") or []
        mask = pd.Series([True] * len(self.df), index=self.df.index)

        for cond in include:
            mask &= self._cond_series(cond)
        for cond in exclude:
            mask &= ~self._cond_series(cond)
        return mask

    def _cond_series(self, cond: Dict[str, Any]) -> pd.Series:
        col, op = cond["col"], cond["op"].lower()
        val = cond.get("value")
        s = self.df[col]

        if op == "eq":
            return s.astype(str).str.strip().str.lower() == str(val).lower()
        if op == "in":
            vals = {str(v).lower() for v in cond.get("values", [])}
            return s.astype(str).str.lower().isin(vals)
        if op == "regex":
            import re
            return s.astype(str).str.contains(val, case=False, na=False)

        raise ValueError(f"Unsupported operator: {op}")


# ---------------------------------------------------------
# 4️⃣ DataFrameOps — unified entry point
# ---------------------------------------------------------
# Import the mixin-based implementation from the package and alias it here.
from .df_ops.dataframe_ops import DataFrameOps as _MixinDataFrameOps

# Alias the imported class to provide a single entry point when using this module.
DataFrameOps = _MixinDataFrameOps


# ---------------------------------------------------------
# ✅ Example usage (for manual testing)
# ---------------------------------------------------------
if __name__ == "__main__":
    # Example usage of the unified DataFrameOps.
    ops = DataFrameOps()
    # Create a DataFrame from a list of records
    df = ops.to_dataframe([
        {"Name": "Alice", "Age": 20},
        {"Name": "Bob", "Age": 21},
    ])
    # Normalize the column names using an alias mapping
    alias = {"name": {"Name"}}
    df = ops.normalize(df, alias)
    print(df)

    # Select rows where the name equals "Alice"
    spec = {"include": [{"col": "name", "op": "eq", "value": "Alice"}]}
    print(ops.select(df, spec))
