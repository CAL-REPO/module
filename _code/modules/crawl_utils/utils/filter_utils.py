"""
크롤링 결과 필터링 Utilities

SRP: 검색 결과 필터링만 담당
- 수동 필터링 (UI)
- 가격 필터링
- 평점 필터링
- URL 파싱

Dependencies: None (순수 유틸리티)
"""

from pathlib import Path
from typing import List, Dict, Optional, Callable
import logging


logger = logging.getLogger(__name__)


def manual_filter_urls(search_output_dir: Path) -> List[str]:
    """
    수동 필터링: 검색 결과에서 원하는 상품 선택
    
    Args:
        search_output_dir: Step 1 출력 디렉토리
        
    Returns:
        선택된 URL 리스트
        
    Raises:
        FileNotFoundError: 디렉토리가 없는 경우
        ValueError: 잘못된 입력
        
    Example:
        >>> search_dir = Path("_output/taobao/search")
        >>> selected = manual_filter_urls(search_dir)
        >>> # 사용자 입력: "1,3,5"
        >>> print(selected)  # [url1, url3, url5]
    """
    if not search_output_dir.exists():
        raise FileNotFoundError(f"디렉토리 없음: {search_output_dir}")
    
    print(f"\n{'='*60}")
    print("🔍 수동 필터링 단계")
    print(f"{'='*60}\n")
    
    # 상품 정보 수집
    product_info = _collect_product_info(search_output_dir)
    
    if not product_info:
        logger.warning("상품 정보가 없습니다.")
        return []
    
    print(f"발견된 상품: {len(product_info)}개\n")
    
    # 상품 목록 출력
    _display_products(product_info)
    
    # 사용자 선택
    selected_urls = _prompt_selection(product_info)
    
    print(f"\n✅ {len(selected_urls)}개 상품 선택됨")
    return selected_urls


def filter_by_price(
    product_info: List[Dict],
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
) -> List[str]:
    """
    가격 범위로 필터링
    
    Args:
        product_info: 상품 정보 리스트
        min_price: 최소 가격
        max_price: 최대 가격
        
    Returns:
        필터링된 URL 리스트
        
    Example:
        >>> products = [{'url': '...', 'price': '¥399'}, ...]
        >>> filtered = filter_by_price(products, min_price=300, max_price=500)
    """
    filtered = []
    
    for product in product_info:
        try:
            # 가격 파싱 (¥399, $39.99 등)
            price_str = product.get('price', '')
            price = _parse_price(price_str)
            
            if price is None:
                continue
            
            # 범위 체크
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
            
            filtered.append(product['url'])
            
        except Exception as e:
            logger.debug(f"가격 파싱 실패: {e}")
            continue
    
    return filtered


def filter_by_rating(
    product_info: List[Dict],
    min_rating: float = 0.0
) -> List[str]:
    """
    평점으로 필터링
    
    Args:
        product_info: 상품 정보 리스트
        min_rating: 최소 평점
        
    Returns:
        필터링된 URL 리스트
    """
    filtered = []
    
    for product in product_info:
        try:
            rating_str = product.get('rating', '')
            rating = float(rating_str)
            
            if rating >= min_rating:
                filtered.append(product['url'])
                
        except (ValueError, TypeError):
            continue
    
    return filtered


def filter_by_custom(
    product_info: List[Dict],
    condition: Callable[[Dict], bool]
) -> List[str]:
    """
    커스텀 조건으로 필터링
    
    Args:
        product_info: 상품 정보 리스트
        condition: 필터 함수 (product -> bool)
        
    Returns:
        필터링된 URL 리스트
        
    Example:
        >>> # 제목에 "nike"가 있는 상품만
        >>> filtered = filter_by_custom(
        ...     products,
        ...     lambda p: "nike" in p['title'].lower()
        ... )
    """
    filtered = []
    
    for product in product_info:
        try:
            if condition(product):
                filtered.append(product['url'])
        except Exception as e:
            logger.debug(f"필터 조건 실패: {e}")
            continue
    
    return filtered


# ========== Private Functions ==========

def _collect_product_info(search_output_dir: Path) -> List[Dict]:
    """검색 결과에서 상품 정보 수집"""
    text_dir = search_output_dir / "text"
    
    if not text_dir.exists():
        return []
    
    url_files = sorted(text_dir.glob("*_url.txt"))
    product_info = []
    
    for url_file in url_files:
        # URL 읽기
        url = _read_file(url_file)
        if not url:
            continue
        
        # 상품명 읽기
        title_file = url_file.with_name(url_file.name.replace("_url.txt", "_title.txt"))
        title = _read_file(title_file) if title_file.exists() else ""
        
        # 가격 읽기
        price_file = url_file.with_name(url_file.name.replace("_url.txt", "_price.txt"))
        price = _read_file(price_file) if price_file.exists() else ""
        
        # 평점 읽기 (옵션)
        rating_file = url_file.with_name(url_file.name.replace("_url.txt", "_rating.txt"))
        rating = _read_file(rating_file) if rating_file.exists() else ""
        
        product_info.append({
            'url': url,
            'title': title,
            'price': price,
            'rating': rating
        })
    
    return product_info


def _display_products(product_info: List[Dict]):
    """상품 목록 출력"""
    for idx, product in enumerate(product_info, 1):
        title = product['title'][:50] if product['title'] else "(제목 없음)"
        price = product['price'] or "(가격 없음)"
        url = product['url'][:60] if product['url'] else ""
        
        print(f"{idx}. {title}")
        print(f"   가격: {price}")
        print(f"   URL: {url}...")
        print()


def _prompt_selection(product_info: List[Dict]) -> List[str]:
    """사용자 선택 입력"""
    print("크롤링할 상품 번호를 입력하세요 (예: 1,3,5 또는 1-5):")
    print("(Enter를 누르면 전체 선택)")
    
    selection = input("> ").strip()
    
    if not selection:
        # 전체 선택
        return [p['url'] for p in product_info]
    
    # 선택 파싱
    selected_indices = _parse_selection(selection)
    selected_urls = [
        product_info[i]['url']
        for i in selected_indices
        if 0 <= i < len(product_info)
    ]
    
    return selected_urls


def _parse_selection(selection: str) -> List[int]:
    """선택 문자열 파싱 (1,3,5 또는 1-5)"""
    indices = []
    
    for part in selection.split(','):
        part = part.strip()
        
        if '-' in part:
            # 범위 (1-5)
            try:
                start, end = map(int, part.split('-'))
                indices.extend(range(start - 1, end))  # 0-based index
            except ValueError:
                logger.warning(f"잘못된 범위: {part}")
                continue
        else:
            # 단일 (3)
            try:
                indices.append(int(part) - 1)  # 0-based index
            except ValueError:
                logger.warning(f"잘못된 번호: {part}")
                continue
    
    return indices


def _read_file(file_path: Path) -> str:
    """파일 내용 읽기"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        logger.debug(f"파일 읽기 실패 {file_path}: {e}")
        return ""


def _parse_price(price_str: str) -> Optional[float]:
    """
    가격 문자열 파싱
    
    Examples:
        "¥399" -> 399.0
        "$39.99" -> 39.99
        "1,299" -> 1299.0
    """
    if not price_str:
        return None
    
    # 통화 기호 제거
    clean = price_str.replace('¥', '').replace('$', '').replace('￥', '')
    # 쉼표 제거
    clean = clean.replace(',', '')
    # 공백 제거
    clean = clean.strip()
    
    try:
        return float(clean)
    except ValueError:
        return None
