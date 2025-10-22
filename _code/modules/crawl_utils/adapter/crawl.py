# -*- coding: utf-8 -*-
"""Crawl - Core crawling business logic (XLOTO Adapter pattern).

책임:
1. URL 리스트를 받아 크롤링 실행
2. URL 분석 및 site/method 자동 감지 (UrlAnalyzer)
3. 메서드별 preset 선택 (MethodResolver)
4. 메서드 브랜칭 로직 (product_detail vs product_search)
5. Pipeline 오케스트레이션 (WebDriver 초기화, 페이지 로드, 데이터 추출)
6. 추출된 데이터 반환 (List[Dict])

XLOTO Pattern:
- Adapter: 비즈니스 로직 (URL 분석, 메서드 브랜칭, 크롤링 실행)
- EntryPoint: YAML 기반 설정 로드 및 Adapter 위임

사용 예시:
```python
# 1. ConfigLoader로 전체 설정 로드
config = ConfigLoader(config_loader_cfg_path="configs/loader/config_loader_crawl.yaml")
crawl_config = config.to_dict(section="crawl")

# 2. Crawl Adapter 생성
crawl = Crawl(crawl_config)

# 3. URLs 크롤링 (자동 site/method 감지)
urls = [
    "https://aliexpress.com/item/123",
    "https://taobao.com/item/456.htm"
]
results = crawl.run(urls)
```
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Optional, Any, Union

from modules.logs_utils import LogManager

from ..core.policy import CrawlPolicy
# from ..provider.base import BaseWebDriver  # Deprecated - Use WebDriverAdapter
from ..services.url_analyzer import UrlAnalyzer
from ..services.method_resolver import MethodResolver


class Crawl:
    """Core crawling service providing run() API.
    
    Standalone 사용 가능 + Crawler에서 위임 받는 Adapter 역할 겸용.
    
    Attributes:
        policy: CrawlPolicy 설정
        webdriver: BaseWebDriver 인스턴스 (lazy-loaded)
        fetcher: PageFetcher 인스턴스 (lazy-loaded)
        extractor: DataExtractor 인스턴스 (lazy-loaded)
        navigator: Navigator 인스턴스 (lazy-loaded)
        log: loguru logger 인스턴스
    """
    
    def __init__(
        self,
        cfg_like: Union[Path, str, dict, CrawlPolicy, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize Crawl with policy.
        
        Args:
            cfg_like: CrawlPolicy, YAML 경로, dict, 또는 None
            log_manager: 외부 LogManager (선택사항)
            **overrides: 런타임 오버라이드
        
        Example:
            >>> # ConfigLoader에서 section 추출 (권장)
            >>> config = ConfigLoader(config_loader_cfg_path="config_loader_crawl.yaml")
            >>> crawl_config = config.to_dict(section="crawl")
            >>> crawl = Crawl(crawl_config)
            
            >>> # YAML에서 직접 로드
            >>> crawl = Crawl("configs/crawl.yaml")
            
            >>> # dict로 직접 설정
            >>> crawl = Crawl({"site": "aliexpress", "source": {"method": "product_detail"}})
            
            >>> # Policy 인스턴스로
            >>> policy = CrawlPolicy(...)
            >>> crawl = Crawl(policy)
            
            >>> # 런타임 오버라이드
            >>> crawl = Crawl("config.yaml", wait__timeout=20)
        """
        # Load policy
        self.policy = self._load_config(cfg_like, **overrides)
        
        # LogManager 생성 (우선순위: 외부 log_manager > policy.log > 기본)
        if log_manager:
            self.log = log_manager.logger
        elif self.policy.log:
            self.log = LogManager(self.policy.log).logger
        else:
            self.log = LogManager({"enabled": False}).logger
        
        # URL 분석 서비스 (config에서 url_patterns 추출)
        url_patterns = None
        if hasattr(self.policy, 'url_patterns') and self.policy.url_patterns:
            url_patterns = self.policy.url_patterns
        self.url_analyzer = UrlAnalyzer(url_patterns)
        
        # Services는 lazy-load
        # Lazy-loaded components
        self._webdriver: Optional[Any] = None  # WebDriverAdapter or Legacy
        self._adapter = None  # SyncSeleniumAdapter
        self._navigator = None  # SyncNavigator
        self._extractor = None  # SyncExtractor (DOM or JS)
        # self._fetcher = None
    
    # ==========================================================================
    # Config Loading (ConfigLikeLoader pattern)
    # ==========================================================================
    
    def _load_config(self, cfg_like, **overrides) -> CrawlPolicy:
        """Load CrawlPolicy from various sources.
        
        Args:
            cfg_like: CrawlPolicy instance, YAML path, dict, or None
            **overrides: Runtime overrides
        
        Returns:
            CrawlPolicy instance
        """
        from cfg_utils.services import ConfigLikeLoader
        
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=CrawlPolicy,
            caller_file=__file__,
            default_config_filename="crawl.yaml",
            **overrides
        )
    
    # ==========================================================================
    # Services (Lazy Loading)
    # ==========================================================================
    
    @property
    def webdriver(self) -> Any:
        """Lazy webdriver creation.
        
        Returns:
            WebDriver instance (WebDriverAdapter or Legacy)
        """
        if self._webdriver is None:
            self.log.debug("[Crawl] Creating WebDriver")
            
            # TODO: WebDriverAdapter로 마이그레이션 필요
            # from ..adapter import WebDriverAdapter
            # self._webdriver = WebDriverAdapter()
            
            self.log.warning("[Crawl] WebDriver lazy loading is deprecated. "
                           "Please provide webdriver instance directly.")
            self._webdriver = None
        
        return self._webdriver
    
    @property
    def adapter(self):
        """Lazy BrowserController adapter creation.
        
        BaseWebDriver를 BrowserController Protocol로 변환합니다.
        
        Returns:
            SyncSeleniumAdapter instance
        """
        if not hasattr(self, '_adapter') or self._adapter is None:
            self.log.debug("[Crawl] Creating SyncSeleniumAdapter")
            from ..services.adapter import SyncSeleniumAdapter
            
            driver = self.webdriver
            if driver is None:
                self.log.warning("[Crawl] WebDriver not available for adapter")
                self._adapter = None
                return None
            
            self._adapter = SyncSeleniumAdapter(driver)
            self.log.debug(f"[Crawl] SyncSeleniumAdapter created")
        
        return self._adapter
    
    @property
    def navigator(self):
        """Lazy navigator creation.
        
        SyncSeleniumAdapter를 사용하여 SyncNavigator를 생성합니다.
        
        Returns:
            SyncNavigator instance
        """
        if self._navigator is None:
            self.log.debug("[Crawl] Creating SyncNavigator")
            from ..services.navigator import SyncNavigator
            
            adapter = self.adapter
            if adapter is None:
                self.log.warning("[Crawl] Adapter not available for navigator")
                return None
            
            self._navigator = SyncNavigator(driver=adapter, policy=self.policy)
            self.log.debug(f"[Crawl] SyncNavigator created")
        
        return self._navigator
    
    @property
    def extractor(self):
        """Lazy extractor creation.
        
        ExtractorPolicy 기반으로 SyncExtractor를 생성합니다.
        
        Returns:
            SyncDOMExtractor 또는 SyncJSExtractor
        """
        if self._extractor is None:
            self.log.debug("[Crawl] Creating SyncExtractor")
            from ..services.sync_extractor import SyncExtractorFactory
            
            adapter = self.adapter
            if adapter is None:
                self.log.warning("[Crawl] Adapter not available for extractor")
                return None
            
            try:
                factory = SyncExtractorFactory(adapter, self.policy)
                self._extractor = factory.create()
                self.log.debug(f"[Crawl] SyncExtractor created: {type(self._extractor).__name__}")
            except Exception as e:
                self.log.warning(f"[Crawl] Failed to create extractor: {e}")
                self._extractor = None
        
        return self._extractor
    
    # ==========================================================================
    # Main API
    # ==========================================================================
    
    def run(self, urls: Optional[List[str]] = None, **runtime_context: Any) -> List[Dict[str, Any]]:
        """Crawl URLs and return extracted data.
        
        XLOTO Pattern - URL 분석 및 메서드 브랜칭:
        ✅ URL 자동 분석: UrlAnalyzer로 site/method 추출
        ✅ Preset 자동 선택: MethodResolver로 적절한 config 선택
        ✅ 메서드 브랜칭: product_detail vs product_search 분기
        ✅ 배치 크롤링: 여러 URL을 순차 처리
        ✅ 에러 핸들링: 실패한 URL은 건너뛰기
        
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
            >>> # Crawl Adapter 생성
            >>> crawl = Crawl(crawl_config)
            >>> 
            >>> # URLs 크롤링 (자동 site/method 감지)
            >>> urls = [
            ...     "https://aliexpress.com/item/123",
            ...     "https://taobao.com/item/456.htm"
            ... ]
            >>> results = crawl.run(urls, cas_no="123-45-6")
            >>> print(results)
            [{"images": [...], "title": "..."}, {"images": [...], "title": "..."}]
        """
        # 1. URLs 결정 (인자 > policy.source.urls)
        target_urls = urls if urls is not None else self.policy.source.urls
        
        if not target_urls:
            self.log.warning("No URLs to crawl")
            return []
        
        self.log.info(f"[Crawl] Starting crawl: {len(target_urls)} URLs")
        
        # 2. URL 분석 및 site/method 자동 감지
        if not self.policy.site or not self.policy.method:
            # 첫 번째 URL로 site/method 추출
            first_url = target_urls[0]
            detected_site, detected_method = self.url_analyzer.analyze(first_url)
            
            # policy에 설정 (auto-detection)
            self.policy.site = detected_site
            self.policy.method = detected_method
            
            self.log.info(f"  Auto-detected: site='{detected_site}', method='{detected_method}'")
        else:
            self.log.info(f"  Using policy: site='{self.policy.site}', method='{self.policy.method}'")
        
        # 3. 메서드 브랜칭 (product_detail vs product_search)
        from ..services.crawl_methods import CrawlMethodFactory
        
        # 메서드별 크롤링 서비스 생성
        crawl_service = CrawlMethodFactory.create(
            method=self.policy.method,
            navigator=self.navigator,
            extractor=self.extractor,
            policy=self.policy,
            logger=self.log
        )
        
        # 크롤링 실행
        results = crawl_service.crawl(target_urls, runtime_context)
        
        self.log.success(f"[Crawl] Completed: {len(results)}/{len(target_urls)} successful")
        
        return results
    
    # ==========================================================================
    # Resource Cleanup
    # ==========================================================================
    
    def close(self):
        """WebDriver 종료 및 리소스 정리."""
        if self._webdriver:
            try:
                self._webdriver.quit()
                self.log.debug("WebDriver closed")
            except Exception as e:
                self.log.warning(f"Error closing WebDriver: {e}")
            finally:
                self._webdriver = None
                self._adapter = None
                self._navigator = None
    
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
            if self._webdriver:
                self.close()
        except Exception:
            pass
