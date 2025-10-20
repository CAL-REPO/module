# -*- coding: utf-8 -*-
# crawl_utils/core/policy.py
# Crawl utilities policy definitions

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Literal, Union

from pydantic import BaseModel, Field, HttpUrl, model_validator, field_validator

from modules.logs_utils import LogPolicy

from .models import ItemKind


# =============================================================================
# WebDriver Policies
# =============================================================================

ProviderType = Literal["firefox", "chrome", "edge"]


class WebDriverPolicy(BaseModel):
    """모든 WebDriver 공통 정책
    
    확장 가능한 WebDriver 설정 베이스 클래스.
    Firefox, Chrome, Edge 등 모든 브라우저의 공통 설정을 정의합니다.
    """
    name: str = Field("webdriver", description="Config section name used by ConfigLoader")
    site: str = Field(default="", description="Site identifier (aliexpress, taobao)")
    provider: ProviderType = Field("firefox", description="WebDriver provider type")
    
    # 기본 WebDriver 설정
    headless: bool = Field(False, description="Run browser in headless mode")
    window_size: Optional[Tuple[int, int]] = Field((1440, 900), description="Browser window size (width, height)")
    
    # Session 관리
    session_path: Optional[Path] = Field(None, description="Path to save/load browser session data")
    save_session: bool = Field(False, description="Enable session save/restore")
    
    # Driver 경로
    driver_path: Optional[Path] = Field(None, description="Custom WebDriver executable path")
    
    # 공통 브라우저 옵션
    user_agent: Optional[str] = Field(None, description="Custom User-Agent string")
    accept_languages: Optional[str] = Field("ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7", description="Accept-Language header")
    
    # Automation 감지 우회
    disable_automation: bool = Field(True, description="Disable automation detection flags")
    
    # 로깅 설정 (logs_utils 호환)
    log_config: Optional[Union[str, Path, dict, None]] = Field(
        None,
        description="Logging configuration: YAML path, dict config, or None for default console logging"
    )
    
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
    def validate_paths(self):
        """경로 유효성 검증 및 세션 디렉토리 생성"""
        if self.driver_path and not Path(self.driver_path).exists():
            # driver_path는 경고만 (webdriver-manager가 자동 다운로드할 수 있음)
            pass
        
        if self.session_path and self.save_session:
            Path(self.session_path).parent.mkdir(parents=True, exist_ok=True)
        
        return self


class FirefoxPolicy(WebDriverPolicy):
    """Firefox WebDriver 전용 정책
    
    Firefox 브라우저의 특화된 설정을 정의합니다.
    """
    name: str = Field("firefox", description="Config section name for Firefox settings")
    provider: Literal["firefox"] = "firefox"
    
    # Firefox 전용 경로
    binary_path: Optional[Path] = Field(None, description="Firefox binary executable path")
    profile_path: Optional[Path] = Field(None, description="Firefox profile directory path")
    
    # Firefox 전용 preferences (Anti-Detection)
    dom_enabled: bool = Field(False, description="dom.webdriver.enabled = false (automation detection bypass)")
    resist_fingerprint_enabled: bool = Field(False, description="privacy.resistFingerprinting = false (natural browser behavior)")
    
    # Firefox 추가 옵션
    enable_cookies: bool = Field(True, description="Enable cookies")
    enable_cache: bool = Field(True, description="Enable cache")
    load_images: bool = Field(True, description="Enable image loading")
    enable_javascript: bool = Field(True, description="Enable JavaScript")
    
    # geckodriver 관리
    use_webdriver_manager: bool = Field(True, description="Auto-download/update geckodriver via webdriver-manager")
    
    @model_validator(mode="after")
    def validate_firefox_paths(self):
        """Firefox 전용 경로 검증"""
        if self.binary_path and not Path(self.binary_path).is_file():
            raise ValueError(f"Invalid Firefox binary_path: {self.binary_path}")
        
        if self.profile_path and not Path(self.profile_path).is_dir():
            raise ValueError(f"Invalid Firefox profile_path: {self.profile_path}")
        
        return self


class ChromePolicy(WebDriverPolicy):
    """Chrome WebDriver 전용 정책 (추후 구현)
    
    Chrome 브라우저의 특화된 설정을 정의합니다.
    """
    name: str = Field("chrome", description="Config section name for Chrome settings")
    provider: Literal["chrome"] = "chrome"
    
    # Chrome 전용 경로
    binary_path: Optional[Path] = Field(None, description="Chrome binary executable path")
    user_data_dir: Optional[Path] = Field(None, description="Chrome user data directory")
    
    # Chrome 전용 arguments
    disable_gpu: bool = Field(False, description="Disable GPU acceleration")
    no_sandbox: bool = Field(False, description="Disable sandbox mode")
    
    # chromedriver 관리
    use_webdriver_manager: bool = Field(True, description="Auto-download chromedriver if not found")


# =============================================================================
# Crawl Pipeline Policies
# =============================================================================


class ExecutionMode(str, Enum):
    """크롤링 실행 모드
    
    - ASYNC: 비동기 실행 (기본값, 고성능)
    - SYNC: 동기 실행 (간단한 스크립트에 적합)
    """
    ASYNC = "async"
    SYNC = "sync"


class ScrollStrategy(str, Enum):
    NONE = "none"
    PAGINATE = "paginate"
    INFINITE = "infinite"


class WaitHook(str, Enum):
    NONE = "none"
    CSS = "css"
    XPATH = "xpath"


class WaitCondition(str, Enum):
    PRESENCE = "presence"
    VISIBILITY = "visibility"


class ExtractorType(str, Enum):
    DOM = "dom"
    JS = "js"
    API = "api"


class NavigationPolicy(BaseModel):
    base_url: HttpUrl
    url_template: Optional[str] = None
    params: Dict[str, str | int | float] = Field(default_factory=dict)
    page_param: str = Field("page", min_length=1)
    start_page: int = Field(1, ge=1)
    max_pages: int = Field(1, ge=1)


class ScrollPolicy(BaseModel):
    strategy: ScrollStrategy = Field(ScrollStrategy.NONE, description="Scroll strategy")
    scroll_count: Optional[int] = Field(None, ge=0, description="Fixed scroll count (site-specific)")
    max_scrolls: int = Field(0, ge=0, description="Maximum scroll attempts")
    scroll_pause_sec: float = Field(0.5, ge=0.0)


class ExtractorPolicy(BaseModel):
    type: ExtractorType = Field(ExtractorType.DOM, description="Extractor type")
    item_selector: Optional[str] = None
    js_snippet: Optional[str] = Field(None, description="Custom JS snippet for JS extractor")
    api_endpoint: Optional[str] = None
    api_method: str = Field("GET", pattern="^[A-Z]+$")
    payload: Optional[Dict] = None


class WaitPolicy(BaseModel):
    hook: WaitHook = Field(WaitHook.NONE, description="Wait hook type")
    selector: Optional[str] = None
    timeout_sec: float = Field(5.0, ge=0.0)
    condition: WaitCondition = Field(
        WaitCondition.PRESENCE,
        description="Wait condition to satisfy (presence/visibility).",
    )


class HttpSessionPolicy(BaseModel):
    use_browser_headers: bool = Field(False, description="Load headers from browser session JSON")
    session_json_path: Optional[Path] = Field(None, description="Path to Firefox session JSON (expects {'headers': {...}})")
    headers: Dict[str, str] = Field(default_factory=dict, description="Extra static headers")


class NormalizationRule(BaseModel):
    kind: ItemKind
    source: str = Field(..., description="Dot-path to value within extractor record.")
    section_field: Optional[str] = Field(None, description="Dot-path for section grouping.")
    static_section: Optional[str] = None
    name_template: Optional[str] = Field(None, description="Format string for output names.")
    extension: Optional[str] = None
    explode: bool = Field(True, description="Treat iterable values as multiple items.")
    allow_empty: bool = Field(False, description="Keep empty values.")


class NormalizationPolicy(BaseModel):
    rules: List[NormalizationRule] = Field(default_factory=list)


# =============================================================================
# PostProcessor Policy (New)
# =============================================================================

class PostProcessorRule(BaseModel):
    """PostProcessor 규칙 (fso_utils 통합)
    
    JS Extractor 결과를 KeyPath로 추출하여 FSOPathBuilder로 저장.
    """
    kind: str = Field(..., description="File kind: image/text/file")
    source: str = Field(..., description="KeyPath to extract from JS result")
    static_section: Optional[str] = Field(None, description="Fixed section name")
    allow_empty: bool = Field(False, description="Keep empty values")
    dynamic_subdir: Optional[str] = Field(None, description="Dynamic subdirectory template")
    
    # FSO policies (명시적 구분)
    fso_name_policy: Dict = Field(default_factory=dict, description="FSONamePolicy dict")
    fso_ops_policy: Optional[Dict] = Field(None, description="FSOOpsPolicy dict")


class PostProcessorPolicy(BaseModel):
    """PostProcessor 정책"""
    target_dir: Path = Field(
        default_factory=lambda: Path.cwd() / "_output" / "crawl",
        description="Base output directory"
    )
    rules: List[PostProcessorRule] = Field(default_factory=list)


def _default_output_root() -> Path:
    return Path.cwd() / "_output" / "crawl"


class StorageTargetPolicy(BaseModel):
    base_dir: Path = Field(default_factory=_default_output_root)
    sub_dir: Optional[str] = None
    name_template: str = Field("{section}_{index}", description="Default filename template.")
    extension: Optional[str] = None
    ensure_unique: bool = True

    @model_validator(mode="after")
    def ensure_exists(self):
        target = self.base_dir / (self.sub_dir or "")
        target.mkdir(parents=True, exist_ok=True)
        return self


class StoragePolicy(BaseModel):
    image: Optional[StorageTargetPolicy] = None
    text: Optional[StorageTargetPolicy] = None
    file: Optional[StorageTargetPolicy] = None

    def target_for(self, kind: ItemKind) -> Optional[StorageTargetPolicy]:
        return getattr(self, kind, None)

    @model_validator(mode="after")
    def validate_any(self):
        if not (self.image or self.text or self.file):
            raise ValueError("StoragePolicy requires at least one target (image/text/file).")
        return self


# =============================================================================
# Source Policy
# =============================================================================

class CrawlSourcePolicy(BaseModel):
    """Crawl Source Policy - URL 소스 설정
    
    크롤링할 URL 목록과 크롤링 방법을 정의합니다.
    """
    urls: List[str] = Field(default_factory=list, description="URL list to crawl")
    method: Literal["product_detail", "product_search"] = Field(
        "product_detail",
        description="Crawl method: product_detail (상품 상세) or product_search (상품 검색)"
    )


# =============================================================================
# Crawl Policy (Adapter)
# =============================================================================

class CrawlPolicy(BaseModel):
    """Crawl(Adapter) 전용 Policy - 순수 크롤링 로직 설정
    
    이 Policy는 Crawl 클래스에서 사용하며, 크롤링 실행에 필요한 설정만 포함합니다.
    - source: URL 소스 및 method 설정
    - navigation: 페이지 네비게이션 설정
    - scroll: 스크롤 설정
    - extractor: 데이터 추출 설정
    - wait: 대기 설정
    - post_processor: PostProcessor 설정 (KeyPath + FSO)
    - log: 로깅 설정 (Optional, config_loader에서 주입 가능)
    """
    # Source 설정
    source: CrawlSourcePolicy = Field(default_factory=CrawlSourcePolicy)  # pyright: ignore[reportArgumentType]
    
    # Site/Method 정보 (URL 분석으로 자동 결정, 또는 YAML에서 명시)
    site: str = Field(default="", description="Site identifier (aliexpress, taobao) - auto-detected from URL")
    method: str = Field(default="", description="Method identifier (detail, search) - from source.method")
    
    # URL 패턴 설정 (UrlAnalyzer에서 사용)
    url_patterns: Optional[Dict[str, Dict[str, List[str]]]] = Field(
        None,
        description="URL pattern configuration for UrlAnalyzer (site_domains, method_patterns)"
    )
    
    navigation: NavigationPolicy
    scroll: ScrollPolicy = Field(default_factory=ScrollPolicy) # pyright: ignore[reportArgumentType]
    extractor: ExtractorPolicy = Field(default_factory=ExtractorPolicy) # pyright: ignore[reportArgumentType]
    wait: WaitPolicy = Field(default_factory=WaitPolicy) # pyright: ignore[reportArgumentType]
    
    # PostProcessor (New - fso_utils 통합)
    post_processor: Optional[PostProcessorPolicy] = Field(
        None,
        description="PostProcessor policy (KeyPath extraction + FSO storage)"
    )
    
    # Legacy (SmartNormalizer용, 선택사항)
    normalization: NormalizationPolicy = Field(default_factory=NormalizationPolicy)
    storage: Optional[StoragePolicy] = None
    
    http_session: HttpSessionPolicy = Field(default_factory=HttpSessionPolicy) # pyright: ignore[reportArgumentType]
    
    # Execution settings
    execution_mode: ExecutionMode = Field(
        ExecutionMode.ASYNC,
        description="실행 모드: async (비동기, 고성능) 또는 sync (동기, 단순)"
    )
    concurrency: int = Field(
        default=2,
        ge=1,
        le=32,
        description="동시 처리 작업 수 (async 모드에서만 유효)"
    )
    
    # Retry settings
    retries: int = Field(default=2, ge=0, le=10)
    retry_backoff_sec: float = Field(1.0, ge=0.0)
    
    # Logging (✨ TranslatePolicy 패턴)
    log: Optional[LogPolicy] = None


# =============================================================================
# EntryPoint Policy (Crawler)
# =============================================================================

class CrawlerPolicy(BaseModel):
    """Crawler EntryPoint 정책 (translate_utils.TranslatorPolicy 패턴)
    
    YAML 파일 기반 크롤링 실행을 위한 통합 정책.
    - source: URL 소스 설정 (TODO: URLSourcePolicy 구현 필요)
    - crawl: 크롤 설정 (CrawlPolicy 위임, log 포함)
    
    Example YAML:
        ```yaml
        # crawler.yaml
        source:
          urls: ["https://aliexpress.com/item/123"]
        
        crawl:
          site: "aliexpress"
          method: "detail"
          wait:
            timeout: 10
          log:
            enabled: true
            log_level: "INFO"
        ```
    """
    name: str = Field("crawler", description="Config section name")
    
    # source: URL 소스 설정 (TODO: URLSourcePolicy 구현 필요)
    # source: Optional[URLSourcePolicy] = None
    
    # crawl: 크롤 설정 (CrawlPolicy 위임, log는 crawl.log에 포함)
    crawl: CrawlPolicy = Field(default_factory=CrawlPolicy)  # pyright: ignore[reportArgumentType]
