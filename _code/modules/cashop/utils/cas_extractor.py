# -*- coding: utf-8 -*-
"""CAS No 추출 Service (FilterMixin + ColumnResolver)

Architecture:
    - ColumnResolver로 컬럼명 해석 (aliases 지원)
    - FilterMixin으로 조건 필터링
    - 셀 위치 추출 (translation_row, translation_col)

Example:
    >>> from cashop.utils import CasExtractor
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
        3. 셀 위치 추출 (cas_row, cas_col)
    
    Filter Conditions (extract 메서드 인자로 제어):
        - cas_key: CAS 컬럼 (필수)
        - download_key + download_must_be_empty:
            * True: download.isna() - 비어있을 때만
            * False: download.notna() - 채워져있을 때만
            * None: 조건 없음
        - translation_key + translation_must_be_empty:
            * True: translation.isna() - 비어있을 때만
            * False: translation.notna() - 채워져있을 때만
            * None: 조건 없음
    
    Example:
        >>> # xlcrawl: download가 비어있을 때만
        >>> extractor = CasExtractor()
        >>> cas_list = extractor.extract(
        ...     df, ws.column_resolver,
        ...     cas_key="cas",
        ...     download_key="download",
        ...     download_must_be_empty=True
        ... )
        >>> 
        >>> # xloto: download가 채워져있고 translation이 비어있을 때
        >>> cas_list = extractor.extract(
        ...     df, ws.column_resolver,
        ...     cas_key="cas",
        ...     download_key="download",
        ...     download_must_be_empty=False,
        ...     translation_key="translation",
        ...     translation_must_be_empty=True
        ... )
        >>> 
        >>> print(cas_list[0])
        {
            "cas_no": "123-45-6",
            "cas_row": 2,
            "cas_col": "B",
            "download_col": "K",
            "translation_col": "L",
            "download_value": "2025-01-01"
        }
    """
    
    def __init__(self):
        """Initialize CasExtractor
        
        Note:
            필터 조건은 extract() 메서드의 인자로 전달
        """
        self.df_filter = FilterMixin()
    
    def extract(
        self,
        df: pd.DataFrame,
        column_resolver: ColumnResolver,
        *,
        cas_key: Optional[str] = None,
        download_key: Optional[str] = None,
        download_must_be_empty: Optional[bool] = None,
        translation_key: Optional[str] = None,
        translation_must_be_empty: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """DataFrame에서 CAS No 추출
        
        Args:
            df: DataFrame
            column_resolver: XwWs.column_resolver (preset 기반)
            cas_key: CAS 컬럼 alias key (Required)
            download_key: Download 컬럼 alias key (Optional)
            download_must_be_empty: True=isna(), False=notna(), None=조건 없음
            translation_key: Translation 컬럼 alias key (Optional)
            translation_must_be_empty: True=isna(), False=notna(), None=조건 없음
        
        Returns:
            List of {
                "cas_no": str,
                "cas_row": int,
                "cas_col": str,
                "download_col": Optional[str],
                "translation_col": Optional[str],
                "download_value": Optional[Any]
            }
        
        Example:
            >>> # xlcrawl: download가 비어있을 때만
            >>> extractor.extract(df, resolver, cas_key="cas", 
            ...                   download_key="download", download_must_be_empty=True)
            
            >>> # xloto: download가 채워져있고 translation이 비어있을 때
            >>> extractor.extract(df, resolver, cas_key="cas",
            ...                   download_key="download", download_must_be_empty=False,
            ...                   translation_key="translation", translation_must_be_empty=True)
        
        Raises:
            ValueError: CAS 컬럼 미발견
        """
        # ========================================
        # Resolve column names (preset 기반)
        # ========================================
        cas_col = column_resolver.resolve(df, cas_key) if cas_key else None
        download_col = column_resolver.resolve(df, download_key) if download_key else None
        translation_col = column_resolver.resolve(df, translation_key) if translation_key else None
        
        # CAS 컬럼 존재 여부 확인
        if not cas_col:
            if cas_key:
                raise ValueError(f"CAS column not found for key '{cas_key}'")
            else:
                raise ValueError("cas_key is required but not provided")
        
        # ========================================
        # Build filter condition
        # ========================================
        filter_conditions = [f"`{cas_col}`.notna()"]
        
        # Download 조건
        if download_col and download_must_be_empty is not None:
            if download_must_be_empty:
                filter_conditions.append(f"`{download_col}`.isna()")
            else:
                filter_conditions.append(f"`{download_col}`.notna()")
        
        # Translation 조건
        if translation_col and translation_must_be_empty is not None:
            if translation_must_be_empty:
                filter_conditions.append(f"`{translation_col}`.isna()")
            else:
                filter_conditions.append(f"`{translation_col}`.notna()")
        
        query_str = " & ".join(filter_conditions)
        
        # ========================================
        # Extract CAS positions
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
                "cas_row": row_idx + 2,  # Excel row (1-based + header)
                "cas_col": cas_col,
                "download_col": download_col,
                "translation_col": translation_col
            }
            
            # Download value 추가 (선택)
            if download_col and row_idx < len(filtered_df):
                download_value = filtered_df.iloc[row_idx].get(download_col)
                cas_item["download_value"] = download_value
            
            cas_list.append(cas_item)
        
        return cas_list
