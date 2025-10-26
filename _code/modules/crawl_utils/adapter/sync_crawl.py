# -*- coding: utf-8 -*-
"""crawl_utils.adapter.sync_crawl
==================================

SyncCrawl Adapter - URL 기반 동기 크롤링 (OTO 패턴)

통합 정책 사용:
- SyncCrawlPolicy: WebDriverManagerPolicy + CrawlPolicy + preset 통합

Preset 사용:
- 정책 레벨 preset (YAML 또는 cfg_like에서 지정)
- **overrides로만 오버라이드 가능 (런타임 preset 파라미터 없음)

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
    >>> # SyncCrawl 초기화
    >>> log_mgr = LogManager(name="crawl", level="INFO")
    >>> crawl = SyncCrawl(
    ...     cfg_like=config.to_dict(),
    ...     log_manager=log_mgr
    ... )
    >>> 
    >>> # run()에서 정책 기본값 사용 (provider="firefox")
    >>> results = crawl.run(
    ...     urls=["https://aliexpress.com/item/123.html"]
    ... )
    >>> 
    >>> # run()에서 **overrides로 provider
    >>> results = crawl.run(
    ...     urls=["https://taobao.com/item/456.htm"],
    ...     webdriver_manager__provider="chrome",  # provider override
    ... )
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel

from logs_utils import LogManager

from ..presets import (
    analyze_url,
    get_preset,
    get_webdriver_override,
    PROVIDER_SPECIFIC_FIELDS,
)
from ..core.policy import SyncCrawlPolicy
from ..adapter.webdriver_manager import WebDriverManager
from ..services.adapter import SyncSeleniumAdapter
from ..services.navigator import SyncNavigator
from ..services.extractor import SyncExtractorFactory, SyncJSExtractor


class SyncCrawl:
    """SyncCrawl Adapter - URL 기반 동기 크롤링 (OTO 패턴)
    
    Architecture:
    1. ConfigLoader가 모든 section 병합 (webdriver_manager, crawl, log)
    2. SectionExtractor가 Policy.name으로 section 추출 (Cascading Priority 적용)
    3. 각 모듈 Adapter에 추출된 cfg_like 전달
    4. 파이프라인 실행: WebDriver → Navigate → Extract →
    
    Design Pattern:
    - Pass-through: SyncCrawl은 ConfigLoader 병합 dict를 받아서 SectionExtractor로 추출만 수행
    - SRP: 각 모듈이 자신의 cfg_like 처리 담당 (cfg_like=None → Pydantic 기본값)
    - Cascading Priority: 개별 cfg_like > 병합 section > None
    
    Attributes:
        policy: SyncCrawlPolicy 설정 (로깅용 - 모든 서브 모듈 정책 통합)
        log: loguru logger 인스턴스
    
    Example:
        >>> # 기본값 사용 (모든 모듈이 Pydantic 기본값)
        >>> crawl = SyncCrawl(log_manager=log_manager)
        
        >>> # 외부에서 ConfigLoader 실행 (권장)
        >>> from cfg_utils import ConfigLoader
        >>> config = ConfigLoader(
        ...     config_loader_cfg_path="configs/loader/config_loader_crawl.yaml",
        ...     env_os=["CASHOP_PATHS"]
        ... )
        >>> crawl = SyncCrawl(cfg_like=config.to_dict(), log_manager=log_manager)
        
        >>> # 개별 cfg_like 우선 (Cascading Priority)
        >>> crawl = SyncCrawl(
        ...     cfg_like=config.to_dict(),  # 병합 dict (우선순위 2)
        ...     cfg_like_crawl={"site": "aliexpress"},  # 개별 cfg_like (우선순위 1)
        ...     log_manager=log_manager
        ... )
        
        >>> # Runtime override (KeyPath 형식)
        >>> crawl = SyncCrawl(
        ...     cfg_like=config.to_dict(),
        ...     crawl__site="aliexpress",
        ...     log_manager=log_manager
        ... )
    
    Note:
        ⚠️ ConfigLoader 실행은 EntryPoint 또는 외부 스크립트 책임.
        ⚠️ cfg_like=None 사용 시: 모든 모듈이 Pydantic 기본값 사용.
    """
    
    def __init__(
        self,
        cfg_like: Union[dict, None] = None,
        *,
        cfg_like_webdriver_manager: Union[BaseModel, Path, str, dict, None] = None,
        cfg_like_crawl: Union[BaseModel, Path, str, dict, None] = None,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Pass-through 패턴 초기화 (완전 하드코딩 제거 + 캐싱).
        
        Architecture:
            1. ConfigLoader가 모든 section 병합 (webdriver_manager, crawl, log)
            2. SectionExtractor.extract_batch()가 Policy.name으로 section 추출 (Cascading Priority)
            3. get_policy_name() 헬퍼로 추출 결과 접근 (하드코딩 없음)
            4. 각 모듈에 추출된 cfg_like 전달 (개별 > 병합 > None)
        
        Zero Hard-coding:
            - ✅ Policy 클래스만 사용 (section 이름 불필요)
            - ✅ Policy.name 필드로 자동 추출
            - ✅ get_policy_name() 캐싱으로 성능 최적화
        
        Logging Strategy:
            - SyncCrawl: Parent logger만 관리 (전체 파이프라인 기록)
            - 개별 모듈: 자신의 policy.log로 logger 생성 (SRP 준수)
            - log_manager 전달 시: 모듈이 parent logger 사용
        
        Args:
            cfg_like: 병합된 dict 또는 None
                - dict: 외부에서 준비한 병합 dict (ConfigLoader.to_dict() 결과)
                - None: 빈 dict (개별 모듈은 Pydantic 기본값 사용)
            cfg_like_webdriver_manager: WebDriverManagerPolicy 개별 설정 (우선순위 1)
            cfg_like_crawl: CrawlPolicy 개별 설정 (우선순위 1)
            log_manager: LogManager 인스턴스 (없으면 policy.log로 생성)
            **overrides: 런타임 오버라이드 (crawl__site="aliexpress" 등)
        
        Cascading Priority:
            1. cfg_like_webdriver_manager (개별 cfg_like) - 최우선
            2. cfg_like["webdriver_manager"] (병합 dict의 section) - Policy.name으로 추출
            3. None (Pydantic 기본값) - fallback
        
        Example:
            >>> # 기본값 사용 (모든 모듈이 Pydantic 기본값)
            >>> crawl = SyncCrawl(log_manager=log_manager)
            
            >>> # 외부에서 ConfigLoader 실행 후 전달 (권장)
            >>> from cfg_utils import ConfigLoader
            >>> config = ConfigLoader(
            ...     config_loader_cfg_path="configs/loader/config_loader_crawl.yaml",
            ...     env_os=["CASHOP_PATHS"]
            ... )
            >>> crawl = SyncCrawl(cfg_like=config.to_dict(), log_manager=log_manager)
            
            >>> # 개별 cfg_like 우선 (Cascading Priority)
            >>> crawl = SyncCrawl(
            ...     cfg_like=config.to_dict(),  # 병합 dict (우선순위 2)
            ...     cfg_like_crawl={"site": "aliexpress"},  # 개별 cfg_like (우선순위 1)
            ...     log_manager=log_manager
            ... )
            
            >>> # Runtime override (KeyPath 형식)
            >>> crawl = SyncCrawl(
            ...     cfg_like=None,
            ...     crawl__site="aliexpress",
            ...     log_manager=log_manager
            ... )
        
        Note:
            ⚠️ ConfigLoader 실행은 EntryPoint 또는 외부 스크립트에서 수행.
            ⚠️ cfg_like=None: 모든 모듈이 Pydantic 기본값 사용 (동작하지만 권장하지 않음).
        """
        # ========================================
        # Config 준비 (외부에서 준비한 dict 또는 None)
        # ========================================
        merged_config = cfg_like or {}
        
        # Runtime overrides 병합
        if overrides:
            from keypath_utils import KeyPathDict
            override_dict = KeyPathDict.to_nested_dict(overrides)
            merged_config = {**merged_config, **override_dict}
        
        # ========================================
        # ✅ SectionExtractor.extract_batch() 사용 (완전 하드코딩 제거)
        # ========================================
        # Import policies here to avoid circular imports
        from crawl_utils.provider.policy import WebDriverManagerPolicy
        
        # 우선순위: 개별 cfg_like > merged_config[Policy.name] > None
        from cfg_utils.services.section_extractor import SectionExtractor
        
        extracted = SectionExtractor.extract_batch(
            merged_config=merged_config,
            individual_cfgs={
                WebDriverManagerPolicy: cfg_like_webdriver_manager,
                SyncCrawlPolicy: cfg_like_crawl,
            }
        )
        
        # ✅ get_policy_name() 헬퍼로 하드코딩 제거
        self._cfg_like_webdriver_manager = extracted[
            SectionExtractor.get_policy_name(WebDriverManagerPolicy)
        ]
        self._cfg_like_crawl = extracted[
            SectionExtractor.get_policy_name(SyncCrawlPolicy)
        ]
        
        # ========================================
        # SyncCrawlPolicy 생성 (통합 정책 - 로깅 설정 추출용)
        # ========================================
        try:
            self.policy = SyncCrawlPolicy(**merged_config)
        except Exception:
            # merged_config가 비어있거나 유효하지 않으면 기본값 사용
            self.policy = SyncCrawlPolicy()  # type: ignore
        
        # ========================================
        # Logger 설정 (Parent logger만 관리, 개별 모듈은 자체 생성)
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
        
        self.log.debug("SyncCrawl adapter initialized (parent logger only)")
    
    def run(
        self,
        urls: Union[str, List[str]],
        **overrides
    ) -> List[Dict[str, Any]]:
        """URL 크롤링 실행 (OTO 패턴)
        
        Pipeline Flow:
            1. Preset 적용 (정책 레벨 preset → **overrides로 오버라이드 가능)
            2. URL 분석
            3. CrawlPolicy 결정 (URL 분석 기반 Preset > fallback)
            4. WebDriverManager 설정 구성
            5. Pipeline 실행: WebDriver → Navigate → Extract → PostProcess
        
        Args:
            urls: 크롤링할 URL (단일 또는 리스트)
            **overrides: 런타임 오버라이드 (KeyPath 형식, 모듈 접두사 포함)
                예: preset="taobao_fast"  # 정책 preset 오버라이드
                    webdriver_manager__provider="chrome"  # provider override
                    webdriver_manager__region="china"
                    crawl__site="aliexpress"
                    cas_no="CAS2024-001"  # PostProcessor 템플릿 변수
        
        Returns:
            크롤링 결과 리스트
        
        Example:
            >>> # 정책 기본값 사용 (provider="firefox", region="global")
            >>> crawl = SyncCrawl(cfg_like=config.to_dict(), log_manager=log_manager)
            >>> results = crawl.run(urls=["https://aliexpress.com/item/123.html"])
            >>> 
            >>> # provider/region override
            >>> results = crawl.run(
            ...     urls=["https://taobao.com/item/456.htm"],
            ...     webdriver_manager__provider="chrome",  # ✅ **overrides로 통일
            ...     webdriver_manager__region="china",
            ...     preset="taobao_fast",
            ...     cas_no="CAS2024-001"
            ... )
        
        Note:
            ⚠️ provider는 WebDriverManagerPolicy.provider 기본값("firefox") 사용.
            ⚠️ **overrides로 provider/region 오버라이드 가능 (webdriver_manager__ 접두사).
            ⚠️ 모듈별 override는 접두사로 구분 (webdriver_manager__, crawl__).
            ⚠️ 접두사 없는 override는 PostProcessor 템플릿 변수로 사용 (cas_no, batch_id 등).
        """
        from cfg_utils.services import filter_overrides_by_prefix
        from cfg_utils.services.section_extractor import SectionExtractor
        from crawl_utils.provider.policy import WebDriverManagerPolicy
        
        # ========================================
        # Step 0: Runtime Overrides 준비 (v2.0)
        # ========================================
        runtime_overrides = overrides.copy()
        
        # URL 정규화
        if isinstance(urls, str):
            urls = [urls]
        
        all_results = []
        
        for url in urls:
            try:
                # ========================================
                # Step 1: URL 분석
                # ========================================
                site, method, region = analyze_url(url)
                self.log.info(f"Analyzed URL: {url} → {site}/{method} (region={region})")
                
                # ========================================
                # Step 2: SyncCrawlPolicy 결정 (Deep Merge: YAML < Preset < Override) v2.0
                # ========================================
                # Priority: Policy Default < YAML Data < Preset < Runtime Override
                
                # ⚠️ crawl__ 접두사 override 적용
                crawl_overrides = filter_overrides_by_prefix(
                    runtime_overrides,
                    f"{SectionExtractor.get_policy_name(SyncCrawlPolicy)}__"
                )
                
                # 1. Base: YAML Data (cfg_like_crawl)
                base_dict = self._cfg_like_crawl if isinstance(self._cfg_like_crawl, dict) else {}
                
                # 2. Preset 로드 (URL 기반)
                preset_dict = get_preset(site, method)
                
                # 3. Deep Merge: YAML < Preset < Override
                from keypath_utils import KeyPathDict
                merged_kp = KeyPathDict(base_dict.copy())
                
                if preset_dict:
                    self.log.info(f"✅ Loaded Preset: {site}/{method}")
                    merged_kp.merge(preset_dict, deep=True)  # YAML + Preset
                else:
                    self.log.warning(f"⚠️  No preset for ({site}, {method}), using YAML data only")
                
                # 4. Runtime Override 적용 (최우선)
                merged_kp.merge(crawl_overrides, deep=True)
                merged_dict = merged_kp.data
                
                # 5. site/method 추가 (URL 분석 결과)
                merged_dict["site"] = site
                merged_dict["method"] = method
                
                # 6. SyncCrawlPolicy 생성
                try:
                    crawl_policy = SyncCrawlPolicy(**merged_dict)
                    self.log.debug(f"SyncCrawlPolicy created: scroll={merged_dict.get('scroll', {}).get('strategy', 'none')}")
                except Exception as e:
                    self.log.error(f"❌ Failed to create SyncCrawlPolicy: {e}")
                    self.log.debug(f"merged_dict keys: {list(merged_dict.keys())}")
                    # Fallback: 기본값만 사용
                    crawl_policy = SyncCrawlPolicy(site=site, method=method)
                
                # ========================================
                # Step 3: WebDriver 설정 구성 (직접 전달)
                # ========================================
                # ⚠️ webdriver_manager__ 접두사 override 적용
                webdriver_overrides = filter_overrides_by_prefix(
                    runtime_overrides,
                    f"{SectionExtractor.get_policy_name(WebDriverManagerPolicy)}__"
                )
                
                # provider 추출 (override > Policy 기본값 "firefox")
                provider = webdriver_overrides.get("provider", "firefox")
                
                # region/provider 기반 override 병합
                self.log.debug(f"🔍 Getting webdriver override: region={region}, provider={provider}")
                preset_override = get_webdriver_override(region, provider)
                self.log.debug(f"🔍 preset_override result: {preset_override}")
                
                if preset_override:                    
                    provider_fields = PROVIDER_SPECIFIC_FIELDS.get(provider, [])
                    
                    for key, value in preset_override.items():
                        # Provider 전용 필드는 provider__ prefix 추가
                        if key in provider_fields:
                            override_key = f"{provider}__{key}"
                        else:
                            # 공통 필드는 prefix 없이 사용
                            override_key = key
                        
                        webdriver_overrides[override_key] = value
                        self.log.debug(f"  ✅ Override: {override_key} = {value}")
                    
                    self.log.info(f"✅ Applied preset override for {region}/{provider}")
                else:
                    self.log.warning(f"⚠️ No preset override found for {region}/{provider}")
                
                # URL 분석에서 추출한 region과 provider를 override로 추가
                webdriver_overrides["region"] = region
                webdriver_overrides["provider"] = provider
                                
                # ========================================
                # Step 5: Pipeline 실행
                # ========================================
                result = self._execute(url, crawl_policy, webdriver_overrides)
                all_results.append(result)
                
            except Exception as e:
                self.log.error(f"Failed: {url} - {e}")
                import traceback
                self.log.debug(traceback.format_exc())
                all_results.append({"url": url, "error": str(e), "success": False})
        
        return all_results
    
    def _execute(
        self,
        url: str,
        crawl_policy: SyncCrawlPolicy,
        webdriver_overrides: Dict[str, Any],
        **overrides
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
            crawl_policy: SyncCrawlPolicy (정책)
            webdriver_overrides: WebDriver override dict (region, provider 포함)
        """
        webdriver_manager = None
        session_bridge = None

        try:
            # ========================================
            # WebDriver 시작 (cfg_like + overrides 직접 전달)
            # ========================================
            provider = webdriver_overrides.get("provider", "firefox")
            self.log.info(f"Starting WebDriver (provider={provider})")
            
            # WebDriverManager에 직접 전달 (OTO 패턴)
            # - self._cfg_like_webdriver_manager: 기본 설정 (SectionExtractor로 추출)
            # - webdriver_overrides: URL 분석 결과 + 런타임 override (region, provider 포함)
            webdriver_manager = WebDriverManager(
                cfg_like=self._cfg_like_webdriver_manager,  # type: ignore
                log_manager=self._parent_log_manager,
                **webdriver_overrides
            )
            webdriver_manager.start()
            
            # SyncSeleniumAdapter로 래핑
            adapter = SyncSeleniumAdapter(driver=webdriver_manager._webdriver)
            session_bridge_policy = crawl_policy.session_bridge
            http_session_policy = crawl_policy.http_session
            cookie_bridge_policy = crawl_policy.cookie_bridge

            if session_bridge_policy or http_session_policy or cookie_bridge_policy:
                try:
                    from ..services.session_bridge import SessionBridge

                    webdriver_for_bridge = adapter._drv
                    accept_language = getattr(webdriver_manager.config, "accept_languages", None)
                    user_agent = (
                        session_bridge_policy.user_agent
                        if session_bridge_policy and session_bridge_policy.user_agent
                        else getattr(webdriver_manager.config, "user_agent", None)
                    )
                    proxy = session_bridge_policy.proxy if session_bridge_policy else None

                    session_bridge = SessionBridge.from_webdriver(
                        webdriver=webdriver_for_bridge,
                        user_agent=user_agent,
                        accept_language=accept_language,
                        proxy=proxy,
                    )
                    self.log.debug("Session bridge initialized")
                except Exception as bridge_exc:
                    session_bridge = None
                    self.log.warning(f"Failed to initialize session bridge: {bridge_exc}")


            # Navigator로 페이지 로드
            self.log.info(f"Loading: {url}")
            navigator = SyncNavigator(driver=adapter, policy=crawl_policy.navigation)
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

            if session_bridge:
                parsed = urlparse(url)
                sync_targets: List[str] = []
                if parsed.hostname:
                    sync_targets.append(parsed.hostname)
                if cookie_bridge_policy and cookie_bridge_policy.cookie_sync_domains:
                    sync_targets.extend(cookie_bridge_policy.cookie_sync_domains)

                for domain in sync_targets:
                    try:
                        session_bridge.sync_cookies_from_webdriver(domain)
                        self.log.debug(f"Synced cookies for domain: {domain}")
                    except Exception as sync_exc:
                        self.log.debug(f"Cookie sync failed for {domain}: {sync_exc}")

                session_bridge.ensure_headers(referer=url, default_referer=url)


            # ========================================
            # Step 6: Pipeline 실행 (Extract → ItemPostProcessor → PostProcessor)
            # ========================================
            self.log.info("Extracting data")
            extractor_factory = SyncExtractorFactory(adapter=adapter, policy=crawl_policy.extractor)
            extractor = extractor_factory.create()
            
            # extract_list() 사용 (List[Dict] 반환)
            extracted_data = extractor.extract_list()
            
            self.log.info(f"  Extracted: {len(extracted_data)} records")
            
            # 🔍 디버깅: 추출된 데이터 구조 확인
            if extracted_data:
                import json
                sample = extracted_data[0] if isinstance(extracted_data, list) else extracted_data
                self.log.debug(f"  Sample extracted data: {json.dumps(sample, ensure_ascii=False, indent=2)[:500]}...")
            
            # ItemPostProcessor 실행 (규칙 기반 처리)
            normalized_items = []
            if crawl_policy.save:
                self.log.info(f"Processing items ({len(crawl_policy.save)} rules)")
                from ..services.Item_Post_Processor import ItemPostProcessor
                
                try:
                    processor = ItemPostProcessor(rules=crawl_policy.save)
                    
                    # v7.0: runtime_context/env_context 제거됨
                    normalized_items = processor.process(extracted_data=extracted_data)
                    self.log.success(f"  Processed: {len(normalized_items)} items")
                except Exception as e:
                    self.log.error(f"  Processing failed: {e}")
                    import traceback
                    self.log.debug(traceback.format_exc())
            
            # PostProcessor 실행 (파일 저장)
            saved_files = []
            save_summary = None
            
            if normalized_items:
                self.log.info(f"Saving items ({len(normalized_items)} items)")
                from ..services.Item_Saver import SyncItemSaver
                from ..services.fetcher import SyncHTTPFetcher
                
                try:
                    saver = SyncItemSaver()
                    fetcher_kwargs: Dict[str, Any] = {}

                    if http_session_policy:
                        fetcher_kwargs.update(
                            {
                                "timeout": http_session_policy.timeout_read_sec,
                                "timeout_connect": http_session_policy.timeout_connect_sec,
                                "timeout_read": http_session_policy.timeout_read_sec,
                                "allow_redirects": http_session_policy.allow_redirects,
                                "stream_download": http_session_policy.stream_download,
                                "reuse_session": http_session_policy.reuse,
                            }
                        )

                    fetcher = SyncHTTPFetcher(
                        session=session_bridge.http_session if session_bridge else None,
                        **fetcher_kwargs,
                    )
                    
                    save_summary = saver.save_items(normalized_items, fetcher=fetcher)
                    
                    # SaveSummary에서 경로 수집
                    saved_files = [
                        str(artifact.path) 
                        for artifact in save_summary.flatten() 
                        if artifact.status == "saved"
                    ]
                    self.log.success(f"  Saved: {len(saved_files)} files")
                    
                except Exception as e:
                    self.log.error(f"  Saving failed: {e}")
                    import traceback
                    self.log.debug(traceback.format_exc())
                    
            if save_summary:
                # SaveSummary에서 경로 수집
                saved_files = [str(artifact.path) for artifact in save_summary.flatten()]
                self.log.success(f"  Saved: {len(saved_files)} files")
                    
            return {
                "url": url,
                "site": crawl_policy.site,
                "method": crawl_policy.method,
                "data": extracted_data,
                "normalized_items": normalized_items,
                "saved_files": saved_files,
                "success": True
            }
        
        except Exception as e:
            self.log.error(f"Execution failed: {e}")
            return {"url": url, "error": str(e), "success": False}
        
        finally:
            if webdriver_manager:
                # ✅ 크롤링 성공 시 실제 UA 추출 및 캐시 저장
                try:
                    if webdriver_manager._webdriver:
                        # execute_script는 WebDriver의 메서드 (타입 체크 우회)
                        actual_ua = webdriver_manager._webdriver.execute_script("return navigator.userAgent;")  # type: ignore
                        
                        if actual_ua:
                            from pathlib import Path
                            import json
                            from datetime import datetime, timezone
                            import re
                            
                            # 캐시 파일 경로
                            cache_path = Path(__file__).parent.parent / "configs" / "browser_version.json"
                            
                            # Firefox 버전 추출 (예: "Firefox/150.0")
                            version_match = re.search(r'Firefox/(\d+\.\d+)', actual_ua)
                            version = version_match.group(1) if version_match else "unknown"
                            
                            cache_path.parent.mkdir(parents=True, exist_ok=True)
                            cache_data = {
                                "firefox": {
                                    "user_agent": actual_ua,
                                    "version": version,
                                    "updated_at": datetime.now(timezone.utc).isoformat(),
                                    "source": "runtime_extraction"
                                }
                            }
                            cache_path.write_text(
                                json.dumps(cache_data, indent=2, ensure_ascii=False), 
                                encoding="utf-8"
                            )
                            self.log.debug(f"✅ Extracted and cached actual UA: Firefox/{version}")
                except Exception as e:
                    self.log.debug(f"Failed to extract/cache actual UA: {e}")
                
                # WebDriver 종료
                self.log.info("Closing WebDriver")
                webdriver_manager.quit()


__all__ = ["SyncCrawl"]
