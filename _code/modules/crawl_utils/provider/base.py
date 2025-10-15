# -*- coding: utf-8 -*-
# crawl_utils/provider/base.py
# Base WebDriver abstract class with ConfigLoader pattern integration

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, Union, Generic, TypeVar, TYPE_CHECKING
from pathlib import Path

from pydantic import BaseModel

if TYPE_CHECKING:
    from cfg_utils import ConfigLoader, ConfigPolicy
    from structured_io import json_fileio
else:
    try:
        from cfg_utils import ConfigLoader, ConfigPolicy
    except ImportError:
        ConfigLoader = None  # type: ignore
        ConfigPolicy = None  # type: ignore
    
    try:
        from structured_io import json_fileio
    except ImportError:
        json_fileio = None  # type: ignore


T = TypeVar('T', bound=BaseModel)


class BaseWebDriver(ABC, Generic[T]):
    """WebDriver 공통 베이스 클래스
    
    모든 WebDriver 구현체는 이 클래스를 상속받아 구현합니다.
    ConfigLoader 패턴을 사용하여 설정을 로드하며, 공통 기능(세션 관리, 로깅 등)을 제공합니다.
    
    Type Parameters:
        T: WebDriverPolicy 또는 그 서브클래스
    
    Example:
        >>> class FirefoxWebDriver(BaseWebDriver[FirefoxPolicy]):
        ...     def _load_config(self, cfg_like, **kwargs):
        ...         # Implementation
        ...         pass
        ...     
        ...     def _create_driver(self):
        ...         # Implementation
        ...         pass
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, list, None] = None,
        *,
        policy_overrides: Optional[dict] = None,
        **overrides: Any
    ):
        """ConfigLoader와 동일한 인자 패턴으로 초기화
        
        Args:
            cfg_like: BaseModel, YAML 경로, dict, 또는 YAML 경로 리스트
                - BaseModel: Policy 인스턴스를 직접 전달
                - str/Path: 단일 YAML 파일 경로
                - list[str/Path]: 여러 YAML 파일 (순서대로 병합)
                - dict: 설정 딕셔너리
                - None: 기본 설정 파일 사용
            policy_overrides: ConfigPolicy 필드 개별 오버라이드 (merge_mode, yaml.source_paths 등)
            **overrides: 런타임 오버라이드 값
        
        Example:
            >>> # YAML 파일에서 로드
            >>> driver = FirefoxWebDriver("configs/firefox.yaml")
            
            >>> # 여러 파일 병합
            >>> driver = FirefoxWebDriver(
            ...     ["base.yaml", "override.yaml"],
            ...     policy_overrides={"merge_mode": "deep"}
            ... )
            
            >>> # dict로 직접 설정
            >>> driver = FirefoxWebDriver({"headless": True})
            
            >>> # 런타임 오버라이드
            >>> driver = FirefoxWebDriver("config.yaml", headless=True, window_size=(1920, 1080))
        """
        self.config: T = self._load_config(cfg_like, policy_overrides=policy_overrides, **overrides)
        self._driver: Optional[Any] = None
        self._logging_active = False
        self._context_managed = False
        self._setup_logging()
    
    # ==========================================================================
    # Abstract Methods (구현 필수)
    # ==========================================================================
    
    @abstractmethod
    def _load_config(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, list, None],
        *,
        policy_overrides: Optional[dict] = None,
        **overrides: Any
    ) -> T:
        """설정 로드 (각 provider가 구현)
        
        ConfigLoader를 사용하여 설정을 로드하고 해당 Policy 모델로 변환합니다.
        
        Args:
            cfg_like: 설정 소스
            policy_overrides: ConfigPolicy 필드 개별 오버라이드 (merge_mode, yaml.source_paths 등)
            **overrides: 런타임 오버라이드
        
        Returns:
            로드된 Policy 인스턴스
        
        Example Implementation:
            >>> def _load_config(self, cfg_like, *, policy_overrides=None, **overrides):
            ...     if cfg_like is None:
            ...         default_path = Path(__file__).parent.parent / "configs" / "firefox.yaml"
            ...         if policy_overrides is None:
            ...             policy_overrides = {}
            ...         
            ...         policy_overrides.setdefault("config_loader_path",
            ...             str(Path(__file__).parent.parent / "configs" / "config_loader_firefox.yaml"))
            ...         
            ...         policy_overrides.setdefault("yaml.source_paths", {
            ...             "path": str(default_path),
            ...             "section": "firefox"
            ...         })
            ...     
            ...     return ConfigLoader.load(cfg_like, model=FirefoxPolicy,
            ...                            policy_overrides=policy_overrides, **overrides)
        """
        pass
    
    @abstractmethod
    def _create_driver(self) -> Any:
        """WebDriver 인스턴스 생성 (각 provider가 구현)
        
        브라우저별 WebDriver 인스턴스를 생성하고 반환합니다.
        
        Returns:
            생성된 WebDriver 인스턴스 (selenium.webdriver.Firefox 등)
        
        Example Implementation:
            >>> def _create_driver(self):
            ...     opts = self._configure_options()
            ...     service = Service(executable_path=self._get_driver_path())
            ...     return webdriver.Firefox(service=service, options=opts)
        """
        pass
    
    @abstractmethod
    def _configure_options(self) -> Any:
        """브라우저 옵션 설정 (각 provider가 구현)
        
        config를 기반으로 브라우저 옵션 객체를 생성합니다.
        
        Returns:
            브라우저 옵션 객체 (selenium Options)
        
        Example Implementation:
            >>> def _configure_options(self):
            ...     opts = Options()
            ...     if self.config.headless:
            ...         opts.add_argument("--headless")
            ...     if self.config.window_size:
            ...         w, h = self.config.window_size
            ...         opts.add_argument(f"--width={w}")
            ...         opts.add_argument(f"--height={h}")
            ...     return opts
        """
        pass
    
    @abstractmethod
    def _extract_headers(self) -> dict:
        """브라우저에서 헤더 추출 (각 provider가 구현)
        
        현재 브라우저 세션에서 User-Agent, Accept-Language 등을 추출합니다.
        
        Returns:
            헤더 딕셔너리
        
        Example Implementation:
            >>> def _extract_headers(self):
            ...     try:
            ...         ua = self._driver.execute_script("return navigator.userAgent")
            ...         langs = self._driver.execute_script("return navigator.languages")
            ...         return {
            ...             "User-Agent": ua,
            ...             "Accept-Language": ",".join(langs) if langs else None,
            ...         }
            ...     except Exception:
            ...         return {}
        """
        pass
    
    # ==========================================================================
    # Concrete Methods (공통 구현)
    # ==========================================================================
    
    @property
    def driver(self) -> Any:
        """Lazy driver creation
        
        처음 접근 시에만 드라이버를 생성합니다.
        
        Returns:
            WebDriver 인스턴스
        """
        if self._driver is None:
            self.logger.debug("Creating WebDriver instance...")
            self._driver = self._create_driver()
            self._post_create()
        return self._driver
    
    def quit(self):
        """WebDriver 종료
        
        WebDriver를 종료하고 리소스를 정리합니다.
        """
        if self._driver:
            try:
                self._driver.quit()
                self.logger.info(f"{self.__class__.__name__} terminated.")
            except Exception as e:
                self.logger.warning(f"Error during quit: {e}")
            finally:
                self._driver = None
        
        if not self._context_managed:
            self._stop_logging()
    
    # ==========================================================================
    # Session Management (공통 로직)
    # ==========================================================================
    
    def _load_session_headers(self) -> dict:
        """세션 헤더 로드 (공통)
        
        저장된 세션 파일에서 헤더를 읽어옵니다.
        
        Returns:
            헤더 딕셔너리
        """
        if not hasattr(self.config, 'session_path') or not hasattr(self.config, 'save_session'):
            return {}
        
        path = self.config.session_path
        if not path or not self.config.save_session:
            return {}
        
        if json_fileio is None:
            self.logger.warning("structured_io not available, session loading disabled")
            return {}
        
        try:
            io = json_fileio(str(path))
            data = io.read()
            headers = data.get("headers", {})
            self.logger.debug(f"Loaded session headers from {path}")
            return headers
        except Exception as e:
            self.logger.warning(f"Failed to load session: {e}")
            return {}
    
    def _save_session_headers(self):
        """세션 헤더 저장 (공통)
        
        현재 브라우저 세션의 헤더를 파일에 저장합니다.
        """
        if not hasattr(self.config, 'session_path') or not hasattr(self.config, 'save_session'):
            return
        
        if not self.config.session_path or not self.config.save_session:
            return
        
        if not self._driver:
            return
        
        if json_fileio is None:
            self.logger.warning("structured_io not available, session saving disabled")
            return
        
        try:
            headers = self._extract_headers()
            if not headers:
                return
            
            path = Path(self.config.session_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            io = json_fileio(str(path))
            
            # 기존 데이터 로드 (있다면)
            try:
                data = io.read()
            except Exception:
                data = {}
            
            # 헤더 업데이트
            data["headers"] = {**data.get("headers", {}), **headers}
            io.write(data)
            
            self.logger.debug(f"Saved session headers to {path}")
        except Exception as e:
            self.logger.warning(f"Failed to save session: {e}")
    
    def _post_create(self):
        """드라이버 생성 후 후처리
        
        드라이버 생성 직후 실행되는 후처리 로직입니다.
        """
        if hasattr(self.config, 'save_session') and self.config.save_session:
            self._save_session_headers()
    
    # ==========================================================================
    # Logging Setup (공통)
    # ==========================================================================
    
    def _setup_logging(self):
        """로깅 설정 (공통)
        
        LogContextManager를 사용하여 로깅을 설정합니다.
        """
        from logs_utils import LogContextManager
        
        # config에서 로깅 설정 가져오기
        log_config = getattr(self.config, 'log_config', None)
        
        # 로깅 설정이 없으면 기본 콘솔 로깅
        if log_config is None:
            log_config = {
                "name": self.__class__.__name__.lower(),
                "sinks": [
                    {
                        "sink_type": "console",
                        "level": "INFO",
                        "format": "<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> | <level>{message}</level>",
                        "colorize": True
                    }
                ]
            }
        
        self._log_context = LogContextManager(log_config)
        self.logger = self._log_context.__enter__()
        self._logging_active = True
        self.logger.debug(f"{self.__class__.__name__} initialized.")
    
    def _stop_logging(self, exc_type=None, exc_val=None, exc_tb=None):
        """로깅 종료 (공통)"""
        if self._logging_active and self._log_context:
            self._log_context.__exit__(exc_type, exc_val, exc_tb)
            self._logging_active = False
    
    # ==========================================================================
    # Context Manager
    # ==========================================================================
    
    def __enter__(self) -> "BaseWebDriver":
        """Context manager entry
        
        Example:
            >>> with FirefoxWebDriver("config.yaml") as driver:
            ...     driver.driver.get("https://example.com")
        """
        self._context_managed = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        try:
            self.quit()
        finally:
            self._stop_logging(exc_type, exc_val, exc_tb)
            self._context_managed = False
    
    def __del__(self):
        """Destructor - 리소스 정리"""
        try:
            if self._driver:
                self.quit()
        except Exception:
            pass
