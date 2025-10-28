# -*- coding: utf-8 -*-
"""Excel 업데이트 Service

Architecture:
    - CAS 처리 결과 기반 Excel 셀 업데이트
    - 날짜 값 쓰기
    - 업데이트 카운트 반환

Example:
    >>> from cashop.utils import ExcelUpdater
    >>> updater = ExcelUpdater()
    >>> updated_count = updater.update(
    ...     worksheet=ws,
    ...     cas_results=[{
    ...         "cas_no": "123-45-6",
    ...         "success": True,
    ...         "processed_count": 3,
    ...         "translation_row": 2,
    ...         "translation_col": "F"
    ...     }],
    ...     date_value="2025-01-25"
    ... )
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import pandas as pd

from xl_utils.services.xw_ws import XwWs


class ExcelUpdater:
    """Excel 업데이트 Service
    
    Responsibilities:
        1. CAS 결과 기반 Excel 셀 업데이트
        2. 날짜 값 쓰기
        3. 업데이트 카운트 반환
    
    Example:
        >>> updater = ExcelUpdater()
        >>> updated_count = updater.update(
        ...     worksheet=ws,
        ...     cas_results=[{
        ...         "cas_no": "123-45-6",
        ...         "success": True,
        ...         "processed_count": 3,
        ...         "translation_row": 2,
        ...         "translation_col": "F"
        ...     }],
        ...     date_value="2025-01-25"
        ... )
        >>> print(updated_count)  # 1
    """
    
    def __init__(self):
        """Initialize ExcelUpdater"""
        pass
    
    def update(
        self,
        worksheet: XwWs,
        cas_results: List[Dict[str, Any]],
        date_value: Optional[Union[str, datetime]] = None
    ) -> int:
        """Excel 셀 업데이트
        
        Args:
            worksheet: XwWs 인스턴스
            cas_results: CAS 처리 결과 리스트
                [{
                    "cas_no": str,
                    "success": bool,
                    "processed_count": int,
                    "translation_row": int,
                    "translation_col": str
                }]
            date_value: 쓸 날짜 값 (None이면 현재 날짜)
        
        Returns:
            업데이트된 셀 수
        
        Example:
            >>> cas_results = [
            ...     {"cas_no": "123-45-6", "success": True, "processed_count": 3, "translation_row": 2, "translation_col": "F"},
            ...     {"cas_no": "789-01-2", "success": True, "processed_count": 0, "translation_row": 3, "translation_col": "F"}
            ... ]
            >>> updated = updater.update(ws, cas_results)
            >>> print(updated)  # 1 (processed_count > 0만 업데이트)
        """
        # ========================================
        # Date value 준비
        # ========================================
        if date_value is None:
            date_value = datetime.now().strftime("%Y-%m-%d")
        elif isinstance(date_value, datetime):
            date_value = date_value.strftime("%Y-%m-%d")
        
        # ========================================
        # Filter successful CAS with processed images or skipped
        # ========================================
        # ✅ success=True AND (processed_count > 0 OR skipped=True)
        # ✅ skipped=True: 파일이 이미 존재하여 크롤링 건너뛴 경우
        successful_cas = [
            r for r in cas_results
            if r.get("success") and (r.get("processed_count", 0) > 0 or r.get("skipped", False))
        ]
        
        if not successful_cas:
            return 0
        
        # ========================================
        # Get DataFrame for column mapping
        # ========================================
        df = worksheet.to_dataframe(anchor="A1", header=True, index=False)
        
        # ========================================
        # Update cells
        # ========================================
        updated_count = 0
        
        for cas_item in successful_cas:
            row = cas_item.get("translation_row")
            col = cas_item.get("translation_col")
            
            if not row or not col:
                continue
            
            try:
                # Convert column name to index
                col_idx = df.columns.get_loc(col)
                
                if isinstance(col_idx, int):
                    col_idx += 1  # Excel column (1-based)
                else:
                    # slice or MultiIndex - fallback to 1
                    col_idx = 1
                
                # ========================================
                # Skip 시: 빈 칸만 날짜 기입, 이미 날짜 있으면 유지
                # 일반 처리: 무조건 날짜 업데이트
                # ========================================
                if cas_item.get("skipped", False):
                    # Skip된 경우: 셀이 비어있을 때만 날짜 기입
                    current_value = worksheet.cell_ops.read((row, col_idx))
                    if current_value is None or str(current_value).strip() == "":
                        worksheet.cell_ops.write(row, col_idx, date_value)
                        updated_count += 1
                    # 이미 날짜가 있으면 업데이트 안함
                else:
                    # 일반 처리된 경우: 무조건 날짜 업데이트
                    worksheet.cell_ops.write(row, col_idx, date_value)
                    updated_count += 1
            
            except (KeyError, ValueError) as e:
                # Column not found - skip
                continue
        
        return updated_count
