# -*- coding: utf-8 -*-
"""crawl_utils.services.url_analyzer
====================================

URL 분석 서비스 - URL에서 site, method 정보 추출 (Config 기반)
"""

from __future__ import annotations

from typing import Tuple, Optional, Dict, List
from urllib.parse import urlparse


class UrlAnalyzer:
    """URL 분석기 - URL에서 site와 method 추출 (Config 기반)
    
    설정 파일에서 site_domains와 method_patterns를 로드하여 사용합니다.
    
    Config 구조:
        url_patterns:
          site_domains:
            aliexpress: ["aliexpress.com", "aliexpress.us"]
            taobao: ["taobao.com", "world.taobao.com"]
          
          method_patterns:
            product_detail: ["/item/", "item.htm"]
            product_search: ["/wholesale", "/search"]
    
    Examples:
        >>> # ConfigLoader로 설정 로드
        >>> config = ConfigLoader("config_loader_crawl.yaml")
        >>> url_patterns = config.to_dict(section="url_patterns")
        >>> 
        >>> # UrlAnalyzer 생성
        >>> analyzer = UrlAnalyzer(url_patterns)
        >>> 
        >>> # URL 분석
        >>> site, method = analyzer.analyze("https://www.aliexpress.com/item/123.html")
        >>> print(site, method)
        aliexpress product_detail
    """
    
    def __init__(self, url_patterns: Optional[Dict[str, Dict[str, List[str]]]] = None):
        """
        Args:
            url_patterns: URL 패턴 설정 딕셔너리
                {
                    "site_domains": {"aliexpress": [...], "taobao": [...]},
                    "method_patterns": {"product_detail": [...], "product_search": [...]}
                }
                None이면 빈 딕셔너리 사용 (모든 URL은 unknown으로 처리)
        """
        if url_patterns is None:
            url_patterns = {"site_domains": {}, "method_patterns": {}}
        
        self.site_domains: Dict[str, List[str]] = url_patterns.get("site_domains", {})
        self.method_patterns: Dict[str, List[str]] = url_patterns.get("method_patterns", {})
    
    def analyze(self, url: str) -> Tuple[str, str]:
        """URL 분석하여 site와 method 추출
        
        Args:
            url: 분석할 URL
        
        Returns:
            (site, method) 튜플
            - site: "aliexpress", "taobao", "unknown"
            - method: "product_detail", "product_search", "unknown"
        
        Examples:
            >>> analyzer = UrlAnalyzer()
            
            >>> # AliExpress 상품 상세
            >>> analyzer.analyze("https://www.aliexpress.com/item/123.html")
            ('aliexpress', 'product_detail')
            
            >>> # Taobao 검색
            >>> analyzer.analyze("https://s.taobao.com/search?q=nike")
            ('taobao', 'product_search')
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        
        # 1. Site 추출
        site = self._extract_site(domain)
        
        # 2. Method 추출
        method = self._extract_method(path, url)
        
        return site, method
    
    def _extract_site(self, domain: str) -> str:
        """도메인에서 site 추출
        
        Args:
            domain: URL 도메인 (netloc)
        
        Returns:
            site 이름 ("aliexpress", "taobao", "unknown")
        """
        for site, domains in self.site_domains.items():
            if any(d in domain for d in domains):
                return site
        return "unknown"
    
    def _extract_method(self, path: str, full_url: str) -> str:
        """경로에서 method 추출
        
        Args:
            path: URL 경로
            full_url: 전체 URL (쿼리 파라미터 확인용)
        
        Returns:
            method 이름 ("product_detail", "product_search", "unknown")
        """
        # product_detail 패턴 확인
        detail_patterns = self.method_patterns.get("product_detail", [])
        for pattern in detail_patterns:
            if pattern in path or pattern in full_url:
                return "product_detail"
        
        # product_search 패턴 확인
        search_patterns = self.method_patterns.get("product_search", [])
        for pattern in search_patterns:
            if pattern in path or pattern in full_url:
                return "product_search"
        
        # 기본값: detail (대부분의 URL은 상품 상세)
        return "product_detail"
    
    def is_valid_url(self, url: str) -> bool:
        """URL이 유효한 크롤링 대상인지 확인
        
        Args:
            url: 검증할 URL
        
        Returns:
            유효한 URL이면 True
        """
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            site = self._extract_site(parsed.netloc.lower())
            return site != "unknown"
        except Exception:
            return False
