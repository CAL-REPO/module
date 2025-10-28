# -*- coding: utf-8 -*-
# crawl_utils/adapter/webdriver_manager.py
# WebDriver Manager - ImageLoad 패턴

from __future__ import annotations

from pathlib import Path
from typing import Any, Union, Optional

from pydantic import BaseModel

from cfg_utils.services import ConfigLikeLoader
from logs_utils import LogManager
from crawl_utils.provider.policy import WebDriverManagerPolicy
from crawl_utils.provider.firefox import FirefoxWebDriver
# from crawl_utils.provider.chrome import ChromeWebDriver  # 미래


class WebDriverManager:
    """WebDriver Manager (ImageLoad 패턴)
    
    책임:
    1. WebDriverManagerPolicy 로드 (ConfigLikeLoader 사용)
    2. provider 필드에 따라 적절한 WebDriver 선택
    3. Context Manager 지원
    
    이 클래스는 설정 로딩과 WebDriver 선택을 담당합니다.
    실제 WebDriver 로직은 FirefoxWebDriver, ChromeWebDriver 등이 처리합니다.
    
    ConfigLikeLoader 사용:
    - Policy.name 필드로 자동 section 추출 ("webdriver_manager")
    - SectionExtractor.get_policy_name(WebDriverManagerPolicy) 사용
    
    Example:
        >>> # YAML 파일에서 로드 (Policy.name = "webdriver_manager" 자동 인식)
        >>> with WebDriverManager("configs/webdriver_china.yaml") as manager:
        ...     manager.driver.get("https://taobao.com")
        ...     print(manager.driver.title)
        
        >>> # dict로 직접 설정
        >>> manager = WebDriverManager({
        ...     "provider": "firefox",
        ...     "region": "china",
        ...     "firefox": {
        ...         "profile_path": "M:/Firefox_Profile/CRAWL_CHINA",
        ...         "use_webdriver_manager": True
        ...     }
        ... })
        >>> manager.start()
        >>> manager.driver.get("https://taobao.com")
        >>> manager.quit()
        
        >>> # WebDriverManagerPolicy 인스턴스로 직접 생성
        >>> from crawl_utils.provider.policy import WebDriverManagerPolicy
        >>> policy = WebDriverManagerPolicy(provider="firefox", ...)
        >>> manager = WebDriverManager(policy)
        
        >>> # SyncCrawl에서 사용 (OTO 패턴)
        >>> # SectionExtractor가 자동으로 Policy.name으로 추출
        >>> wd_manager = WebDriverManager(
        ...     cfg_like=self._cfg_like_webdriver_manager,  # SectionExtractor로 추출
        ...     log_manager=self._parent_log_manager,
        ...     region="china",  # **overrides
        ...     provider="firefox"
        ... )
    """
    
    def __init__(
        self,
        cfg_like: Union[WebDriverManagerPolicy, Path, str, dict, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """WebDriverManager 초기화
        
        Args:
            cfg_like: WebDriverManagerPolicy, YAML 경로, dict 등
            log_manager: LogManager 인스턴스 (선택사항, ImageLoad 패턴)
            **overrides: 런타임 오버라이드
        """
        # 1. ConfigLikeLoader로 WebDriverManagerPolicy 로드
        self.config = self._load_config(cfg_like, **overrides)
        
        # 2. LogManager 초기화 (ImageLoad 패턴)
        if log_manager:
            self.log = log_manager.logger
        elif self.config.log_config:
            self.log = LogManager(self.config.log_config).logger
        else:
            self.log = LogManager({"enabled": False}).logger
        
        self.log.debug("WebDriverManager initialized")
        
        # 3. provider에 따라 WebDriver 선택
        self._webdriver = self._create_webdriver()
    
    def _load_config(self, cfg_like, **overrides) -> WebDriverManagerPolicy:
        """Load WebDriverManagerPolicy from various sources.
        
        ConfigLikeLoader가 모든 경우를 처리:
        1. Policy 인스턴스 → 그대로 반환
        2. Path/str → ConfigLoader로 YAML 로드
        3. dict → ConfigLoader로 파싱 (Policy.name section 자동 추출)
        4. None → 기본 YAML 또는 Pydantic 기본값
        
        Args:
            cfg_like: WebDriverManagerPolicy instance, YAML path, dict, or None
            **overrides: Runtime overrides
        
        Returns:
            WebDriverManagerPolicy instance
        """
        return ConfigLikeLoader.load(
            cfg_like=cfg_like,
            policy_class=WebDriverManagerPolicy,
            module_file=__file__,
            config_filename="webdriver_manager.yaml",
            **overrides
        )  # type: ignore
    
    def _create_webdriver(self):
        """provider에 따라 WebDriver 생성
        
        Returns:
            FirefoxWebDriver, ChromeWebDriver 등
        
        Raises:
            ValueError: 지원하지 않는 provider
            NotImplementedError: 아직 구현되지 않은 provider
        """
        provider = self.config.provider.lower()
        self.log.debug(f"Creating WebDriver for provider: {provider}")
        
        if provider == "firefox":
            self.log.info(f"Initializing Firefox WebDriver (region: {self.config.region})")
            return FirefoxWebDriver(self.config)
        elif provider == "chrome":
            # return ChromeWebDriver(self.config)
            self.log.error("Chrome WebDriver not implemented yet")
            raise NotImplementedError(
                "Chrome WebDriver not implemented yet. "
                "Use provider='firefox' for now."
            )
        elif provider == "edge":
            # return EdgeWebDriver(self.config)
            self.log.error("Edge WebDriver not implemented yet")
            raise NotImplementedError(
                "Edge WebDriver not implemented yet. "
                "Use provider='firefox' for now."
            )
        else:
            self.log.error(f"Unsupported provider: {provider}")
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported providers: firefox (chrome, edge - coming soon)"
            )
    
    @property
    def driver(self):
        """Selenium WebDriver 인스턴스 접근
        
        Returns:
            selenium.webdriver.Firefox 또는 Chrome 등
        
        Raises:
            RuntimeError: WebDriver가 시작되지 않은 경우
        """
        return self._webdriver.driver
    
    # ==========================================================================
    # Context Manager 지원
    # ==========================================================================
    
    def __enter__(self):
        """with 문 진입 시 WebDriver 시작
        
        Returns:
            self (WebDriverAdapter 인스턴스)
        """
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """with 문 종료 시 WebDriver 정리
        
        예외가 발생해도 반드시 WebDriver를 종료합니다.
        
        Args:
            exc_type: 예외 타입
            exc_value: 예외 값
            traceback: 트레이스백
        
        Returns:
            False (예외를 전파)
        """
        self.quit()
        return False  # 예외 전파
    
    # ==========================================================================
    # Public Methods
    # ==========================================================================
    
    def start(self):
        """WebDriver 시작
        
        내부적으로 선택된 WebDriver의 start() 메서드를 호출합니다.
        시작 후 실제 User-Agent를 추출하여 캐시에 저장합니다.
        """
        self.log.info(f"Starting WebDriver ({self.config.provider}, region={self.config.region})")
        self._webdriver.start()
        self.log.info("WebDriver started successfully")
        
        # ✅ 실제 User-Agent 추출 및 캐시 저장 (항상 실행)
        self._cache_user_agent()
    
    def quit(self):
        """WebDriver 종료
        
        내부적으로 선택된 WebDriver의 quit() 메서드를 호출합니다.
        """
        self.log.info(f"Quitting WebDriver ({self.config.provider})")
        self._webdriver.quit()
        self.log.info("WebDriver quit successfully")
    
    # ==========================================================================
    # Private Methods
    # ==========================================================================
    
    def _cache_user_agent(self):
        """실제 User-Agent 추출 및 캐시 저장 (항상 실행)
        
        WebDriver 시작 후 실제 브라우저의 User-Agent를 추출하여
        browser_version.json 캐시 파일에 저장합니다.
        
        캐시 구조:
        {
            "firefox": {
                "user_agent": "Mozilla/5.0 ...",
                "version": "150.0",
                "updated_at": "2025-10-28T12:34:56.789Z",
                "source": "runtime_extraction"
            }
        }
        
        실패 시 경고 로그만 출력하고 계속 진행합니다.
        """
        try:
            if not self._webdriver or not self._webdriver.driver:
                self.log.warning("WebDriver not available for UA extraction")
                return
            
            # 실제 User-Agent 추출
            actual_ua = self.driver.execute_script("return navigator.userAgent;")
            
            if not actual_ua:
                self.log.warning("Failed to extract User-Agent: empty result")
                return
            
            from pathlib import Path
            import json
            from datetime import datetime, timezone
            import re
            
            # 캐시 파일 경로
            cache_path = Path(__file__).parent.parent / "configs" / "browser_version.json"
            
            # Provider별 버전 추출
            provider = self.config.provider.lower()
            version = "unknown"
            
            if provider == "firefox":
                # Firefox 버전 추출 (예: "Firefox/150.0")
                version_match = re.search(r'Firefox/(\d+\.\d+)', actual_ua)
                version = version_match.group(1) if version_match else "unknown"
            elif provider == "chrome":
                # Chrome 버전 추출 (예: "Chrome/120.0.6099.109")
                version_match = re.search(r'Chrome/(\d+\.\d+)', actual_ua)
                version = version_match.group(1) if version_match else "unknown"
            elif provider == "edge":
                # Edge 버전 추출 (예: "Edg/120.0.6099.109")
                version_match = re.search(r'Edg/(\d+\.\d+)', actual_ua)
                version = version_match.group(1) if version_match else "unknown"
            
            # 캐시 데이터 생성
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_data = {
                provider: {
                    "user_agent": actual_ua,
                    "version": version,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "source": "runtime_extraction"
                }
            }
            
            # 기존 캐시 읽기 (다른 provider 데이터 보존)
            if cache_path.exists():
                try:
                    existing_data = json.loads(cache_path.read_text(encoding="utf-8"))
                    existing_data.update(cache_data)
                    cache_data = existing_data
                except Exception as read_exc:
                    self.log.warning(f"Failed to read existing cache: {read_exc}")
            
            # 캐시 파일 저장
            cache_path.write_text(
                json.dumps(cache_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            
            self.log.info(f"✅ User-Agent cached: {provider}/{version}")
        
        except Exception as e:
            self.log.warning(f"Failed to cache User-Agent: {e}")
    
    # ==========================================================================
    # Properties
    # ==========================================================================
    
    @property
    def provider(self) -> str:
        """현재 사용 중인 WebDriver provider"""
        return self.config.provider
    
    @property
    def region(self) -> str:
        """현재 설정의 region"""
        return self.config.region


__all__ = ['WebDriverManager']
