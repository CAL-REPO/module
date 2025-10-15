# -*- coding: utf-8 -*-
# crawl_utils/provider/factory.py
# WebDriver Factory for creating provider-specific drivers

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union, TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from crawl_utils.provider.base import BaseWebDriver
    from crawl_utils.core.policy import ProviderType
    from cfg_utils import ConfigPolicy


def create_webdriver(
    provider: Union[str, "ProviderType"],
    cfg_like: Union[BaseModel, Path, str, dict, list, None] = None,
    *,
    policy: Optional[Any] = None,  # ConfigPolicy
    **overrides: Any
) -> "BaseWebDriver":
    """WebDriver 팩토리 함수
    
    provider 타입에 따라 적절한 WebDriver 인스턴스를 생성합니다.
    ConfigLoader 패턴을 따르며, 모든 드라이버는 동일한 인터페이스를 제공합니다.
    
    Args:
        provider: WebDriver 타입 ("firefox", "chrome", "edge" 등)
        cfg_like: 설정 소스 (BaseModel, YAML 경로, dict, list 등)
            - BaseModel: Policy 인스턴스 직접 전달
            - str/Path: YAML 파일 경로
            - list: 여러 YAML 파일 (순서대로 병합)
            - dict: 설정 딕셔너리
            - None: 기본 설정 파일 사용
        policy: ConfigPolicy 인스턴스 (merge_mode 등)
        **overrides: 런타임 오버라이드 값
    
    Returns:
        생성된 WebDriver 인스턴스 (BaseWebDriver 서브클래스)
    
    Raises:
        ValueError: 지원하지 않는 provider 타입
        ImportError: 필요한 의존성이 설치되지 않음
    
    Example:
        >>> # Firefox 드라이버 생성
        >>> driver = create_webdriver("firefox", "configs/firefox.yaml")
        >>> driver.driver.get("https://example.com")
        
        >>> # dict로 직접 설정
        >>> driver = create_webdriver(
        ...     "firefox",
        ...     {"headless": True, "window_size": (1920, 1080)}
        ... )
        
        >>> # 런타임 오버라이드
        >>> driver = create_webdriver(
        ...     "firefox",
        ...     "config.yaml",
        ...     headless=True,
        ...     user_agent="Custom UA"
        ... )
        
        >>> # Context manager 사용
        >>> with create_webdriver("firefox", {"headless": True}) as driver:
        ...     driver.driver.get("https://example.com")
        
        >>> # Chrome 드라이버 (향후 구현)
        >>> # driver = create_webdriver("chrome", "config/chrome.yaml")
    """
    provider_lower = provider.lower()
    
    # Firefox
    if provider_lower == "firefox":
        try:
            from crawl_utils.provider.firefox import FirefoxWebDriver
            return FirefoxWebDriver(cfg_like, policy=policy, **overrides)
        except ImportError as e:
            raise ImportError(
                f"Firefox WebDriver dependencies not installed. "
                f"Install with: pip install selenium\n"
                f"Original error: {e}"
            ) from e
    
    # Chrome (향후 구현)
    elif provider_lower == "chrome":
        raise NotImplementedError(
            "Chrome WebDriver is not yet implemented. "
            "Please use 'firefox' or implement ChromeWebDriver."
        )
    
    # Edge (향후 구현)
    elif provider_lower == "edge":
        raise NotImplementedError(
            "Edge WebDriver is not yet implemented. "
            "Please use 'firefox' or implement EdgeWebDriver."
        )
    
    # 지원하지 않는 provider
    else:
        raise ValueError(
            f"Unsupported provider: {provider!r}. "
            f"Supported providers: 'firefox', 'chrome' (planned), 'edge' (planned)"
        )


# Alias for convenience
webdriver_factory = create_webdriver
