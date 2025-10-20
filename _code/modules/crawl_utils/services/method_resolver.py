# -*- coding: utf-8 -*-
"""crawl_utils.services.method_resolver
========================================

Method Resolver - site + method로 ConfigLoader section 추출
"""

from __future__ import annotations

from typing import Dict, Any, Optional

try:
    from cfg_utils import ConfigLoader
except ImportError:
    ConfigLoader = None  # type: ignore


class MethodResolver:
    """Method Resolver - site + method로 적절한 crawl preset 추출
    
    ConfigLoader와 연동하여 site + method 조합으로
    적절한 section을 찾고 설정을 반환합니다.
    
    Section 이름 규칙: crawl__{site}__{method}
    - aliexpress + product_detail → crawl__aliexpress__detail
    - taobao + product_search → crawl__taobao__search
    
    Examples:
        >>> from cfg_utils import ConfigLoader
        >>> 
        >>> # ConfigLoader로 설정 로드
        >>> config = ConfigLoader("config_loader_crawl.yaml")
        >>> resolver = MethodResolver(config)
        >>> 
        >>> # Preset 추출
        >>> preset = resolver.resolve("aliexpress", "product_detail")
        >>> print(preset.get("wait", {}).get("timeout_sec"))
        25.0
    """
    
    def __init__(self, config: Optional["ConfigLoader"] = None):
        """
        Args:
            config: ConfigLoader 인스턴스 (선택사항)
                    None이면 section 이름만 생성 가능
        """
        self.config = config
    
    @staticmethod
    def get_section_name(site: str, method: str) -> str:
        """Site와 method로 config section 이름 생성
        
        Args:
            site: 사이트 이름 ("aliexpress", "taobao")
            method: 크롤링 메서드 ("product_detail", "product_search")
        
        Returns:
            Config section 이름
        
        Examples:
            >>> MethodResolver.get_section_name("aliexpress", "product_detail")
            'crawl__aliexpress__detail'
            
            >>> MethodResolver.get_section_name("taobao", "product_search")
            'crawl__taobao__search'
        """
        # method에서 "product_" 제거
        method_short = method.replace("product_", "")
        return f"crawl__{site}__{method_short}"
    
    def resolve(
        self,
        site: str,
        method: str,
        *,
        default_section: Optional[str] = None,
        raise_if_missing: bool = True
    ) -> Dict[str, Any]:
        """Site와 method로 crawl preset 추출
        
        Args:
            site: 사이트 이름 ("aliexpress", "taobao")
            method: 크롤링 메서드 ("product_detail", "product_search")
            default_section: Section이 없을 때 사용할 기본 section
            raise_if_missing: Section이 없을 때 raise 여부
        
        Returns:
            Crawl preset 설정 딕셔너리
        
        Raises:
            ValueError: ConfigLoader가 없을 때
            KeyError: Section이 없고 raise_if_missing=True일 때
        
        Examples:
            >>> config = ConfigLoader("config_loader_crawl.yaml")
            >>> resolver = MethodResolver(config)
            >>> 
            >>> # Preset 추출
            >>> preset = resolver.resolve("aliexpress", "product_detail")
            >>> 
            >>> # 기본값 사용
            >>> preset = resolver.resolve("unknown", "unknown",
            ...                          default_section="crawl__aliexpress__detail")
        """
        if self.config is None:
            raise ValueError("ConfigLoader is required for resolve()")
        
        # 1. Section 이름 생성
        section_name = self.get_section_name(site, method)
        
        # 2. Section 존재 확인
        if not self.has_section(section_name):
            if default_section:
                section_name = default_section
            elif raise_if_missing:
                available = self.list_sections()
                raise KeyError(
                    f"Section '{section_name}' not found in ConfigLoader. "
                    f"site='{site}', method='{method}'. "
                    f"Available sections: {available}"
                )
            else:
                return {}
        
        # 3. Section 추출
        preset = self.config.to_dict(section=section_name)
        
        if not preset and raise_if_missing:
            raise KeyError(f"Section '{section_name}' is empty")
        
        return preset
    
    def has_section(self, section_name: str) -> bool:
        """Section이 ConfigLoader에 존재하는지 확인
        
        Args:
            section_name: 확인할 section 이름
        
        Returns:
            존재하면 True
        """
        if self.config is None:
            return False
        
        # ConfigLoader에서 section 추출 시도
        try:
            result = self.config.to_dict(section=section_name)
            return bool(result)
        except (KeyError, AttributeError):
            return False
    
    def list_sections(self) -> list[str]:
        """ConfigLoader에서 사용 가능한 모든 section 목록 반환
        
        Returns:
            Section 이름 리스트
        """
        if self.config is None:
            return []
        
        # ConfigLoader의 section 목록 추출
        if hasattr(self.config, '_merged_data'):
            return list(self.config._merged_data.keys())
        
        return []
