# -*- coding: utf-8 -*-
"""crawl_utils.adapter.sync_crawl
==================================

SyncCrawl Adapter - URL 기반 동기 크롤링 (High-Level Orchestrator)

Architecture (v8.0):
1. SyncCrawl (High-Level):
   - URL 분석 및 preset_policy 준비
   - WebDriverManager 관리 (시작/종료)
   - SessionBridge 설정
   - SyncPipeline 호출

2. SyncPipeline (Core Service):
   - Navigator → Extractor → ItemNormalizer → PresetNormalizer
   - → merge → Runtime Override → ItemTransformer → ItemSaver

통합 정책 사용:
- SyncCrawlPolicy: WebDriverManagerPolicy + CrawlPolicy + preset 통합

Preset 사용 (v8.0):
- preset_policy: Site별 preset (Python 함수 기반)
  * presets/sites/aliexpress_full.py: get_aliexpress_detail_preset()
  * URL 기반 자동 선택
- overrides: 런타임 override 값

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
    >>> # run() - URL 기반 자동 preset 선택
    >>> results = crawl.run(
    ...     urls=["https://aliexpress.com/item/123.html"]
    ... )
    >>> # → _prepare_preset() 자동 호출 → get_aliexpress_detail_preset()
    >>> 
    >>> # run() - overrides 적용
    >>> results = crawl.run(
    ...     urls=["https://aliexpress.com/item/123.html"],
    ...     webdriver_manager__provider="chrome",  # WebDriver override
    ...     product__images__fso_name__prefix="CUSTOM"  # ItemSaver override
    ... )
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel

from logs_utils import LogManager
from keypath_utils import KeyPathDict

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
from ..services.preset_policy_normalizer import PresetPolicyNormalizer


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
        ...     cfg_like_sync_crawl={"site": "aliexpress"},  # 개별 cfg_like (우선순위 1)
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
        cfg_like_sync_crawl: Union[BaseModel, Path, str, dict, None] = None,
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
            cfg_like_sync_crawl: CrawlPolicy 개별 설정 (우선순위 1)
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
            ...     cfg_like_sync_crawl={"site": "aliexpress"},  # 개별 cfg_like (우선순위 1)
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
                SyncCrawlPolicy: cfg_like_sync_crawl,
            }
        )
        
        # ✅ get_policy_name() 헬퍼로 하드코딩 제거
        self._cfg_like_webdriver_manager = extracted[
            SectionExtractor.get_policy_name(WebDriverManagerPolicy)
        ]
        self._cfg_like_sync_crawl = extracted[  
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
        
        # self.log.debug("SyncCrawl adapter initialized (parent logger only)")

        # 각 Adapter는 lazy-load (첫 process() 호출 시 초기화)
        self._webdriver_manager: Optional[WebDriverManager] = None
        
        # ✅ Phase 2: WebDriver Pool (동일 설정 재사용)
        self._webdriver_pool: Dict[str, WebDriverManager] = {}
        
        # ✅ Context Manager: Pool 수동 관리 플래그
        self._manual_pool_management = False

    # ==========================================================================
    # Context Manager (WebDriver Pool 수동 관리)
    # ==========================================================================
    
    def __enter__(self):
        """컨텍스트 매니저 진입: Pool 수동 관리 모드 활성화
        
        Example:
            >>> with sync_crawl:  # Pool cleanup 연기
            ...     for url in urls:
            ...         sync_crawl.run([url])  # 브라우저 재사용
            ... # __exit__에서 Pool cleanup
        """
        self._manual_pool_management = True
        self.log.info("♻️ WebDriver Pool: Manual management enabled")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료: Pool cleanup 수행"""
        self._manual_pool_management = False
        self._cleanup_webdriver_pool()
        self.log.info("🧹 WebDriver Pool: Cleaned up")
        return False  # Exception을 재발생시킴

    # ==========================================================================
    # Adapter Lazy Loading (with log_manager injection)
    # ==========================================================================
    
    @property
    def webdriver_manager(self) -> WebDriverManager:
        """WebDriverManager Adapter lazy-loading.
        
        cfg_like는 SectionExtractor로 이미 추출됨 (self._cfg_like_we).
        """
        if self._webdriver_manager is None:
            self._webdriver_manager = WebDriverManager(
                cfg_like=self._cfg_like_webdriver_manager,  # type: ignore
                log_manager=self._parent_log_manager,
            )
        return self._webdriver_manager

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
        """
        from cfg_utils.services import filter_overrides_by_prefix
        from cfg_utils.services.section_extractor import SectionExtractor
        from crawl_utils.provider.policy import WebDriverManagerPolicy
        
        # URL 정규화
        if isinstance(urls, str):
            urls = [urls]
        
        all_results = []
        
        # ✅ Phase 2: WebDriver Pool 관리 (try-finally로 cleanup 보장)
        try:
            for url in urls:
                try:
                    # ========================================
                    # Step 1: URL 분석 및 preset 준비
                    # ========================================
                    site, method, region = analyze_url(url)
                    self.log.info(f"Analyzed URL: {url} → {site}/{method} (region={region})")
                    
                    # preset_policy 준비 (URL 기반) - get_preset() 호출
                    preset_policy = get_preset(site, method)
                    if preset_policy:
                        self.log.info(f"✅ Loaded preset: {site}/{method}")
                    else:
                        self.log.warning(f"⚠️ No preset for {site}/{method}, using YAML data only")
                    
                    # ========================================
                    # Step 2: SyncCrawlPolicy 결정 (Deep Merge: YAML < Preset < Override)
                    # ========================================
                    # Priority: Policy Default < YAML Data < Preset < Runtime Override
                    
                    # ⚠️ crawl__ 접두사 override 적용
                    crawl_overrides_flat = filter_overrides_by_prefix(
                        overrides,
                        f"{SectionExtractor.get_policy_name(SyncCrawlPolicy)}__"
                    )
                    
                    # 1. Base: YAML Data (cfg_like_sync_crawl)
                    base_dict = self._cfg_like_sync_crawl if isinstance(self._cfg_like_sync_crawl, dict) else {}
                    
                    # 2. Deep Merge: YAML < Preset (배열은 전체 덮어쓰기)
                    from keypath_utils import KeyPathDict
                    merged_kp = KeyPathDict(base_dict.copy())
                    
                    if preset_policy:
                        merged_kp.merge(preset_policy, deep=True)  # YAML + Preset
                    
                    # 3. Runtime Override 적용
                    # ✅ to_nested_dict()가 items[0]__dir_path 패턴 자동 처리
                    for flat_key, flat_value in crawl_overrides_flat.items():
                        nested_override = KeyPathDict.to_nested_dict({flat_key: flat_value})
                        
                        # 배열 override는 merge_array() 사용
                        if "items" in nested_override and isinstance(nested_override["items"], list):
                            merged_kp.merge_array(nested_override, key="items", strategy="update")
                        else:
                            # Non-array override: use merge
                            merged_kp.merge(nested_override, deep=True)
                    
                    merged_kp.drop_blanks()
                    merged_dict = merged_kp.data

                    # 4. site/method/region 추가 (URL 분석 결과)
                    merged_dict["site"] = site
                    merged_dict["method"] = method
                    
                    # 5. SyncCrawlPolicy 생성
                    try:
                        crawl_policy = SyncCrawlPolicy(**merged_dict)
                        # self.log.debug(f"SyncCrawlPolicy created: scroll={merged_dict.get('scroll', {}).get('strategy', 'none')}")
                    except Exception as e:
                        self.log.error(f"❌ Failed to create SyncCrawlPolicy: {e}")
                        self.log.warning(f"⏭️  Skipping URL due to invalid policy: {url}")
                        all_results.append({
                            "url": url,
                            "error": f"Invalid SyncCrawlPolicy: {e}",
                            "success": False
                        })
                        continue  # ✅ WebDriver 시작 안하고 다음 URL로
                    
                    # ========================================
                    # Step 3: WebDriver 설정 구성 및 Pool 관리
                    # ========================================
                    # ⚠️ webdriver_manager__ 접두사 override 적용
                    webdriver_overrides = filter_overrides_by_prefix(
                        overrides,
                        f"{SectionExtractor.get_policy_name(WebDriverManagerPolicy)}__"
                    )
                    
                    # provider 추출 (override > Policy 기본값 "firefox")
                    provider = webdriver_overrides.get("provider", "firefox")
                    
                    # region/provider 기반 override 병합
                    # self.log.debug(f"🔍 Getting webdriver override: region={region}, provider={provider}")
                    preset_override = get_webdriver_override(region, provider)
                    # self.log.debug(f"🔍 preset_override result: {preset_override}")
                    
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
                            # self.log.debug(f"  ✅ Override: {override_key} = {value}")
                        
                        self.log.info(f"✅ Applied preset override for {region}/{provider}")
                    else:
                        self.log.warning(f"⚠️ No preset override found for {region}/{provider}")
                    
                    # URL 분석에서 추출한 region과 provider를 override로 추가
                    webdriver_overrides["region"] = region
                    webdriver_overrides["provider"] = provider
                    
                    # ✅ Phase 2: WebDriver Pool Key 생성 및 재사용
                    accept_languages = webdriver_overrides.get("accept_languages")
                    profile_path = webdriver_overrides.get(f"{provider}__profile_path")
                    
                    pool_key = self._get_webdriver_key(
                        provider=provider,
                        region=region,
                        accept_languages=accept_languages,
                        profile_path=profile_path
                    )
                    
                    # Pool에서 조회 또는 생성
                    if pool_key in self._webdriver_pool:
                        webdriver_manager = self._webdriver_pool[pool_key]
                        self.log.info(f"♻️ Reusing WebDriver from pool: {pool_key}")
                    else:
                        # 새 WebDriver 생성
                        webdriver_manager = WebDriverManager(
                            cfg_like=self._cfg_like_webdriver_manager,
                            log_manager=self._parent_log_manager,
                            **webdriver_overrides
                        )
                        webdriver_manager.start()  # ✅ 시작 (UA 캐싱 포함)
                        self._webdriver_pool[pool_key] = webdriver_manager
                        self.log.info(f"🆕 Created new WebDriver in pool: {pool_key}")
                                    
                    # ========================================
                    # Step 4: Pipeline 실행 (webdriver_manager 전달)
                    # ========================================
                    result = self._execute(
                        url=url,
                        crawl_policy=crawl_policy,
                        webdriver_manager=webdriver_manager,  # ✅ Pool에서 전달
                        preset_policy=preset_policy or {},  # ✅ None 처리
                        **overrides  # ✅ overrides 전달
                    )
                    all_results.append(result)
                    
                except Exception as e:
                    self.log.error(f"Failed: {url} - {e}")
                    import traceback
                    # self.log.debug(traceback.format_exc())
                    all_results.append({"url": url, "error": str(e), "success": False})
        
        finally:
            # ✅ Phase 2: Pool cleanup (컨텍스트 매니저 사용 시 skip)
            if not self._manual_pool_management:
                self._cleanup_webdriver_pool()
        
        return all_results
    
    def _prepare_preset_item_policy(
        self,
        preset_policy: Dict[str, Any],
        crawl_policy: SyncCrawlPolicy
    ) -> KeyPathDict:
        """Preset item policy 준비 (우선순위: crawl_policy.items > preset_policy > empty)
        
        Args:
            preset_policy: Site별 preset dict (Python 함수 기반)
            crawl_policy: SyncCrawlPolicy (YAML + Preset + Runtime Override 적용됨)
        
        Returns:
            KeyPathDict: Normalized preset item policy
        
        Priority:
            1. crawl_policy.items: Runtime Override 반영된 최종 정책 ✅ **최우선**
            2. preset_policy (Python 함수): get_aliexpress_detail_preset() 등
            3. empty: KeyPathDict({})
        
        Example:
            >>> # Case 1: crawl_policy.items 우선 (Runtime Override 반영)
            >>> result = self._prepare_preset_item_policy(preset, crawl_policy)
            
            >>> # Case 2: preset_policy fallback
            >>> result = self._prepare_preset_item_policy(preset, SyncCrawlPolicy())
            
            >>> # Case 3: empty
            >>> result = self._prepare_preset_item_policy({}, SyncCrawlPolicy())
        """
        preset_normalizer = PresetPolicyNormalizer()
        preset_item_policy_kp = KeyPathDict({})
        
        # ✅ Priority 1: crawl_policy.items (Runtime Override 반영됨)
        if hasattr(crawl_policy, 'items') and crawl_policy.items:
            # Convert list of Pydantic models to dicts
            items_src = crawl_policy.items
            if isinstance(items_src, list):
                normalized_list = []
                for it in items_src:
                    if hasattr(it, 'model_dump'):
                        normalized_list.append(it.model_dump())
                    elif hasattr(it, 'dict'):
                        normalized_list.append(it.dict())
                    else:
                        normalized_list.append(it)
                preset_item_policy_kp = preset_normalizer.normalize({'items': normalized_list})
            elif isinstance(items_src, dict):
                preset_item_policy_kp = preset_normalizer.normalize(items_src)
            # self.log.debug(f"✅ Using crawl_policy.items: {len(preset_item_policy_kp.data)} keys")
        
        # ✅ Priority 2: preset_policy fallback (crawl_policy.items 없을 때만)
        elif preset_policy:
            preset_item_policy_kp = preset_normalizer.normalize(preset_policy)
            # self.log.debug(f"✅ Using preset_policy: {len(preset_item_policy_kp.data)} keys")
        else:
            pass
            # self.log.debug("⚠️ No preset items available (empty)")
        
        return preset_item_policy_kp
    
    def _execute(
        self,
        url: str,
        crawl_policy: SyncCrawlPolicy,
        webdriver_manager: WebDriverManager,  # ✅ Phase 2: Pool에서 전달받기
        preset_policy: Dict[str, Any],  # ✅ preset_policy 직접 받기 (중복 제거)
        **overrides: Dict[str, Any]  # ✅ overrides 전달
    ) -> Dict[str, Any]:
        """Pipeline 실행: WebDriver (Pool에서 받기) → SyncPipeline
        
        Architecture (Phase 2):
        1. WebDriverManager: run()에서 Pool 관리 → _execute()로 전달받기
           - ✅ 시작/종료 로직 제거 (run()이 관리)
           - ✅ 동일 설정 = WebDriver 재사용
        2. SessionBridge: Cookie/Header 동기화 (선택적)
        3. HTTP Session: SessionBridge를 통해 ItemSaver로 전달
        4. SyncPipeline: 완전한 크롤링 파이프라인
           - Navigator → Extractor → ItemNormalizer → PresetNormalizer
           - → merge → Runtime Override → ItemTransformer → ItemSaver
        
        Args:
            url: 크롤링할 URL (source)
            crawl_policy: SyncCrawlPolicy (정책)
            webdriver_manager: WebDriverManager (Pool에서 전달, 이미 시작됨)
            preset_policy: Site별 preset dict (run()에서 이미 로드됨)
            overrides: 런타임 override dict
        
        Note:
            ✅ URL 분석 및 preset 로드는 run()에서 수행 (중복 제거)
            ✅ WebDriver 시작/종료는 run()에서 수행 (Pool 관리)
            ✅ finally 블록에서 SessionBridge cleanup만 수행
        """
        session_bridge = None

        try:
            # ========================================
            # Step 1: WebDriver는 Pool에서 전달받음 (시작 로직 제거)
            # ========================================
            # ✅ webdriver_manager는 이미 run()에서 start() 완료
            self.log.info(f"Using WebDriver from pool for URL: {url}")
            
            # ========================================
            # Step 2: Adapter 생성 (SessionBridge와 Navigator에서 공유)
            # ========================================
            adapter = SyncSeleniumAdapter(driver=webdriver_manager._webdriver)
            
            # ========================================
            # Step 3: SessionBridge 초기화 (선택적)
            # ========================================
            session_bridge_policy = crawl_policy.session_bridge
            http_session_policy = crawl_policy.http_session

            if http_session_policy:  # ✅ 단순화: http_session_policy만 체크
                try:
                    from ..services.session_bridge import SessionBridge

                    webdriver_for_bridge = adapter._drv
                    accept_language = getattr(webdriver_manager.config, "accept_languages", None)
                    user_agent = getattr(webdriver_manager.config, "user_agent", None)
                    # ✅ proxy는 session_bridge_policy에서 가져오기 (HttpSessionPolicy가 아님)
                    proxy = session_bridge_policy.proxy if session_bridge_policy else None

                    session_bridge = SessionBridge.from_webdriver(
                        webdriver=webdriver_for_bridge,
                        user_agent=user_agent,
                        accept_language=accept_language,
                        proxy=proxy,
                    )
                    # self.log.debug("✅ Session bridge initialized")
                except Exception as bridge_exc:
                    session_bridge = None
                    self.log.warning(f"Failed to initialize session bridge: {bridge_exc}")

            # ========================================
            # Step 4: Inline pipeline (deprecated SyncPipeline) - perform flow here
            #  - Navigate -> Extract -> ItemsNormalizer -> ItemSaver
            # This avoids the indirection and allows session reuse and simpler overrides.
            # ========================================
            from ..services.items_normalizer import ItemsNormalizer
            from ..services.item_saver import SyncItemSaver

            # ✅ Navigator (Adapter 재사용)
            navigator = SyncNavigator(adapter, crawl_policy.navigation)

            # 1) Navigate / scroll / wait (same behavior as old pipeline)
            navigator.load(url)

            if crawl_policy.scroll and crawl_policy.scroll.strategy != "none":
                navigator.scroll(
                    strategy=crawl_policy.scroll.strategy,
                    max_scrolls=crawl_policy.scroll.max_scrolls,
                    pause_sec=crawl_policy.scroll.scroll_pause_sec,
                    scroll_count=crawl_policy.scroll.scroll_count,
                    step_px=crawl_policy.scroll.scroll_step_px,
                )

            if crawl_policy.wait and crawl_policy.wait.hook != "none":
                navigator.wait(
                    hook=crawl_policy.wait.hook,
                    selector=crawl_policy.wait.selector,
                    timeout=crawl_policy.wait.timeout_sec,
                    condition=crawl_policy.wait.condition,
                )

            # ========================================
            # Phase 2: Extract (JS Execution → Flattened KeyPath Records)
            # ========================================
            # Extractor returns List[Dict] with nested structures
            # We flatten them here using KeyPathDict.from_nested_dict()
            #   Nested dict: {"product": {"title": "..."}} → {"product__title": "..."}
            #   List[dict]: [{"url": "...", "name": "Red"}] → {"url": [...], "name": [...]}
            # Result: List[Dict[str, Any]] with flat KeyPath keys
            extractor = SyncExtractorFactory(adapter, crawl_policy.extractor).create()
            dom = navigator.get_dom() if hasattr(navigator, 'get_dom') else ""
            
            # Prefer extract_list (canonicalized List[Dict])
            if callable(getattr(extractor, 'extract_list', None)):
                extracted_records = extractor.extract_list(dom=dom)
            elif callable(getattr(extractor, 'extract', None)):
                extracted_records = extractor.extract(dom=dom)
            else:
                # Fallback to any callable 'run' implementation
                run_callable = getattr(extractor, 'run', None)
                if callable(run_callable):
                    extracted_records = run_callable()
                else:
                    extracted_records = []
            
            # ✅ Flatten nested structures to KeyPath format
            # Use KeyPathDict.from_nested_dict() (static method, 13/13 tests passed)
            # Get separator from crawl_policy (default: "__")
            separator = getattr(crawl_policy, 'keypath_separator', '__')
            
            flattened_records = []
            for rec in extracted_records:
                if isinstance(rec, dict):
                    # Convert nested dict to flat KeyPath dict
                    # from_nested_dict returns Dict[str, Any] directly
                    flat_rec = KeyPathDict.from_nested_dict(rec, separator=separator)
                    flattened_records.append(flat_rec)
                else:
                    flattened_records.append(rec)
            
            # self.log.debug(f"✅ Extractor output: {len(extracted_records)} records → {len(flattened_records)} flattened (separator='{separator}')")

            # ========================================
            # Phase 3: Prepare Preset Items (KeyPathDict)
            # ========================================
            # Priority: preset_policy > crawl_policy.items > empty
            # Result: KeyPathDict with flat KeyPath structure
            preset_item_policy_kp = self._prepare_preset_item_policy(
                preset_policy=preset_policy,
                crawl_policy=crawl_policy
            )
            # self.log.debug(f"[SyncCrawl] Flattened data: {flattened_records}")
            # self.log.debug(f"[SyncCrawl] Preset items policy: {preset_item_policy_kp}")

            # ========================================
            # Phase 4: ItemsNormalizer (Merge → Resolve → Explode → Transform)
            # ========================================
            # Flow:
            #   1. Merge: flattened_records (runtime) < preset_items (policy)
            #   2. Explode: Convert field arrays to individual items
            #   3. Transform: Apply ItemNormalizer per item
            # Input: List[Dict] (flat KeyPath) + KeyPathDict (flat KeyPath)
            # Output: List[CrawlItem] (structured Pydantic models)
            items_normalizer = ItemsNormalizer()
            items = items_normalizer.process(
                extracted_records=flattened_records,  # ✅ Use flattened data
                preset_item_policy=preset_item_policy_kp
            )
            
            self.log.info(f"✅ ItemsNormalizer output: {len(items)} items")

            # 5) Save items (SessionBridge 직접 전달)
            item_saver = SyncItemSaver()
            http_session = session_bridge.http_session if session_bridge else None
            summary = item_saver.save_items(items, http_session=http_session)

            # 6) Return result (shape similar to previous PipelineResult)
            return {
                "url": url,
                "site": crawl_policy.site,
                "method": crawl_policy.method,
                "data": extracted_records,
                "normalized_items": items,
                "saved_files": [str(artifact.path) for artifact in summary.flatten() if artifact.status == "saved"],
                "success": True,
            }
        
        except Exception as e:
            self.log.error(f"Execution failed: {e}")
            import traceback
            # self.log.debug(traceback.format_exc())
            return {"url": url, "error": str(e), "success": False}
        
        finally:
            # ✅ Cleanup: SessionBridge HTTP Session close
            if session_bridge:
                try:
                    session_bridge.http_session.close()
                    # self.log.debug("✅ SessionBridge HTTP session closed")
                except Exception as cleanup_exc:
                    pass
                    # self.log.debug(f"Failed to close HTTP session: {cleanup_exc}")
            
            # ✅ Phase 2: WebDriver 종료는 run()에서 관리 (_cleanup_webdriver_pool)
            # WebDriver는 Pool에 남아있어 다른 URL에서 재사용 가능
    
    # ==========================================================================
    # WebDriver Pool Management (Phase 2)
    # ==========================================================================
    
    def _get_webdriver_key(
        self,
        provider: str,
        region: str,
        accept_languages: Optional[str] = None,
        profile_path: Optional[str] = None
    ) -> str:
        """WebDriver Pool Key 생성 (presets.webdrivers 기반)
        
        동일한 설정 = 동일한 Key = WebDriver 재사용
        다른 설정 = 다른 Key = 새 WebDriver 생성
        
        Key 구성 요소 (우선순위):
        1. profile_path: **가장 중요** - Cookie/Login 상태 격리
        2. provider: firefox, chrome, edge
        3. region: global, china (presets.webdrivers.WEBDRIVER_OVERRIDES 참조)
        4. accept_languages: presets에서 region/provider별 자동 매핑
        
        Args:
            provider: WebDriver provider (firefox, chrome, edge)
            region: 지역 코드 (global, china)
            accept_languages: 명시적 Accept-Language 설정 (선택적)
            profile_path: Firefox Profile 경로 (선택적, **가장 중요**)
        
        Returns:
            Pool Key 문자열 (예: "firefox_china_CRAWL_CHINA_zh-CN,zh;q=0.9")
        
        Example:
            >>> # Case 1: presets 자동 매핑
            >>> key1 = self._get_webdriver_key("firefox", "china", None, None)
            >>> # "firefox_china_CRAWL_CHINA_zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
            >>> 
            >>> # Case 2: 명시적 설정
            >>> key2 = self._get_webdriver_key(
            ...     "firefox", "china", 
            ...     "ja-JP,ja;q=0.9",
            ...     "M:/WEB_PROFILE/CRAWL_JAPAN"
            ... )
            >>> # "firefox_china_CRAWL_JAPAN_ja-JP,ja;q=0.9"
        
        Note:
            ⚠️ Profile이 가장 중요! 없으면 모든 것이 막힘
            ⚠️ presets.webdrivers.WEBDRIVER_OVERRIDES 기반 매핑
            ⚠️ region/provider 조합 없으면 fallback
        """
        from ..presets.webdrivers import WEBDRIVER_OVERRIDES
        
        # ========================================
        # Step 1: Accept-Language 결정
        # ========================================
        if accept_languages:
            # 명시적 설정 우선
            al_key = accept_languages
        else:
            # presets에서 region/provider별 매핑 조회
            region_overrides = WEBDRIVER_OVERRIDES.get(region, {})
            provider_overrides = region_overrides.get(provider, {})
            al_key = provider_overrides.get("accept_languages", "en-US,en;q=0.9")
        
        # ========================================
        # Step 2: Profile 식별자 결정 (가장 중요!)
        # ========================================
        if profile_path:
            # 명시적 설정 우선
            from pathlib import Path
            profile_key = Path(profile_path).name
        else:
            # presets에서 region/provider별 매핑 조회
            region_overrides = WEBDRIVER_OVERRIDES.get(region, {})
            provider_overrides = region_overrides.get(provider, {})
            
            # provider별 필드명 다름
            if provider == "firefox":
                preset_profile = provider_overrides.get("profile_path")
            elif provider == "chrome":
                preset_profile = provider_overrides.get("user_data_dir")
            else:
                preset_profile = None
            
            if preset_profile:
                from pathlib import Path
                profile_key = Path(preset_profile).name
            else:
                # ⚠️ Profile 없음 → 경고
                profile_key = "none"
                self.log.warning(f"⚠️ No profile for {region}/{provider} - Cookie/Login may fail!")
        
        # ========================================
        # Step 3: Pool Key 생성
        # ========================================
        # 우선순위: Profile > Provider > Region > Accept-Language
        pool_key = f"{provider}_{region}_{profile_key}_{al_key}"
        
        return pool_key
    
    def _cleanup_webdriver_pool(self):
        """WebDriver Pool 정리 (모든 WebDriver 종료)
        
        run() 메서드 종료 시 호출되어 Pool의 모든 WebDriver를 안전하게 종료합니다.
        
        동작:
        1. Pool의 모든 WebDriver에 대해 quit() 호출
        2. 예외 발생 시에도 계속 진행 (다른 WebDriver 종료)
        3. Pool 딕셔너리 초기화
        
        Note:
            - finally 블록 역할 (Pool 버전)
            - 개별 URL 실패해도 모든 WebDriver 정리 보장
        
        Example:
            >>> try:
            ...     for url in urls:
            ...         result = self._execute(url, webdriver_manager)
            ... finally:
            ...     self._cleanup_webdriver_pool()
        """
        for pool_key, manager in self._webdriver_pool.items():
            try:
                self.log.info(f"🔄 Closing WebDriver from pool: {pool_key}")
                manager.quit()
            except Exception as e:
                self.log.error(f"❌ Failed to quit WebDriver {pool_key}: {e}")
        
        self._webdriver_pool.clear()
        self.log.info("✅ WebDriver pool cleaned up")


__all__ = ["SyncCrawl"]
