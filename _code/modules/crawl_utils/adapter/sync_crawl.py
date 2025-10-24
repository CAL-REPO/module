# -*- coding: utf-8 -*-
"""crawl_utils.adapter.sync_crawl
==================================

SyncCrawl Adapter - URL 기반 동기 크롤링 (OTO 패턴)

통합 정책 사용:
- SyncCrawlPolicy: WebDriverManagerPolicy + CrawlPolicy 통합

사용 예시:
    >>> from crawl_utils.adapter import SyncCrawl
    >>> from logs_utils import LogManager
    >>> 
    >>> # ConfigLoader로 전체 섹션 병합
    >>> from cfg_utils import ConfigLoader
    >>> config = ConfigLoader(
    ...     config_loader_cfg_path="configs/loader/config_loader_crawl.yaml",
    ...     env_os=["CASHOP_PATHS"]
    ... )
    >>> 
    >>> # SyncCrawl 초기화 (OTO 패턴 - 단일 cfg_like)
    >>> log_mgr = LogManager(name="crawl", level="INFO")
    >>> crawl = SyncCrawl(
    ...     cfg_like=config.to_dict(),  # ✅ 통합 dict (단일 인자)
    ...     log_manager=log_mgr
    ... )
    >>> 
    >>> # run()에서 URL 전달
    >>> # - Preset 있으면 Preset 사용
    >>> # - Preset 없으면 policy.crawl 사용 (fallback)
    >>> results = crawl.run(
    ...     urls=["https://aliexpress.com/item/123.html"],
    ...     provider="firefox",
    ...     cas_no="CAS2024-001"
    ... )
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from pydantic import BaseModel

from logs_utils import LogManager

from ..presets import PresetManager
from ..core.policy import SyncCrawlPolicy, CrawlPolicy
from ..adapter.webdriver_manager import WebDriverManager
from ..services.adapter import SyncSeleniumAdapter
from ..services.navigator import SyncNavigator
from ..services.extractor import SyncJSExtractor


class SyncCrawl:
    """SyncCrawl Adapter - URL 기반 동기 크롤링 (OTO 패턴)
    
    통합 정책 (SyncCrawlPolicy):
    - webdriver_manager: WebDriverManagerPolicy (WebDriver 설정)
    - crawl: CrawlPolicy (Preset 없을 때 fallback)
    - log: LogPolicy (로깅 설정)
    
    run(): URL → PresetManager → CrawlPolicy (or fallback) + Override
    
    Attributes:
        policy: SyncCrawlPolicy (통합 정책)
        preset_manager: PresetManager 인스턴스
        log: loguru logger
    """
    
    def __init__(
        self,
        cfg_like: Union[SyncCrawlPolicy, Path, str, dict, None] = None,
        *,
        preset_manager: Optional[PresetManager] = None,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """SyncCrawl Adapter 초기화 (OTO 패턴 - 단일 cfg_like)
        
        OTO 패턴 특징:
        - 단일 cfg_like 인자로 통합 설정 전달
        - ConfigLoader.to_dict() 결과를 그대로 사용
        - _load_config()에서 SyncCrawlPolicy로 자동 변환
        
        Logging Strategy:
            1. Primary Logger (Parent): log_manager 우선 사용
            2. Secondary Logger (Module): policy.log에서 로드 (선택적)
        
        Args:
            cfg_like: SyncCrawlPolicy, YAML 경로, dict, 또는 None
                - dict 형태: {"webdriver_manager": {...}, "crawl": {...}, "log": {...}}
                - ConfigLoader.to_dict() 결과를 그대로 전달
            preset_manager: PresetManager 인스턴스 (None이면 자동 생성)
            log_manager: LogManager 인스턴스 (선택사항)
            **overrides: 런타임 오버라이드
        """
        # 1. SyncCrawlPolicy 로드 (통합 정책)
        self.policy = self._load_config(cfg_like, **overrides)
        
        # 2. PresetManager 초기화
        self.preset_manager = preset_manager or PresetManager()
        
        # ========================================
        # Primary Logger: Parent logger (통합 로그)
        # ========================================
        if log_manager:
            self.log = log_manager.logger
            self._parent_log_manager = log_manager
        elif self.policy.log:
            self._parent_log_manager = LogManager(self.policy.log)
            self.log = self._parent_log_manager.logger
        else:
            self._parent_log_manager = None
            self.log = LogManager({"enabled": False}).logger
        
        # ========================================
        # Secondary Logger: Module logger (모듈별 로그 - 선택적)
        # ========================================
        self._module_log_manager = None
        self._module_logger = None
        
        # policy.crawl.log이 있고 parent logger와 다르면 모듈 전용 logger 생성
        if self.policy.crawl.log and log_manager:
            try:
                self._module_log_manager = LogManager(self.policy.crawl.log)
                self._module_logger = self._module_log_manager.logger
            except Exception as e:
                self.log.debug(f"Could not create module logger: {e}")
        
        self.log.debug("SyncCrawl initialized (OTO Pattern - Single Policy)")
        if self._module_logger:
            self._module_logger.debug("Module-specific logger enabled for detailed debugging")
    
    @staticmethod
    def _load_config(cfg_like, **overrides) -> SyncCrawlPolicy:
        """Load SyncCrawlPolicy (OTO 패턴)
        
        ConfigLikeLoader를 사용하여 통합 정책 로드:
        - cfg_like=None: sync_crawl.yaml 기본 로드
        - cfg_like=dict: ConfigLoader.to_dict() 결과 파싱
        - cfg_like=Path/str: YAML 파일 로드
        """
        from cfg_utils.services.config_like_loader import ConfigLikeLoader
        
        return ConfigLikeLoader.load(
            cfg_like=cfg_like,
            policy_class=SyncCrawlPolicy,
            module_file=__file__,
            config_filename="sync_crawl.yaml",  # 기본 fallback (통합 정책 예시)
            **overrides
        )
    
    def run(
        self,
        urls: Union[str, List[str]],
        provider: str = "firefox",
        **dynamic_overrides
    ) -> List[Dict[str, Any]]:
        """URL 크롤링 실행 (OTO 패턴)
        
        Args:
            urls: 크롤링할 URL (단일 또는 리스트)
            provider: WebDriver provider ("firefox", "chrome" 등)
            **dynamic_overrides: 동적 오버라이드 (cas_no, batch_id 등)
                - PostProcessor 템플릿 변수로 사용
                - 추출 데이터에 메타데이터로 추가
        
        Returns:
            크롤링 결과 리스트
        """
        # URL 정규화
        if isinstance(urls, str):
            urls = [urls]
        
        all_results = []
        
        for url in urls:
            try:
                # 1. URL 분석
                site, method, region = self.preset_manager.analyze_url(url)
                self.log.info(f"Analyzed URL: {url} → {site}/{method} (region={region})")
                
                # 2. 정책 로드 (Preset 없으면 fallback 사용)
                policy_dict = self.preset_manager.get_crawl_policy(site, method)
                if not policy_dict:
                    self.log.warning(f"No preset for ({site}, {method}), using fallback CrawlPolicy")
                    crawl_policy = self.policy.crawl  # ✅ OTO 패턴: policy.crawl 사용
                else:
                    crawl_policy = CrawlPolicy(**policy_dict)
                
                # 3. WebDriver 설정
                webdriver_config = self._build_webdriver_config(region, provider)
                
                # 4. Pipeline 실행 (dynamic_overrides 전달)
                result = self._execute(url, crawl_policy, webdriver_config, dynamic_overrides)
                all_results.append(result)
                
            except Exception as e:
                self.log.error(f"Failed: {url} - {e}")
                all_results.append({"url": url, "error": str(e), "success": False})
        
        return all_results
    
    def _build_webdriver_config(
        self,
        region: str,
        provider: str
    ) -> Dict[str, Any]:
        """WebDriver 설정 구성 (Policy + Preset Override)
        
        OTO 패턴:
        1. self.policy.webdriver_manager에서 기본 dict 추출
        2. PresetManager에서 region/provider 기반 override 추출
        3. override를 기본 dict에 병합
        """
        # 1. Policy를 dict로 변환 (기본 설정)
        base_config = self.policy.webdriver_manager.model_dump(exclude_none=True)  # ✅ OTO 패턴
        
        # 2. Preset override 적용
        override = self.preset_manager.get_webdriver_override(region, provider)
        if override:
            # provider 섹션이 없으면 생성
            if provider not in base_config:
                base_config[provider] = {}
            
            # override 병합
            if isinstance(base_config[provider], dict):
                base_config[provider].update(override)
            
            self.log.debug(f"Applied preset override for {region}/{provider}")
        
        # 3. provider와 region 명시적 설정
        base_config["provider"] = provider
        base_config["region"] = region
        
        return base_config
    
    def _execute(
        self,
        url: str,
        crawl_policy: CrawlPolicy,
        webdriver_config: Dict[str, Any],
        dynamic_overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Pipeline 실행: WebDriver → Navigate → Scroll → Wait → Extract → PostProcess
        
        Pipeline 옵션:
        1. 기본 방식 (현재): Navigator + Extractor 직접 사용
        2. CrawlMethod 방식 (선택): CrawlMethodFactory로 Template Method 패턴 적용
        
        CrawlMethod 사용 예시 (향후 개선):
            ```python
            from crawl_utils.services.crawl_methods import CrawlMethodFactory
            
            crawl_service = CrawlMethodFactory.create(
                method=crawl_policy.method,
                navigator=navigator,
                extractor=extractor,
                policy=crawl_policy,
                logger=self.log
            )
            results = crawl_service.crawl(urls=[url], runtime_context=dynamic_overrides)
            ```
        
        Args:
            url: 크롤링할 URL (source)
            crawl_policy: CrawlPolicy (정책)
            webdriver_config: WebDriver 설정 (config)
            dynamic_overrides: 동적 오버라이드 (cas_no 등)
        """
        wd_manager = None
        
        try:
            # WebDriver 시작
            self.log.info(f"Starting WebDriver ({webdriver_config['provider']})")
            wd_manager = WebDriverManager(webdriver_config)
            wd_manager.start()
            
            # SyncSeleniumAdapter로 래핑
            adapter = SyncSeleniumAdapter(driver=wd_manager._webdriver)
            
            # Navigator로 페이지 로드
            self.log.info(f"Loading: {url}")
            navigator = SyncNavigator(driver=adapter, policy=crawl_policy)
            navigator.load(base_url=url)
            
            # Scroll (선택적)
            if crawl_policy.scroll:
                self.log.info(f"Scrolling ({crawl_policy.scroll.strategy})")
                navigator.scroll(
                    strategy=crawl_policy.scroll.strategy,
                    max_scrolls=crawl_policy.scroll.max_scrolls,
                    pause_sec=crawl_policy.scroll.scroll_pause_sec
                )
            
            # Wait (선택적)
            if crawl_policy.wait:
                self.log.info(f"Waiting for: {crawl_policy.wait.selector}")
                navigator.wait(
                    hook=crawl_policy.wait.hook,
                    selector=crawl_policy.wait.selector,
                    timeout=crawl_policy.wait.timeout_sec,
                    condition=crawl_policy.wait.condition
                )
            
            # Extract
            self.log.info("Extracting data")
            extractor = SyncJSExtractor(adapter=adapter, policy=crawl_policy)
            data = extractor.extract()
            
            # dynamic_overrides를 추출 데이터에 병합
            data.update(dynamic_overrides)
            
            # PostProcessor 실행 (선택적)
            saved_files = []
            if crawl_policy.post_processor:
                self.log.info("Running PostProcessor")
                from ..services.post_processor import SyncPostProcessor
                
                try:
                    post_processor = SyncPostProcessor(crawl_policy.post_processor)
                    save_summary = post_processor.process(data, dynamic_overrides)
                    
                    # 저장된 파일 경로 수집
                    saved_files = [str(artifact.path) for artifact in save_summary.flatten()]
                    self.log.success(f"  Saved: {len(saved_files)} files")
                    
                except Exception as e:
                    self.log.error(f"  PostProcessor failed: {e}")
                    import traceback
                    self.log.debug(traceback.format_exc())
            
            return {
                "url": url,
                "site": crawl_policy.site,
                "method": crawl_policy.method,
                "data": data,
                "saved_files": saved_files,
                "success": True
            }
        
        except Exception as e:
            self.log.error(f"Execution failed: {e}")
            return {"url": url, "error": str(e), "success": False}
        
        finally:
            if wd_manager:
                self.log.info("Closing WebDriver")
                wd_manager.quit()


__all__ = ["SyncCrawl"]
