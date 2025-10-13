from typing import Optional
import pandas as pd

class DataFramePolicy:
    """DataFrame 처리 정책 정의"""
    def __init__(self, allow_empty: bool = False):
        self.allow_empty = allow_empty

class BaseDFMixin:
    """모든 Mixin의 기본 부모"""
    def __init__(self, policy: Optional[DataFramePolicy] = None):
        self.policy = policy or DataFramePolicy()
