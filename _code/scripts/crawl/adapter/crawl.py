# -*- coding: utf-8 -*-
"""
Crawl Adapter - URL 기반 동기 크롤링 파이프라인.

책임:
1. URL → Site/Method 분석 → CrawlPolicy 선택
2. WebDriver → Navigate → Scroll → Wait → Extract → PostProcess
3. PresetManager 통합
4. Standalone 사용 가능 (ConfigLoader 통합)

EntryPoint와의 역할 분담:
- Adapter (이 파일): 순수 크롤링 로직, URL 처리
- EntryPoint: ConfigLoader 로딩, 파일 I/O, 메타데이터 저장
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from cfg_utils.services.config_like_loader import ConfigLikeLoader
from logs_utils import LogManager

from scripts.crawl.policy.crawl_policy import CrawlScriptPolicy

from crawl_utils.adapter.webdriver_manager import WebDriverManager
from crawl_utils.services.adapter import SyncSeleniumAdapter
from crawl_utils.services.navigator import SyncNavigator
from crawl_utils.services.extractor import SyncJSExtractor
from crawl_utils.presets import PresetManager
from crawl_utils.core.policy import CrawlPolicy


class Crawl:
    """URL 기반 동기 크롤링 파이프라인 (Standalone Adapter).
    
    URL을 받아서 PresetManager로 분석 → CrawlPolicy 선택 → Pipeline 실행
    Adapter Pattern: Policy에 URLs 없음, run()에서 urls 받음
    
    Attributes:
        policy: CrawlScriptPolicy 설정 (webdriver + crawl)
        log: loguru logger 인스턴스
        preset_manager: PresetManager 인스턴스
    
    Example:
        >>> # 기본값 사용
        >>> crawl = Crawl(cfg_like=None, log_manager=log_manager)
        
        >>> # ConfigLoader 사용 (모든 section 병합)
        >>> from cfg_utils import ConfigLoader
        >>> config = ConfigLoader("scripts/crawl/configs/crawl_config_loader.yaml")
        >>> crawl = Crawl(cfg_like=config.to_dict(), log_manager=log_manager)
        
        >>> # Runtime override
        >>> crawl = Crawl(
        ...     cfg_like=None,
        ...     webdriver_manager__region="china",
        ...     crawl__scroll__max_scrolls=15,
        ...     log_manager=log_manager
        ... )
        
        >>> # URL 크롤링 실행
        >>> results = crawl.run(
        ...     urls=["https://www.aliexpress.com/item/123.html"],
        ...     provider="firefox",
        ...     cas_no="CAS2024-001"
        ... )
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        *,
        preset_manager: Optional[PresetManager] = None,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """CrawlScriptPolicy 기반 초기화 (OTO Adapter 패턴).
        
        Logging Strategy:
            1. Primary Logger (Parent): 통합 로그 - 전체 파이프라인 기록
            2. Secondary Logger (Module): 모듈별 로그 - 상세 디버깅용 (선택적)
        
        Args:
            cfg_like: CrawlScriptPolicy, YAML 경로, dict, 또는 None
                - CrawlScriptPolicy: 인스턴스 직접 전달
                - str/Path: YAML 파일 경로
                - dict: ConfigLoader.to_dict() 결과 (모든 section 병합)
                - None: crawl_config_loader.yaml 자동 로드
            preset_manager: PresetManager 인스턴스 (None이면 자동 생성)
            log_manager: LogManager 인스턴스 (없으면 policy.log로 생성)
            **overrides: 런타임 오버라이드 (webdriver_manager__region="china" 등)
        
        Example:
            >>> # 기본값 사용
            >>> crawl = Crawl(log_manager=log_manager)
            
            >>> # ConfigLoader 사용
            >>> config = ConfigLoader("crawl_config_loader.yaml")
            >>> crawl = Crawl(cfg_like=config.to_dict(), log_manager=log_manager)
            
            >>> # Runtime override
            >>> crawl = Crawl(
            ...     cfg_like=None,
            ...     webdriver_manager__firefox__profile_path="M:/Firefox_Profile/CRAWL_GLOBAL",
            ...     log_manager=log_manager
            ... )
        """
        # ConfigLikeLoader로 CrawlScriptPolicy 로드
        self.policy = self._load_config(cfg_like, **overrides)
        
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
        
        if self.policy.log and self.policy.log.enabled and log_manager:
            # Parent logger가 있고 policy.log도 enabled면 모듈 전용 LogManager 생성
            self._module_log_manager = LogManager(self.policy.log)
            self._module_logger = self._module_log_manager.logger
        
        # PresetManager 초기화
        self.preset_manager = preset_manager or PresetManager()
        
        self.log.debug("Crawl adapter initialized with dual logging")
        if self._module_logger:
            self._module_logger.debug("Module-specific logger enabled for detailed debugging")
    
    # ==========================================================================
    # ConfigLikeLoader Integration
    # ==========================================================================
    
    @staticmethod
    def _load_config(
        cfg_like: Union[BaseModel, Path, str, dict, None],
        **overrides: Any
    ) -> CrawlScriptPolicy:
        """CrawlScriptPolicy 로드 (분리된 YAML 파일들을 병합).
        
        복합 Adapter 패턴 (MULTI_POLICY_ADAPTER_PATTERN):
        - cfg_like=None: ConfigLoader로 여러 YAML 파일 자동 병합
        - cfg_like=dict: 외부에서 병합된 dict 전달
        - cfg_like=CrawlScriptPolicy: 인스턴스 직접 전달
        
        Args:
            cfg_like: CrawlScriptPolicy 인스턴스, 병합된 dict, 또는 None
            **overrides: 런타임 오버라이드 (KeyPath 형식)
                예: webdriver_manager__region="china"
        
        Returns:
            CrawlScriptPolicy 인스턴스
        """
        # 1. CrawlScriptPolicy 인스턴스 전달
        if cfg_like is not None and cfg_like.__class__.__name__ == "CrawlScriptPolicy":
            if overrides:
                return cfg_like.model_copy(update=overrides)  # type: ignore
            return cfg_like  # type: ignore
        
        # 2. cfg_like=None → crawl_config_loader.yaml 자동 로드
        if cfg_like is None:
            from cfg_utils import ConfigLoader
            
            config_loader_path = Path(__file__).parent.parent / "configs" / "crawl_config_loader.yaml"
            
            if not config_loader_path.exists():
                raise FileNotFoundError(
                    f"❌ ConfigLoader 설정 파일을 찾을 수 없습니다: {config_loader_path}\n"
                    f"   Crawl Adapter는 cfg_like=None 사용 시 crawl_config_loader.yaml이 필요합니다."
                )
            
            try:
                loader = ConfigLoader(
                    config_loader_cfg_path=str(config_loader_path),
                    env_os=["CASHOP_PATHS"]
                )
                cfg_like = loader.to_dict()
            except Exception as e:
                raise RuntimeError(
                    f"❌ ConfigLoader 실행 실패: {config_loader_path}\n"
                    f"   Error: {type(e).__name__}: {e}\n"
                    f"   💡 Hint: CASHOP_PATHS 환경변수가 설정되어 있는지 확인하세요."
                ) from e
        
        # 3. cfg_like=dict → CrawlScriptPolicy 변환
        if isinstance(cfg_like, dict):
            # overrides 병합
            if overrides:
                from keypath_utils import KeyPathDict
                override_dict = KeyPathDict.to_nested_dict(overrides)
                cfg_like = {**cfg_like, **override_dict}
            
            try:
                return CrawlScriptPolicy(**cfg_like)
            except Exception as e:
                raise ValueError(
                    f"❌ CrawlScriptPolicy 생성 실패\n"
                    f"   Error: {type(e).__name__}: {e}\n"
                    f"   Received dict keys: {list(cfg_like.keys())}"
                ) from e
        
        # 4. 지원하지 않는 타입
        raise TypeError(
            f"❌ Crawl Adapter는 cfg_like로 다음 타입만 지원합니다:\n"
            f"   - CrawlScriptPolicy 인스턴스\n"
            f"   - dict (ConfigLoader.to_dict() 결과)\n"
            f"   - None (crawl_config_loader.yaml 자동 로드)\n"
            f"   받은 타입: {type(cfg_like).__name__}"
        )
    
    def _log_both(self, level: str, message: str, **kwargs):
        """Log to both parent and module loggers."""
        getattr(self.log, level)(message, **kwargs)
        if self._module_logger:
            getattr(self._module_logger, level)(message, **kwargs)
    
    # ==========================================================================
    # Core Pipeline Methods
    # ==========================================================================
    
    def run(
        self,
        urls: Union[str, List[str]],
        provider: str = "firefox",
        **dynamic_overrides
    ) -> List[Dict[str, Any]]:
        """URL 크롤링 실행 (Adapter Pattern).
        
        Adapter Pattern: run()에서 URLs를 받아서 처리합니다.
        
        Pipeline Flow:
            1. URL → PresetManager.analyze_url() → (site, method, region)
            2. PresetManager.get_crawl_policy() → CrawlPolicy (or fallback)
            3. WebDriverManager → Navigator → Extractor → PostProcessor
        
        Args:
            urls: 크롤링할 URL (단일 또는 리스트)
            provider: WebDriver provider ("firefox", "chrome" 등)
            **dynamic_overrides: 동적 오버라이드 (cas_no, batch_id 등)
                - PostProcessor 템플릿 변수로 사용
        
        Returns:
            크롤링 결과 리스트:
            [
                {
                    "url": str,
                    "site": str,
                    "method": str,
                    "data": dict,  # JS 추출 결과
                    "saved_files": List[str],  # 저장된 파일 경로
                    "success": bool,
                    "error": Optional[str]
                },
                ...
            ]
        
        Example:
            >>> crawl = Crawl(log_manager=log_manager)
            >>> results = crawl.run(
            ...     urls=["https://www.aliexpress.com/item/123.html"],
            ...     provider="firefox",
            ...     cas_no="CAS2024-001"
            ... )
            >>> for result in results:
            ...     if result['success']:
            ...         print(f"✅ {result['url']}")
            ...         print(f"   Files: {result['saved_files']}")
        """
        # URL 정규화
        if isinstance(urls, str):
            urls = [urls]
        
        all_results = []
        
        self.log.info(f"{'='*80}")
        self.log.info(f"🌐 Crawl Pipeline: {len(urls)} URLs")
        self.log.info(f"{'='*80}\n")
        
        for url in urls:
            try:
                # 1. URL 분석
                site, method, region = self.preset_manager.analyze_url(url)
                self.log.info(f"📍 Analyzed: {url}")
                self.log.info(f"   → Site: {site}, Method: {method}, Region: {region}")
                
                # 2. 정책 로드 (Preset 없으면 fallback 사용)
                policy_dict = self.preset_manager.get_crawl_policy(site, method)
                if not policy_dict:
                    self.log.warning(f"⚠️  No preset for ({site}, {method}), using fallback CrawlPolicy")
                    crawl_policy = self.policy.crawl
                else:
                    self.log.info(f"✅ Preset found: {site}/{method}")
                    crawl_policy = CrawlPolicy(**policy_dict)
                
                # 3. WebDriver 설정
                webdriver_config = self._build_webdriver_config(region, provider)
                
                # 4. Pipeline 실행
                result = self._execute(url, crawl_policy, webdriver_config, dynamic_overrides)
                all_results.append(result)
                
            except Exception as e:
                self.log.error(f"❌ Failed: {url} - {e}")
                import traceback
                self.log.debug(traceback.format_exc())
                all_results.append({
                    "url": url,
                    "error": str(e),
                    "success": False
                })
        
        self.log.info(f"\n{'='*80}")
        self.log.success(f"✅ Crawl Pipeline Completed: {len(all_results)} results")
        self.log.info(f"{'='*80}\n")
        
        return all_results
    
    def _build_webdriver_config(
        self,
        region: str,
        provider: str
    ) -> Dict[str, Any]:
        """WebDriver 설정 구성 (Policy + Preset Override)."""
        # 1. Policy를 dict로 변환
        base_config = self.policy.webdriver_manager.model_dump(exclude_none=True)
        
        # 2. Preset override 적용
        override = self.preset_manager.get_webdriver_override(region, provider)
        if override:
            if provider not in base_config:
                base_config[provider] = {}
            
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
        """Pipeline 실행: WebDriver → Navigate → Scroll → Wait → Extract → PostProcess."""
        wd_manager = None
        
        for attempt in range(1 + crawl_policy.retries):
            try:
                # WebDriver 시작
                self.log.info(f"[1/6] Starting WebDriver ({webdriver_config['provider']})...")
                wd_manager = WebDriverManager(webdriver_config)
                wd_manager.start()
                self.log.success("✅ WebDriver started")
                
                # SyncSeleniumAdapter로 래핑
                adapter = SyncSeleniumAdapter(driver=wd_manager._webdriver)
                
                # Navigator로 페이지 로드
                self.log.info(f"\n[2/6] Loading: {url}")
                navigator = SyncNavigator(driver=adapter, policy=crawl_policy)
                navigator.load(base_url=url)
                self.log.success("✅ Page loaded")
                
                # Scroll (선택적)
                if crawl_policy.scroll and crawl_policy.scroll.strategy != "none":
                    self.log.info(f"\n[3/6] Scrolling ({crawl_policy.scroll.strategy})...")
                    navigator.scroll(
                        strategy=crawl_policy.scroll.strategy,
                        max_scrolls=crawl_policy.scroll.max_scrolls,
                        pause_sec=crawl_policy.scroll.scroll_pause_sec
                    )
                    self.log.success("✅ Scroll completed")
                else:
                    self.log.info("\n[3/6] Skipping scroll")
                
                # Wait (선택적)
                if crawl_policy.wait and crawl_policy.wait.hook != "none":
                    self.log.info(f"\n[4/6] Waiting for: {crawl_policy.wait.selector}")
                    navigator.wait(
                        hook=crawl_policy.wait.hook,
                        selector=crawl_policy.wait.selector,
                        timeout=crawl_policy.wait.timeout_sec,
                        condition=crawl_policy.wait.condition
                    )
                    self.log.success("✅ Wait completed")
                else:
                    self.log.info("\n[4/6] Skipping wait")
                
                # Extract
                self.log.info("\n[5/6] Extracting data...")
                extractor = SyncJSExtractor(adapter=adapter, policy=crawl_policy)
                data = extractor.extract()
                
                # dynamic_overrides 병합
                data.update(dynamic_overrides)
                self.log.success(f"✅ Extraction completed: {len(data)} fields")
                
                # PostProcessor 실행 (선택적)
                saved_files = []
                if crawl_policy.post_processor:
                    self.log.info("\n[6/6] Running PostProcessor...")
                    from crawl_utils.services.post_processor import SyncPostProcessor
                    
                    try:
                        post_processor = SyncPostProcessor(crawl_policy.post_processor)
                        save_summary = post_processor.process(data, dynamic_overrides)
                        
                        saved_files = [str(artifact.path) for artifact in save_summary.flatten()]
                        self.log.success(f"✅ PostProcessor: {len(saved_files)} files saved")
                        
                    except Exception as e:
                        self.log.error(f"❌ PostProcessor failed: {e}")
                        import traceback
                        self.log.debug(traceback.format_exc())
                else:
                    self.log.info("\n[6/6] Skipping PostProcessor")
                
                return {
                    "url": url,
                    "site": crawl_policy.site,
                    "method": crawl_policy.method,
                    "data": data,
                    "saved_files": saved_files,
                    "success": True
                }
            
            except Exception as e:
                if attempt < crawl_policy.retries:
                    wait_time = crawl_policy.retry_backoff_sec * (2 ** attempt)
                    self.log.warning(f"⚠️  Retry {attempt+1}/{crawl_policy.retries} after {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    self.log.error(f"❌ Execution failed after {crawl_policy.retries} retries: {e}")
                    import traceback
                    self.log.debug(traceback.format_exc())
                    return {"url": url, "error": str(e), "success": False}
            
            finally:
                if wd_manager:
                    self.log.info("Closing WebDriver...")
                    wd_manager.quit()
    
    def __repr__(self) -> str:
        return f"Crawl(policy={self.policy.__class__.__name__})"


__all__ = ["Crawl"]
