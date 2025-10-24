# -*- coding: utf-8 -*-
"""crawl_utils.presets
=======================

Preset 관리 모듈 V4.0

이 모듈은 URL + Provider 기반 정책 관리를 담당합니다.
- URL → (site, method, region) 분석
- (site, method) → 크롤링 정책 선택
- (region, provider) → WebDriver 정책 선택
"""

from typing import Dict, Any, Optional, Tuple

# URL 분석용 매핑 (presets/ 바로 아래)
from .domains import DOMAIN_MAPPING
from .methods import METHOD_PATTERNS

# Site별 크롤링 정책
from .sites import (
    ALIEXPRESS_DETAIL_POLICY,
    TAOBAO_DETAIL_POLICY,
)

# WebDriver region별 override
from .webdrivers import WEBDRIVER_OVERRIDES


class PresetManager:
    """Preset 관리 클래스 V4.0
    
    URL + Provider 기반 정책 관리:
    1. URL 분석 → (site, method, region) 추출
    2. (site, method) → 크롤링 정책 선택
    3. (region, provider) → WebDriver 정책 선택
    
    Example:
        >>> manager = PresetManager()
        >>> 
        >>> # URL 분석
        >>> site, method, region = manager.analyze_url("https://taobao.com/item/123.htm")
        >>> print(site, method, region)
        ('taobao', 'detail', 'china')
        >>> 
        >>> # 크롤링 정책 로드
        >>> crawl_policy = manager.get_crawl_policy(site, method)
        >>> 
        >>> # WebDriver 정책 로드
        >>> webdriver_policy = manager.get_webdriver_policy(region, "firefox")
    """
    
    def __init__(self):
        """PresetManager 초기화
        
        모든 preset 정책을 로드합니다.
        """
        # 도메인 매핑 (site → region)
        self.domain_mapping = DOMAIN_MAPPING
        
        # 메서드 패턴 (URL → method)
        self.method_patterns = METHOD_PATTERNS
        
        # 크롤링 정책 저장소 {(site, method): policy_dict}
        self.crawl_policies: Dict[Tuple[str, str], Dict[str, Any]] = {
            ("aliexpress", "detail"): ALIEXPRESS_DETAIL_POLICY,
            ("taobao", "detail"): TAOBAO_DETAIL_POLICY,
            # 추가 site/method 조합은 여기에 등록
            # ("tmall", "detail"): TMALL_DETAIL_POLICY,
            # ("1688", "detail"): SITE1688_DETAIL_POLICY,
            # ("aliexpress", "search"): ALIEXPRESS_SEARCH_POLICY,
        }
        
        # WebDriver 정책 저장소 {region: {provider: override_dict}}
        self.webdriver_overrides: Dict[str, Dict[str, Any]] = WEBDRIVER_OVERRIDES
    
    def analyze_url(self, url: str) -> Tuple[str, str, str]:
        """URL 분석 → (site, method, region)
        
        Args:
            url: 크롤링할 URL
        
        Returns:
            (site, method, region)
            - site: "aliexpress", "taobao" 등
            - method: "detail", "search" 등
            - region: "global", "china" 등
        
        Example:
            >>> manager = PresetManager()
            >>> site, method, region = manager.analyze_url("https://taobao.com/item/123.htm")
            >>> print(site, method, region)
            ('taobao', 'detail', 'china')
        """
        url_lower = url.lower()
        
        # 1. Site + Region 추출
        site = None
        region = None
        for site_name, config in self.domain_mapping.items():
            if any(domain in url_lower for domain in config["domains"]):
                site = site_name
                region = config["region"]
                break
        
        if not site or not region:
            raise ValueError(f"Cannot identify site/region from URL: {url}")
        
        # 2. Method 추출
        method = None
        for method_name, patterns in self.method_patterns.items():
            if any(pattern in url_lower for pattern in patterns):
                method = method_name
                break
        
        if not method:
            raise ValueError(f"Cannot identify method from URL: {url}")
        
        return site, method, region
    
    def get_crawl_policy(self, site: str, method: str) -> Optional[Dict[str, Any]]:
        """크롤링 정책 로드
        
        Args:
            site: Site identifier
            method: Method identifier
        
        Returns:
            Crawl policy dict or None
        
        Example:
            >>> manager = PresetManager()
            >>> policy = manager.get_crawl_policy("aliexpress", "detail")
            >>> print(policy["site"], policy["method"])
            ('aliexpress', 'detail')
        """
        return self.crawl_policies.get((site, method))
    
    def get_webdriver_override(
        self,
        region: str,
        provider: str
    ) -> Optional[Dict[str, Any]]:
        """WebDriver Override 로드
        
        Args:
            region: Region identifier ("global", "china", etc.)
            provider: Provider identifier ("firefox", "chrome", etc.)
        
        Returns:
            Provider-specific override dict or None
        
        Example:
            >>> manager = PresetManager()
            >>> override = manager.get_webdriver_override("china", "firefox")
            >>> print(override)
            {'profile_path': 'M:/Firefox_Profile/CRAWL_CHINA', 'accept_languages': '...'}
        """
        region_overrides = self.webdriver_overrides.get(region, {})
        return region_overrides.get(provider)
    
    def register_crawl_policy(
        self,
        site: str,
        method: str,
        policy: Dict[str, Any]
    ) -> None:
        """새로운 크롤링 정책 등록 (동적 확장)
        
        Args:
            site: Site identifier
            method: Method identifier
            policy: Crawl policy dict
        """
        self.crawl_policies[(site, method)] = policy
    
    def register_webdriver_override(
        self,
        region: str,
        override_dict: Dict[str, Any]
    ) -> None:
        """새로운 WebDriver Override 등록 (동적 확장)
        
        Args:
            region: Region identifier
            override_dict: Override dict with provider keys (firefox/chrome)
        """
        self.webdriver_overrides[region] = override_dict
    
    def list_crawl_policies(self) -> list[Tuple[str, str]]:
        """등록된 모든 크롤링 정책 목록
        
        Returns:
            List of (site, method) tuples
        """
        return list(self.crawl_policies.keys())
    
    def list_webdriver_regions(self) -> list[str]:
        """등록된 모든 WebDriver region 목록
        
        Returns:
            List of region identifiers
        """
        return list(self.webdriver_overrides.keys())
    
    def has_crawl_policy(self, site: str, method: str) -> bool:
        """크롤링 정책 존재 여부
        
        Args:
            site: Site identifier
            method: Method identifier
        
        Returns:
            True if policy exists
        """
        return (site, method) in self.crawl_policies
    
    def has_webdriver_override(self, region: str) -> bool:
        """WebDriver Override 존재 여부
        
        Args:
            region: Region identifier
        
        Returns:
            True if override exists
        """
        return region in self.webdriver_overrides


__all__ = [
    "PresetManager",
    "DOMAIN_MAPPING",
    "METHOD_PATTERNS",
    "ALIEXPRESS_DETAIL_POLICY",
    "TAOBAO_DETAIL_POLICY",
    "WEBDRIVER_OVERRIDES",
]

