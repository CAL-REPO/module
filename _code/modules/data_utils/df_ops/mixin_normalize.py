from .base import BaseDFMixin

class DataFrameNormalizeMixin(BaseDFMixin):
    """컬럼 정규화 및 alias 처리"""
    def normalize_columns(self, df, aliases: dict[str, str] | None = None):
        if aliases:
            df = df.rename(columns=aliases)
        return df
