# -*- coding: utf-8 -*-
"""Crawler - Crawling service entry point (OTO Pattern)

책임:
1. ConfigLoader 기반 설정 로드
2. SyncCrawl Adapter 위임

사용 예시 (OTO 패턴):
```python
from cfg_utils import ConfigLoader
from crawl_utils.entry_point import Crawler

config = ConfigLoader(
    config_loader_cfg_path="configs/loader/config_loader_crawl.yaml",
    env_os=["CASHOP_PATHS"]
)

# ✅ 단일 cfg_like로 초기화 (OTO 패턴)
crawler = Crawler(cfg_like=config.to_dict())

# run() 실행
results = crawler.run(
    urls=["https://aliexpress.com/item/123"],
    provider="firefox",
    cas_no="CAS2024-001"
)
```
"""

from __future__ import annotations

from typing import Union, Optional, Any, List, Dict
from pathlib import Path

from logs_utils import LogManager

from ..adapter.sync_crawl import SyncCrawl
from ..presets import PresetManager
from ..core.policy import SyncCrawlPolicy


class Crawler:
    """크롤링 EntryPoint - SyncCrawl Adapter 래퍼 (OTO 패턴)
    
    OTO 패턴 특징:
    - 단일 cfg_like 인자로 통합 설정 전달
    - ConfigLoader.to_dict() 결과를 그대로 사용
    - SyncCrawl에서 SyncCrawlPolicy로 자동 변환
    
    Attributes:
        crawl: SyncCrawl Adapter 인스턴스
    """
    
    def __init__(
        self,
        cfg_like: Union[SyncCrawlPolicy, Path, str, dict, None] = None,
        *,
        preset_manager: Optional[PresetManager] = None,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize Crawler with OTO pattern (단일 cfg_like).
        
        Args:
            cfg_like: SyncCrawlPolicy, YAML 경로, dict, 또는 None
                - dict 형태: {"webdriver_manager": {...}, "crawl": {...}, "log": {...}}
                - ConfigLoader.to_dict() 결과를 그대로 전달
            preset_manager: PresetManager 인스턴스 (None이면 자동 생성)
            log_manager: LogManager 인스턴스 (None이면 기본 생성)
            **overrides: 런타임 오버라이드
        
        Example (OTO Pattern):
            >>> from cfg_utils import ConfigLoader
            >>> config = ConfigLoader(
            ...     "configs/loader/config_loader_crawl.yaml",
            ...     env_os=["CASHOP_PATHS"]
            ... )
            >>> 
            >>> # ✅ 단일 cfg_like 전달
            >>> crawler = Crawler(cfg_like=config.to_dict())
            >>> 
            >>> # run() 실행
            >>> results = crawler.run(
            ...     urls=["https://aliexpress.com/item/123"],
            ...     provider="firefox"
            ... )
        """
        self.crawl = SyncCrawl(
            cfg_like=cfg_like,  # ✅ OTO 패턴: 단일 인자
            preset_manager=preset_manager,
            log_manager=log_manager,
            **overrides
        )
    
    def run(
        self,
        urls: Union[str, List[str]],
        provider: str = "firefox",
        **dynamic_overrides
    ) -> List[Dict[str, Any]]:
        """URL 크롤링 실행 (SyncCrawl.run 위임)
        
        Args:
            urls: 크롤링할 URL (단일 또는 리스트)
            provider: WebDriver provider ("firefox", "chrome" 등)
            **dynamic_overrides: 동적 오버라이드 (cas_no, batch_id 등)
        
        Returns:
            크롤링 결과 리스트
        """
        return self.crawl.run(urls=urls, provider=provider, **dynamic_overrides)
    
    @property
    def log(self):
        """Logger (SyncCrawl에서 위임)"""
        return self.crawl.log
    
    @property
    def preset_manager(self) -> PresetManager:
        """PresetManager (SyncCrawl에서 위임)"""
        return self.crawl.preset_manager


__all__ = ["Crawler"]
