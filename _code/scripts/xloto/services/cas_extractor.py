# -*- coding: utf-8 -*-
"""CAS No Extractor Service.

DataFrame에서 CAS No 추출 및 필터링 로직 분리.

책임:
1. DataFrame 컬럼명 해석 (aliases 매핑)
2. 날짜 필터링 로직 (download=날짜, translation≠날짜)
3. CAS No 리스트 추출 (Excel 셀 정보 포함)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd


class CasExtractor:
    """CAS No 추출 서비스.
    
    DataFrame 필터링 및 CAS No 추출 로직을 담당합니다.
    
    Attributes:
        aliases: 컬럼 별칭 매핑 (excel config의 aliases)
        cas_column: CAS No 컬럼 키
        download_column: 다운로드 날짜 컬럼 키
        translation_column: 번역 날짜 컬럼 키
    
    Example:
        >>> extractor = CasExtractor(
        ...     aliases=excel_config.get("aliases", {}),
        ...     cas_column="cas",
        ...     download_column="download",
        ...     translation_column="translation"
        ... )
        >>> cas_list = extractor.extract(df)
    """
    
    def __init__(
        self,
        aliases: Dict[str, List[str]],
        cas_column: str = "cas",
        download_column: str = "download",
        translation_column: str = "translation"
    ):
        """Initialize CasExtractor.
        
        Args:
            aliases: 컬럼 별칭 딕셔너리 {key: [alias1, alias2, ...]}
            cas_column: CAS No 컬럼 키
            download_column: 다운로드 날짜 컬럼 키
            translation_column: 번역 날짜 컬럼 키
        """
        self.aliases = aliases
        self.cas_column = cas_column
        self.download_column = download_column
        self.translation_column = translation_column
    
    def extract(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """DataFrame에서 CAS No 추출 (필터링).
        
        필터링 조건:
        - download 컬럼: 날짜 값이 있음
        - translation 컬럼: 날짜 값이 없음
        
        Args:
            df: pandas DataFrame
        
        Returns:
            List of {
                "cas_no": str,
                "translation_row": int (Excel 1-based),
                "translation_col": str (컬럼명)
            }
        
        Raises:
            ValueError: 필수 컬럼을 찾을 수 없는 경우
        """
        # 컬럼명 해석
        cas_col = self._resolve_column(df, self.cas_column)
        download_col = self._resolve_column(df, self.download_column)
        translation_col = self._resolve_column(df, self.translation_column)
        
        if not all([cas_col, download_col, translation_col]):
            raise ValueError(
                f"Required columns not found: "
                f"cas={cas_col}, download={download_col}, translation={translation_col}"
            )
        
        # 필터링: download=날짜, translation≠날짜
        target_df = df[
            (pd.to_datetime(df[download_col], errors='coerce').notna()) &
            (pd.to_datetime(df[translation_col], errors='coerce').isna())
        ].copy()
        
        # CAS No + 셀 정보 추출
        result = []
        for idx, row in target_df.iterrows():
            result.append({
                "cas_no": str(row[cas_col]),
                "translation_row": int(idx) + 2,  # Excel is 1-based, +1 for header
                "translation_col": translation_col,
            })
        
        return result
    
    def _resolve_column(
        self,
        df: pd.DataFrame,
        key: str
    ) -> Optional[str]:
        """컬럼 별칭 → 실제 컬럼명 매핑.
        
        Args:
            df: DataFrame
            key: 컬럼 키 (예: "cas", "download")
        
        Returns:
            실제 컬럼명, 없으면 None
        """
        alias_list = self.aliases.get(key, [])
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if col_lower in [a.lower().strip() for a in alias_list]:
                return col
        return None
    
    def get_resolved_columns(self, df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """모든 컬럼 해석 결과 반환 (디버깅용).
        
        Returns:
            {
                "cas": "실제컬럼명",
                "download": "실제컬럼명",
                "translation": "실제컬럼명"
            }
        """
        return {
            "cas": self._resolve_column(df, self.cas_column),
            "download": self._resolve_column(df, self.download_column),
            "translation": self._resolve_column(df, self.translation_column),
        }


__all__ = ["CasExtractor"]
