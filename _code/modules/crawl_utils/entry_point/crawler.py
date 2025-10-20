# -*- coding: utf-8 -*-
"""Crawler - Crawling service entry point (XLOTO EntryPoint pattern).

책임:
1. ConfigLoader 기반 설정 로드 (config_loader_crawl.yaml)
2. Crawl Adapter 위임
3. LogManager 통합

XLOTO Pattern:
- EntryPoint: YAML 설정 로드 및 Adapter 위임
- Adapter(Crawl): 비즈니스 로직 (URL 분석, 메서드 브랜칭, 크롤링)

사용 예시:
```python
# 1. ConfigLoader로 설정 로드 (권장)
config = ConfigLoader(config_loader_cfg_path="configs/loader/config_loader_crawl.yaml")
crawl_config = config.to_dict(section="crawl")

# 2. Crawler EntryPoint 생성 및 실행
crawler = Crawler(crawl_config)
urls = ["https://aliexpress.com/item/123"]
results = crawler.run(urls)

# 또는 Crawl Adapter 직접 사용
from modules.crawl_utils.adapter import Crawl
crawl = Crawl(crawl_config)
results = crawl.run(urls)
```
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, Optional, Any, List, Dict

from logs_utils import LogManager
from cfg_utils import ConfigLoader

from ..core.policy import CrawlPolicy
from ..adapter.crawl import Crawl


class Crawler:
    """크롤링 EntryPoint - ConfigLoader 기반 크롤링 실행.
    
    XLOTO Pattern:
    - ConfigLoader로 설정 로드 (config_loader_crawl.yaml)
    - Crawl Adapter에 위임 (URL 분석, 메서드 브랜칭, 크롤링)
    
    Attributes:
        policy: CrawlPolicy 설정
        crawl: Crawl Adapter 인스턴스
    """
    
    def __init__(
        self,
        cfg_like: Union[Path, str, dict, CrawlPolicy, ConfigLoader, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize Crawler with ConfigLoader or CrawlPolicy.
        
        Args:
            cfg_like: ConfigLoader, CrawlPolicy, YAML 경로, dict, 또는 None
            log_manager: 외부 LogManager (선택사항)
            **overrides: 런타임 오버라이드 값 (wait__timeout, scroll__count 등)
        
        Example:
            >>> # ConfigLoader로 설정 로드 (권장)
            >>> config = ConfigLoader("configs/loader/config_loader_crawl.yaml")
            >>> crawl_config = config.to_dict(section="crawl")
            >>> crawler = Crawler(crawl_config)
            
            >>> # YAML 파일에서 직접 로드
            >>> crawler = Crawler("configs/crawl.yaml")
            
            >>> # dict로 직접 설정
            >>> crawler = Crawler({"site": "aliexpress", "source": {"method": "product_detail"}})
            
            >>> # 런타임 오버라이드
            >>> crawler = Crawler("config.yaml", wait__timeout=20)
        """
        # ConfigLoader 또는 CrawlPolicy 로드
        if isinstance(cfg_like, ConfigLoader):
            # ConfigLoader에서 crawl 섹션 추출
            crawl_config = cfg_like.to_dict(section="crawl")
            self._crawl = Crawl(cfg_like=crawl_config, log_manager=log_manager, **overrides)
        else:
            # CrawlPolicy 또는 dict로 직접 생성
            self._crawl = Crawl(cfg_like=cfg_like, log_manager=log_manager, **overrides)
    
    # ==========================================================================
    # Properties
    # ==========================================================================
    
    # ==========================================================================
    # Properties
    # ==========================================================================
    
    @property
    def crawl(self) -> Crawl:
        """Crawl Adapter 인스턴스.
        
        Returns:
            Crawl instance
        """
        return self._crawl
    
    @property
    def policy(self) -> CrawlPolicy:
        """CrawlPolicy (Crawl Adapter에서 위임).
        
        Returns:
            CrawlPolicy instance
        """
        return self._crawl.policy
    
    @property
    def log(self):
        """Logger (Crawl Adapter에서 위임).
        
        Returns:
            loguru logger
        """
        return self._crawl.log
    
    # ==========================================================================
    # Main Execution
    # ==========================================================================
    
    def run(
        self,
        urls: Optional[List[str]] = None,
        **runtime_context: Any
    ) -> List[Dict[str, Any]]:
        """Execute crawling and return extracted data.
        
        XLOTO Pattern:
        - URL 리스트를 받아 Crawl Adapter에 위임
        - Crawl이 URL 분석 및 메서드 브랜칭 수행
        
        Args:
            urls: 크롤링할 URL 리스트 (None이면 policy.source.urls 사용)
            **runtime_context: 런타임 컨텍스트 (cas_no 등)
        
        Returns:
            List of extracted data dictionaries
        
        Example:
            >>> # ConfigLoader로 설정 로드
            >>> config = ConfigLoader("config_loader_crawl.yaml")
            >>> crawl_config = config.to_dict(section="crawl")
            >>> 
            >>> # Crawler 생성 및 실행
            >>> crawler = Crawler(crawl_config)
            >>> urls = ["https://aliexpress.com/item/123"]
            >>> results = crawler.run(urls, cas_no="123-45-6")
            >>> print(results)
            [{"images": [...], "title": "..."}, ...]
        """
        self.log.info("=" * 70)
        self.log.info("[Crawler EntryPoint] Starting crawling")
        
        # Delegate to Crawl Adapter
        results = self._crawl.run(urls, **runtime_context)
        
        self.log.success(f"[Crawler EntryPoint] Completed: {len(results)} items extracted")
        self.log.info("=" * 70)
        
        return results
    
    # ==========================================================================
    # Resource Cleanup
    # ==========================================================================
    
    def close(self):
        """Crawl 종료 및 리소스 정리."""
        try:
            self._crawl.close()
            self.log.debug("Crawl closed")
        except Exception as e:
            self.log.warning(f"Error closing crawl: {e}")
    
    def __enter__(self):
        """Context manager 진입."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료."""
        self.close()
        return False
    
    def __del__(self):
        """Destructor - cleanup resources."""
        try:
            self.close()
        except Exception:
            pass
