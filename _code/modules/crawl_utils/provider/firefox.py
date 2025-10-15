# -*- coding: utf-8 -*-
# crawl_utils/provider/firefox.py
# Firefox WebDriver implementation using BaseWebDriver pattern

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Optional, Union
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from pydantic import BaseModel
from cfg_utils import ConfigLoader
from crawl_utils.provider.base import BaseWebDriver
from crawl_utils.core.policy import FirefoxPolicy


class FirefoxWebDriver(BaseWebDriver[FirefoxPolicy]):
    """Firefox WebDriver 구현체
    
    BaseWebDriver를 상속받아 Firefox 전용 WebDriver를 구현합니다.
    ConfigLoader 패턴을 따르며, 설정 기반 초기화를 지원합니다.
    
    Example:
        >>> # YAML 파일에서 로드
        >>> driver = FirefoxWebDriver("configs/firefox.yaml")
        >>> driver.driver.get("https://example.com")
        
        >>> # dict로 직접 설정
        >>> driver = FirefoxWebDriver({"headless": True, "window_size": (1920, 1080)})
        
        >>> # Context manager 사용
        >>> with FirefoxWebDriver("configs.yaml") as driver:
        ...     driver.driver.get("https://example.com")
    """
    
    # ==========================================================================
    # Abstract Method Implementations (BaseWebDriver 요구사항)
    # ==========================================================================
    
    def _load_config(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, list, None],
        *,
        policy_overrides: Optional[dict] = None,
        **overrides: Any
    ) -> FirefoxPolicy:
        """FirefoxPolicy 로드
        
        Args:
            cfg_like: 설정 소스 (FirefoxPolicy, YAML 경로, dict 등)
            policy_overrides: ConfigPolicy 필드 개별 오버라이드 (merge_mode, yaml.source_paths 등)
            **overrides: 런타임 오버라이드
        
        Returns:
            로드된 FirefoxPolicy 인스턴스
        """
        if cfg_like is None:
            default_path = Path(__file__).parent.parent / "configs" / "firefox.yaml"
            if policy_overrides is None:
                policy_overrides = {}
            
            # ConfigLoader 정책 파일 지정
            policy_overrides.setdefault("config_loader_path",
                str(Path(__file__).parent.parent / "configs" / "config_loader_firefox.yaml"))
            
            # 데이터 파일 + 섹션 지정
            policy_overrides.setdefault("yaml.source_paths", {
                "path": str(default_path),
                "section": "firefox"
            })
        
        return ConfigLoader.load(
            cfg_like,
            model=FirefoxPolicy,
            policy_overrides=policy_overrides,
            **overrides
        )
    
    def _create_driver(self) -> webdriver.Firefox:
        """Firefox WebDriver 인스턴스 생성
        
        Returns:
            생성된 selenium.webdriver.Firefox 인스턴스
        """
        opts = self._configure_options()
        exe = self._get_driver_path()
        
        self.logger.info("Launching Firefox WebDriver")
        return webdriver.Firefox(service=Service(executable_path=exe), options=opts)
    
    def _configure_options(self) -> Options:
        """Firefox 옵션 설정
        
        config를 기반으로 Firefox Options를 구성합니다.
        
        Returns:
            구성된 selenium.webdriver.firefox.options.Options 인스턴스
        """
        cfg = self.config
        opts = Options()
        
        # Binary path
        if cfg.binary_path:
            opts.binary_location = str(cfg.binary_path)
            self.logger.debug(f"Set binary path: {cfg.binary_path}")
        
        # Profile path
        if cfg.profile_path:
            opts.add_argument("-profile")
            opts.add_argument(str(cfg.profile_path))
            self.logger.debug(f"Using Firefox profile: {cfg.profile_path}")
        
        # Headless mode
        if cfg.headless:
            opts.add_argument("--headless")
        
        # Window size
        if cfg.window_size:
            w, h = cfg.window_size
            opts.add_argument(f"--width={w}")
            opts.add_argument(f"--height={h}")
        
        # Session headers (세션 파일에서 로드)
        headers = self._load_session_headers()
        
        if headers:
            self.logger.debug("Restoring headers from session file")
            if "User-Agent" in headers:
                opts.set_preference("general.useragent.override", headers["User-Agent"])
            if "Accept-Language" in headers:
                opts.set_preference("intl.accept_languages", headers["Accept-Language"])
        else:
            # 설정에서 헤더 적용
            if cfg.accept_languages:
                opts.set_preference("intl.accept_languages", cfg.accept_languages)
            if cfg.user_agent:
                opts.set_preference("general.useragent.override", cfg.user_agent)
        
        # Firefox 전용 설정
        if cfg.disable_automation:
            opts.set_preference("dom.webdriver.enabled", False)
        else:
            opts.set_preference("dom.webdriver.enabled", cfg.dom_enabled)
        
        opts.set_preference("privacy.resistFingerprinting", cfg.resist_fingerprint_enabled)
        
        return opts
    
    def _extract_headers(self) -> dict:
        """브라우저에서 헤더 추출
        
        현재 Firefox 세션에서 User-Agent, Accept-Language 등을 추출합니다.
        
        Returns:
            헤더 딕셔너리
        """
        if not self._driver:
            return {}
        
        try:
            ua = self._driver.execute_script("return navigator.userAgent")
            langs = self._driver.execute_script("return navigator.languages")
            return {
                "User-Agent": ua,
                "Accept-Language": ",".join(langs) if langs else None,
            }
        except Exception as e:
            self.logger.warning(f"Failed to extract headers: {e}")
            return {}
    
    # ==========================================================================
    # Firefox-specific Methods
    # ==========================================================================
    
    def _get_driver_path(self) -> str:
        """GeckoDriver 실행 파일 경로 확인
        
        1. config.driver_path 우선 사용
        2. 시스템 PATH에서 geckodriver 검색
        3. webdriver-manager로 자동 다운로드 (use_webdriver_manager=True인 경우)
        
        Returns:
            GeckoDriver 실행 파일 경로
        """
        # 1. 명시적 경로
        if self.config.driver_path:
            return str(self.config.driver_path)
        
        # 2. 시스템 PATH 검색
        if shutil.which("geckodriver"):
            return "geckodriver"
        
        # 3. webdriver-manager 사용
        if self.config.use_webdriver_manager:
            try:
                from webdriver_manager.firefox import GeckoDriverManager
                return GeckoDriverManager().install()
            except ImportError:
                self.logger.warning("webdriver-manager not installed, falling back to 'geckodriver'")
                return "geckodriver"
        
        # 기본값
        return "geckodriver"
