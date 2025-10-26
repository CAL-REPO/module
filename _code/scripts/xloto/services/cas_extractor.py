# -*- coding: utf-8 -*-
"""CAS No 추출 Service (FilterMixin + ColumnResolver)

Architecture:
    - ColumnResolver로 컬럼명 해석 (aliases 지원)
    - FilterMixin으로 조건 필터링
    - 셀 위치 추출 (translation_row, translation_col)

Example:
    >>> extractor = CasExtractor(aliases={"cas": ["CAS No", "CAS Number"]})
    >>> cas_list = extractor.extract(df)
    >>> # [{"cas_no": "123-45-6", "translation_row": 2, "translation_col": "F"}]
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
import pandas as pd

from structured_data import FilterMixin
from xl_utils.services.column_resolver import ColumnResolver


class CasExtractor:
    """DataFrame에서 CAS No 추출 (ws.column_resolver 사용)
    
    Responsibilities:
        1. XwWs.column_resolver로 컬럼명 해석 (preset 기반)
        2. FilterMixin으로 조건 필터링
        3. 셀 위치 추출 (translation_row, translation_col)
    
    Filter Conditions:
        - CAS column is not null (필수)
        - Download column is not null (선택)
        - Translation column is null (선택)
    
    ⚠️ translation_row/translation_col을 extract 단계에서 저장하는 이유:
        - filter 조건에 맞지 않는 row가 제거되므로
        - 나중에 Excel 업데이트 시 원본 DataFrame에서 다시 찾는 것은 메모리 낭비
    
    Example:
        >>> extractor = CasExtractor(
        ...     include_download=True,
        ...     include_translation=True
        ... )
        >>> 
        >>> # ws.column_resolver는 xl_utils.presets 기반
        >>> cas_list = extractor.extract(df, ws.column_resolver)
        >>> print(cas_list[0])
        {
            "cas_no": "123-45-6",
            "translation_row": 2,
            "translation_col": "F",
            "download_value": "2025-01-01"
        }
    """
    
    def __init__(
        self,
        *,
        include_download: bool = True,
        include_translation: bool = True
    ):
        """Initialize CasExtractor
        
        Args:
            include_download: Download 컬럼 조건 포함 여부
            include_translation: Translation 컬럼 조건 포함 여부
        
        Note:
            ColumnResolver는 XwWs에서 전달받음 (preset 기반)
        """
        self.df_filter = FilterMixin()
        self.include_download = include_download
        self.include_translation = include_translation
    
    def extract(
        self,
        df: pd.DataFrame,
        column_resolver: ColumnResolver,
        *,
        cas_key: str = "cas",
        download_key: str = "download",
        translation_key: str = "translation"
    ) -> List[Dict[str, Any]]:
        """DataFrame에서 CAS No 추출
        
        Args:
            df: DataFrame
            column_resolver: XwWs.column_resolver (preset 기반)
            cas_key: CAS 컬럼 alias key (preset의 키)
            download_key: Download 컬럼 alias key
            translation_key: Translation 컬럼 alias key
        
        Returns:
            List of {
                "cas_no": str,
                "translation_row": int,     # Excel row (1-based + header)
                "translation_col": str,     # Excel column name
                "download_value": Optional[Any]
            }
        
        Raises:
            ValueError: CAS 컬럼 미발견
        """
        # ========================================
        # Resolve column names (preset 기반)
        # ========================================
        cas_col = column_resolver.resolve(df, cas_key)
        download_col = column_resolver.resolve(df, download_key) if self.include_download else None
        translation_col = column_resolver.resolve(df, translation_key) if self.include_translation else None
        
        if not cas_col:
            raise ValueError(f"CAS column not found for key '{cas_key}'")
        
        # ========================================
        # Build filter condition
        # ========================================
        filter_conditions = [f"`{cas_col}`.notna()"]
        
        if download_col:
            filter_conditions.append(f"`{download_col}`.notna()")
        
        if translation_col:
            filter_conditions.append(f"`{translation_col}`.isna()")
        
        query_str = " & ".join(filter_conditions)
        
        # ========================================
        # Extract CAS positions (⚠️ 여기서 translation_row/col 저장)
        # ========================================
        filtered_df, positions, values = self.df_filter.filter_df_with_cell_positions(
            df=df,
            condition=query_str,
            column=cas_col
        )
        
        # ========================================
        # Build result list
        # ========================================
        cas_list = []
        
        for (row_idx, col_idx), cas_value in zip(positions, values):
            cas_item = {
                "cas_no": str(cas_value).strip(),
                "translation_row": row_idx + 2,  # Excel row (1-based + header)
                "translation_col": translation_col if translation_col else None
            }
            
            # Download value 추가 (선택)
            if download_col and row_idx < len(filtered_df):
                download_value = filtered_df.iloc[row_idx].get(download_col)
                cas_item["download_value"] = download_value
            
            cas_list.append(cas_item)
        
        return cas_list