# -*- coding: utf-8 -*-
"""Column Alias Presets for xl_utils.

컬럼명 별칭(alias) 매핑을 사전 정의한 preset 모음.
Excel 파일의 다양한 컬럼명을 표준 키로 통일합니다.

Usage:
    >>> from xl_utils.presets import get_preset
    >>> 
    >>> aliases = get_preset("PRODUCT_LIST")
    >>> # aliases = {"date": ["date", "날짜"], "cas": ["cas", "cas no", ...], ...}
"""

from typing import Dict, List


# ============================================================================
# PRODUCT_LIST Preset - 제품 리스트 Excel 표준
# ============================================================================
PRODUCT_LIST = {
    "date": [
        "date",
        "날짜",
        "일자",
        "작성일",
    ],
    
    "cas": [
        "cas",
        "cas no",
        "casno",
        "cas no.",
        "cas 번호",
        "상품코드",
        "제품코드",
    ],
    
    "shop": [
        "shop",
        "store",
        "스토어",
        "마켓",
        "쇼핑몰",
        "판매처",
    ],
    
    "product_no": [
        "product no",
        "productno",
        "product_no",
        "제품번호",
        "상품번호",
        "pn",
        "sku",
        "품번",
    ],
    
    "product_brand": [
        "product brand",
        "brand",
        "브랜드",
        "제조사",
        "manufacturer",
    ],
    
    "product_type": [
        "product type",
        "type",
        "타입",
        "유형",
        "종류",
        "분류",
    ],
    
    "category": [
        "category",
        "카테고리",
        "범주",
    ],
    
    "price_yuan": [
        "price(yuan)",
        "price yuan",
        "price_yuan",
        "rmb",
        "price_rmb",
        "위안",
        "중국위안",
        "yuan",
    ],
    
    "price_dollar": [
        "price(dollar)",
        "price dollar",
        "price_dollar",
        "price usd",
        "price_usd",
        "usd",
        "달러",
        "dollar",
    ],
    
    "price_won": [
        "price(won)",
        "price won",
        "price_won",
        "krw",
        "원",
        "가격(원)",
        "가격",
        "price",
    ],
    
    "download": [
        "download",
        "다운로드",
        "받기",
        "dl",
    ],
    
    "translation": [
        "translation",
        "번역",
        "translate",
        "trans",
    ],
    
    "removed": [
        "removed",
        "삭제대상",
        "삭제",
        "제거",
        "delete",
    ],
    
    "final": [
        "final",
        "최종",
        "완료",
        "done",
    ],
    
    "url": [
        "url",
        "link",
        "링크",
        "주소",
        "address",
        "href",
    ],
}


# ============================================================================
# Preset Registry
# ============================================================================
PRESETS: Dict[str, Dict[str, List[str]]] = {
    "PRODUCT_LIST": PRODUCT_LIST,
}


# ============================================================================
# Helper Functions
# ============================================================================
def get_preset(name: str) -> Dict[str, List[str]]:
    """Get column alias preset by name.
    
    Args:
        name: Preset name (e.g., "PRODUCT_LIST")
    
    Returns:
        Column alias dictionary {key: [alias1, alias2, ...]}
    
    Raises:
        KeyError: If preset name not found
    
    Example:
        >>> aliases = get_preset("PRODUCT_LIST")
        >>> print(aliases["cas"])
        ['cas', 'cas no', 'casno', 'cas no.', 'cas 번호', '상품코드', '제품코드']
    """
    if name not in PRESETS:
        raise KeyError(
            f"Preset '{name}' not found. Available presets: {list(PRESETS.keys())}"
        )
    
    return PRESETS[name].copy()


def list_presets() -> List[str]:
    """List all available preset names.
    
    Returns:
        List of preset names
    
    Example:
        >>> presets = list_presets()
        >>> print(presets)
        ['PRODUCT_LIST']
    """
    return list(PRESETS.keys())


__all__ = [
    "PRESETS",
    "PRODUCT_LIST",
    "get_preset",
    "list_presets",
]
