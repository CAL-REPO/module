# -*- coding: utf-8 -*-
# data_utils/df_ops.py (리팩토링 버전)
# pandas 중심 DataFrame 정책 및 조작 클래스 구조화

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, List, Set
import pandas as pd


# ---------------------------------------------------------
# 1️⃣ 정책 정의 (Pydantic 아님: 내부 전용용 간단 dataclass)
# ---------------------------------------------------------
@dataclass
class DataFramePolicy:
    normalize_columns: bool = True
    drop_empty_rows: bool = True
    drop_empty_cols: bool = True
    warn_on_duplicate_cols: bool = True
    default_aliases: Dict[str, Set[str]] = field(default_factory=dict)


# ---------------------------------------------------------
# 2️⃣ 컬럼 정규화기
# ---------------------------------------------------------
class DataFrameNormalizer:
    def __init__(self, alias_map: Optional[Dict[str, Set[str]]] = None):
        self.alias_map = alias_map or {}

    @staticmethod
    def _norm_col(name: Any) -> str:
        s = str(name or "").strip().lower()
        return " ".join(s.split())

    def normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        reverse_map = {
            alias.lower().strip(): key
            for key, aliases in self.alias_map.items()
            for alias in aliases
        }
        mapper = {col: reverse_map.get(self._norm_col(col), col) for col in df.columns}
        df2 = df.rename(columns=mapper)
        if df2.columns.duplicated().any():
            dupes = df2.columns[df2.columns.duplicated()].tolist()
            print(f"[경고] 정규화 후 중복 컬럼 발견: {dupes}")
        return df2


# ---------------------------------------------------------
# 3️⃣ 조건/필터링 로직
# ---------------------------------------------------------
class DataFrameSelector:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def eligible_rows(self, spec: Dict[str, Any]) -> pd.DataFrame:
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

        raise ValueError(f"지원하지 않는 연산자: {op}")


# ---------------------------------------------------------
# 4️⃣ DataFrameOps — 통합 진입점
# ---------------------------------------------------------
class DataFrameOps:
    def __init__(self, policy: Optional[DataFramePolicy] = None):
        self.policy = policy or DataFramePolicy()

    # --- 생성 ---
    def to_dataframe(self, records: Iterable[dict] | None, columns: Optional[List[str]] = None) -> pd.DataFrame:
        if not records:
            return pd.DataFrame(columns=columns or [])
        df = pd.DataFrame.from_records(list(records))
        if columns:
            for c in columns:
                if c not in df.columns:
                    df[c] = None
            df = df[columns]
        return df

    # --- 정규화 ---
    def normalize(self, df: pd.DataFrame, aliases: Optional[Dict[str, Set[str]]] = None) -> pd.DataFrame:
        if not self.policy.normalize_columns:
            return df
        norm = DataFrameNormalizer(aliases or self.policy.default_aliases)
        return norm.normalize_columns(df)

    # --- 필터 ---
    def select(self, df: pd.DataFrame, spec: Dict[str, Any]) -> pd.DataFrame:
        return DataFrameSelector(df).eligible_rows(spec)

    # --- 업데이트 ---
    def update(self, df: pd.DataFrame, where: Dict[str, Any], set: Dict[str, Any]) -> pd.DataFrame:
        if not set:
            raise ValueError("update() requires non-empty set dict.")
        mask = DataFrameSelector(df)._build_mask(where)
        out = df.copy()
        for col, val in set.items():
            if col not in out.columns:
                out[col] = None
            out.loc[mask, col] = val
        return out

    # --- Drop 처리 ---
    def drop_empty(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.policy.drop_empty_rows:
            df = df.dropna(how="all")
        if self.policy.drop_empty_cols:
            df = df.dropna(axis=1, how="all")
        return df


# ---------------------------------------------------------
# ✅ 사용 예시 (예: 테스트용)
# ---------------------------------------------------------
if __name__ == "__main__":
    ops = DataFrameOps()
    df = ops.to_dataframe([{"Name": "홍길동", "Age": 20}, {"Name": "이몽룡", "Age": 21}])
    alias = {"name": {"이름", "Name"}}
    df = ops.normalize(df, alias)
    print(df)

    spec = {"include": [{"col": "name", "op": "eq", "value": "홍길동"}]}
    print(ops.select(df, spec))
