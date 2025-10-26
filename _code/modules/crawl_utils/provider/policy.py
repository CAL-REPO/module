# -*- coding: utf-8 -*-
# crawl_utils/provider/policy.py
# WebDriver provider policy definitions

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Literal, Union

from pydantic import BaseModel, Field, model_validator, field_validator


# =============================================================================
# WebDriver Policies
# =============================================================================

ProviderType = Literal["firefox", "chrome", "edge"]


# -----------------------------------------------------------------------------
# Browser-Specific Config Models
# -----------------------------------------------------------------------------

class FirefoxConfig(BaseModel):
    """Firefox WebDriver 설정"""
    binary_path: Optional[Path] = Field(None, description="Firefox binary executable path")
    profile_path: Optional[Path] = Field(None, description="Firefox profile directory path")
    driver_path: Optional[Path] = Field(None, description="Geckodriver path")
    use_webdriver_manager: bool = Field(True, description="Auto-download/update geckodriver")
    
    # Firefox preferences (Anti-Detection)
    dom_enabled: bool = Field(False, description="dom.webdriver.enabled = false")
    resist_fingerprint_enabled: bool = Field(False, description="privacy.resistFingerprinting = false")
    
    # 추가 옵션
    enable_cookies: bool = Field(True, description="Enable cookies")
    enable_cache: bool = Field(True, description="Enable cache")
    load_images: bool = Field(True, description="Enable image loading")
    enable_javascript: bool = Field(True, description="Enable JavaScript")


class ChromeConfig(BaseModel):
    """Chrome WebDriver 설정"""
    binary_path: Optional[Path] = Field(None, description="Chrome binary executable path")
    user_data_dir: Optional[Path] = Field(None, description="Chrome user data directory")
    driver_path: Optional[Path] = Field(None, description="Chromedriver path")
    use_webdriver_manager: bool = Field(True, description="Auto-download chromedriver")
    
    # Chrome 옵션
    disable_extensions: bool = Field(True, description="Disable Chrome extensions")
    disable_gpu: bool = Field(False, description="Disable GPU acceleration")
    no_sandbox: bool = Field(False, description="Disable sandbox mode")


class EdgeConfig(BaseModel):
    """Edge WebDriver 설정"""
    binary_path: Optional[Path] = Field(None, description="Edge binary executable path")
    user_data_dir: Optional[Path] = Field(None, description="Edge user data directory")
    driver_path: Optional[Path] = Field(None, description="EdgeDriver path")
    use_webdriver_manager: bool = Field(True, description="Auto-download edgedriver")


# -----------------------------------------------------------------------------
# WebDriver Policy (Unified)
# -----------------------------------------------------------------------------

class WebDriverManagerPolicy(BaseModel):
    """통합 WebDriver Manager 정책 (모든 브라우저 지원)
    
    Section명: Policy.name 필드 사용 (기본값: "webdriver_manager")
    provider 필드로 Firefox/Chrome/Edge 구분
    
    ConfigLikeLoader 사용:
    - Policy.name 필드로 자동 section 추출
    - SectionExtractor.get_policy_name(WebDriverManagerPolicy) 사용
    
    Example YAML:
        ```yaml
        webdriver_manager:  # ✅ Policy.name 필드 사용
          provider: "firefox"  # firefox, chrome, edge
          region: "china"
          
          # 공통 설정
          user_agent: "Mozilla/5.0 ..."
          accept_languages: "zh-CN,zh;q=0.9,..."
          
          # Firefox 전용
          firefox:
            profile_path: "M:/Firefox_Profile/China"
            dom_enabled: false
          
          # Chrome 전용 (선택사항)
          chrome:
            user_data_dir: "M:/Chrome_Profile/China"
        ```
    """
    name: str = Field(default="webdriver_manager", description="Config section name (ConfigLikeLoader용)")
    region: str = Field(default="", description="Region identifier (china, global, us, eu)")
    provider: ProviderType = Field(default="firefox", description="WebDriver provider type")
    
    # 기본 WebDriver 설정 (모든 브라우저 공통)
    headless: bool = Field(False, description="Run browser in headless mode")
    window_size: Optional[Tuple[int, int]] = Field((1920, 1080), description="Browser window size")
    
    # User-Agent & Accept-Language (모든 브라우저 공통)
    user_agent: str = Field(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0",
        description="User-Agent string (default: Firefox 144.0)"
    )
    accept_languages: str = Field(
        "en-US,en;q=0.9",
        description="Accept-Language header"
    )
    
    # Automation 감지 우회 (모든 브라우저 공통)
    disable_automation: bool = Field(True, description="Disable automation detection flags")
    
    # 로깅 설정
    log_config: Optional[Union[str, Path, dict, None]] = Field(
        None,
        description="Logging configuration"
    )
    
    # -------------------------------------------------------------------------
    # 브라우저별 전용 설정 (선택적)
    # -------------------------------------------------------------------------
    firefox: Optional[FirefoxConfig] = Field(None, description="Firefox config")
    chrome: Optional[ChromeConfig] = Field(None, description="Chrome config")
    edge: Optional[EdgeConfig] = Field(None, description="Edge config")
    
    @field_validator("window_size", mode="before")
    @classmethod
    def validate_window_size(cls, v):
        """window_size를 튜플로 변환"""
        if v is None:
            return None
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return (int(v[0]), int(v[1]))
        raise ValueError("window_size must be a tuple of two integers or None")
    
    @model_validator(mode="after")
    def validate_provider_config(self):
        """provider에 맞는 전용 설정 확인"""
        # region이 설정되어 있으면 실제 사용 중이므로 validation 수행
        # region이 빈 문자열이면 기본 인스턴스 생성이므로 skip
        if self.region == "":
            return self
        
        if self.provider == "firefox" and not self.firefox:
            raise ValueError(
                "Firefox provider requires 'firefox' config section. "
                "Add 'firefox:' section to your YAML config."
            )
        
        if self.provider == "chrome" and not self.chrome:
            raise ValueError(
                "Chrome provider requires 'chrome' config section. "
                "Add 'chrome:' section to your YAML config."
            )
        
        if self.provider == "edge" and not self.edge:
            raise ValueError(
                "Edge provider requires 'edge' config section. "
                "Add 'edge:' section to your YAML config."
            )
        return self
