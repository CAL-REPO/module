# -*- coding: utf-8 -*-
# crawl_utils/provider/firefox.py
# Firefox WebDriver - Pure Logic (ImageLoad 패턴)

from __future__ import annotations

import shutil
from typing import Optional
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from .policy import WebDriverManagerPolicy


class FirefoxWebDriver:
    """
    Firefox WebDriver - 순수 로직만 담당 (ImageLoad 패턴)
    
    설계 원칙:
    - 설정 로딩은 WebDriverManager가 담당
    - FirefoxWebDriver는 Policy만 받아서 WebDriver 생성
    
    Args:
        config (WebDriverManagerPolicy): WebDriver Manager 정책 객체
    
    Example:
        >>> from crawl_utils.adapter import WebDriverManager
        >>> 
        >>> # WebDriverManager가 설정 로딩 + provider 선택
        >>> with WebDriverManager("configs/webdriver_china.yaml") as manager:
        ...     manager.driver.get("https://taobao.com")
        ...     print(manager.driver.title)
    """
    
    def __init__(self, config: WebDriverManagerPolicy):
        """
        Initialize Firefox WebDriver with Policy.
        
        Args:
            config (WebDriverPolicy): WebDriver 정책 객체
        
        Raises:
            ValueError: Firefox configuration이 없을 때
        """
        if not config.firefox:
            raise ValueError(
                "Firefox configuration is required. "
                "Ensure 'firefox' section exists in WebDriverPolicy."
            )
        
        self.config = config
        self._driver: Optional[webdriver.Firefox] = None
        
        # Logger 초기화
        self._init_logger()
    
    def _init_logger(self):
        """Logger 초기화 (logs_utils 또는 기본 로거)"""
        try:
            from logs_utils import LogManager
            if self.config.log_config:
                self.logger = LogManager(self.config.log_config).logger
            else:
                self.logger = LogManager({"enabled": False}).logger
        except (ImportError, AttributeError):
            import logging
            self.logger = logging.getLogger("FirefoxWebDriver")
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(
                    logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    )
                )
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
    
    def start(self):
        """
        Start Firefox WebDriver.
        
        Raises:
            RuntimeError: WebDriver가 이미 실행 중일 때
            FileNotFoundError: geckodriver를 찾을 수 없을 때
        """
        if self._driver is not None:
            raise RuntimeError("WebDriver is already started.")
        
        self.logger.info("Starting Firefox WebDriver...")
        
        # Firefox Options 설정
        options = self._configure_options()
        
        # geckodriver 경로 확인
        driver_path = self._get_driver_path()
        
        # WebDriver 생성
        service = Service(executable_path=driver_path)
        self._driver = webdriver.Firefox(service=service, options=options)
        
        # ✅ Stealth Mode 강제 적용: JavaScript로 navigator.webdriver 제거
        try:
            self._driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.logger.debug("✅ navigator.webdriver forcefully removed via JavaScript")
        except Exception as e:
            self.logger.warning(f"Failed to remove navigator.webdriver: {e}")
        
        # Window size 설정
        if self.config.window_size:
            w, h = self.config.window_size
            self._driver.set_window_size(w, h)
            self.logger.info(f"Window size set to {w}x{h}")
        
        self.logger.info("Firefox WebDriver started successfully.")
    
    def quit(self):
        """
        Quit Firefox WebDriver.
        
        안전하게 WebDriver를 종료합니다.
        """
        if self._driver is not None:
            try:
                self.logger.info("Quitting Firefox WebDriver...")
                self._driver.quit()
                self.logger.info("Firefox WebDriver quit successfully.")
            except Exception as e:
                self.logger.error(f"Error while quitting WebDriver: {e}")
            finally:
                self._driver = None
    
    @property
    def driver(self) -> webdriver.Firefox:
        """
        Get Selenium WebDriver instance.
        
        Returns:
            webdriver.Firefox: Selenium WebDriver 인스턴스
        
        Raises:
            RuntimeError: WebDriver가 시작되지 않았을 때
        """
        if self._driver is None:
            raise RuntimeError(
                "WebDriver not started. Call start() first or use as context manager."
            )
        return self._driver
    
    def _configure_options(self) -> Options:
        """
        Configure Firefox options.
        
        Returns:
            Options: Firefox Options 객체
        """
        options = Options()
        firefox_cfg = self.config.firefox
        
        # Binary path
        if firefox_cfg.binary_path:
            options.binary_location = str(firefox_cfg.binary_path)
            self.logger.info(f"Firefox binary: {firefox_cfg.binary_path}")
        
        # Profile path
        if firefox_cfg.profile_path:
            options.add_argument(f"-profile")
            options.add_argument(str(firefox_cfg.profile_path))
            self.logger.info(f"Firefox profile: {firefox_cfg.profile_path}")
        
        # Headless mode
        if self.config.headless:
            options.add_argument("--headless")
            self.logger.info("Headless mode enabled")
        
        # ✅ Stealth Mode: navigator.webdriver 제거 (Bot 탐지 회피)
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        # ✅ 추가: Automation 확장 비활성화
        options.set_preference("devtools.jsonview.enabled", False)
        self.logger.info("✅ Stealth mode enabled: navigator.webdriver disabled")
        
        # ✅ User-Agent 3단계 Fallback: 명시적 설정 → 자동 감지 → 캐시 로드 → 예외
        ua = self.config.user_agent
        
        # 기본값(rv:144.0) 또는 비어있으면 자동 감지 시도
        if not ua or "rv:144.0" in ua:
            from pathlib import Path
            import json
            from datetime import datetime, timezone
            
            # 캐시 파일 경로
            cache_path = Path(__file__).parent.parent / "configs" / "browser_version.json"
            
            # Step 1: 자동 감지
            try:
                from crawl_utils.provider.browser_version import get_firefox_version, build_user_agent
                
                current_version = get_firefox_version()
                if current_version:
                    ua = build_user_agent("firefox", current_version)
                    self.logger.info(f"✅ Auto-detected UA: Firefox/{current_version}")
                    
                    # 캐시 저장 (자동 감지 성공 시)
                    try:
                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        cache_data = {
                            "firefox": {
                                "user_agent": ua,
                                "version": current_version,
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                                "source": "auto_detection"
                            }
                        }
                        cache_path.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False), encoding="utf-8")
                        self.logger.debug(f"Cached UA to: {cache_path}")
                    except Exception as e:
                        self.logger.warning(f"Failed to cache UA: {e}")
                else:
                    # Step 2: 캐시 로드 (자동 감지 실패 시)
                    if cache_path.exists():
                        try:
                            cache_data = json.loads(cache_path.read_text(encoding="utf-8"))
                            cached_ua = cache_data.get("firefox", {}).get("user_agent")
                            cached_version = cache_data.get("firefox", {}).get("version")
                            
                            if cached_ua:
                                ua = cached_ua
                                self.logger.warning(
                                    f"⚠️ Auto-detection failed, loaded cached UA: Firefox/{cached_version}"
                                )
                            else:
                                raise ValueError("Invalid cache format")
                        except Exception as e:
                            self.logger.error(f"Failed to load cached UA: {e}")
                            # Step 3: 예외 발생 (캐시 로드 실패)
                            raise RuntimeError(
                                "Failed to detect Firefox version and load cached UA.\n"
                                "Using outdated default UA (rv:144.0) may cause server-side bot detection.\n\n"
                                "Please fix one of the following:\n"
                                "  1. Ensure Firefox is installed in default location\n"
                                "     - C:\\Program Files\\Mozilla Firefox\\firefox.exe\n"
                                "     - C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe\n"
                                "  2. Set explicit user_agent in config YAML:\n"
                                "     webdriver_manager:\n"
                                "       user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0'\n"
                                "  3. Run PowerShell with administrator privileges\n"
                                "  4. Check PowerShell execution policy: Get-ExecutionPolicy\n"
                                f"  5. Fix cache file: {cache_path}"
                            )
                    else:
                        # Step 3: 예외 발생 (캐시 파일 없음)
                        raise RuntimeError(
                            "Failed to detect Firefox version and no cached UA found.\n"
                            "Using outdated default UA (rv:144.0) may cause server-side bot detection.\n\n"
                            "Please fix one of the following:\n"
                            "  1. Ensure Firefox is installed in default location\n"
                            "     - C:\\Program Files\\Mozilla Firefox\\firefox.exe\n"
                            "     - C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe\n"
                            "  2. Set explicit user_agent in config YAML:\n"
                            "     webdriver_manager:\n"
                            "       user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0'\n"
                            "  3. Run PowerShell with administrator privileges\n"
                            "  4. Check PowerShell execution policy: Get-ExecutionPolicy"
                        )
            except RuntimeError:
                raise  # Re-raise RuntimeError
            except Exception as e:
                # 기타 예외 발생 시에도 중단
                raise RuntimeError(
                    f"Failed to configure Firefox User-Agent: {e}\n\n"
                    "Please set explicit user_agent in config YAML:\n"
                    "  webdriver_manager:\n"
                    "    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0'"
                ) from e
        
        if ua:
            options.set_preference("general.useragent.override", ua)
            self.logger.info(f"User-Agent: {ua}")
        
        # Accept-Languages
        if self.config.accept_languages:
            options.set_preference("intl.accept_languages", self.config.accept_languages)
            self.logger.info(f"Accept-Languages: {self.config.accept_languages}")
        
        return options
    
    def _get_driver_path(self) -> str:
        """
        Get geckodriver executable path.
        
        Returns:
            str: geckodriver 경로
        
        Raises:
            FileNotFoundError: geckodriver를 찾을 수 없을 때
        """
        firefox_cfg = self.config.firefox
        
        # 1. 설정에서 지정한 경로
        if firefox_cfg.driver_path:
            driver_path = str(firefox_cfg.driver_path)
            self.logger.info(f"Using specified driver path: {driver_path}")
            return driver_path
        
        # 2. System PATH에서 찾기
        driver_path = shutil.which("geckodriver")
        if driver_path:
            self.logger.info(f"Found geckodriver in PATH: {driver_path}")
            return driver_path
        
        # 3. 찾지 못함
        raise FileNotFoundError(
            "geckodriver not found. Please:\n"
            "1. Install geckodriver: https://github.com/mozilla/geckodriver/releases\n"
            "2. Add to PATH or specify 'driver_path' in config\n"
            "3. Example: firefox.driver_path = 'M:/geckodriver.exe'"
        )
    
    def __enter__(self):
        """Context Manager enter."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Context Manager exit."""
        self.quit()
        return False
    
    def __repr__(self):
        """String representation."""
        status = "running" if self._driver is not None else "stopped"
        return f"<FirefoxWebDriver status={status} region={self.config.region}>"
