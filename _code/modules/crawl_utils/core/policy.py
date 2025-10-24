# -*- coding: utf-8 -*-
# crawl_utils/core/policy.py
# Crawl utilities policy definitions

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Literal, Any

from pydantic import BaseModel, Field, HttpUrl, model_validator

from modules.logs_utils import LogPolicy

from .models import ItemKind


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
    """데이터 추출 정책
    
    Extractor 타입에 따라 다양한 방식으로 데이터 추출:
    - DOM: CSS/XPath 선택자로 DOM 추출 (BeautifulSoup - 향후)
    - JS: JavaScript snippet 실행 (현재 우선)
    - API: REST API 호출 (향후)
    
    JS snippet 방식:
    - js_snippet: YAML inline JS 코드 (간단한 경우)
    - js_snippet_file: 별도 .js 파일 경로 (복잡한 경우, v1.1 향후 지원)
    """
    type: ExtractorType = Field(ExtractorType.JS, description="Extractor type (dom/js/api)")
    
    # DOM Extractor (향후 BeautifulSoup)
    item_selector: Optional[str] = Field(None, description="CSS/XPath selector for DOM extractor")
    
    # JS Extractor
    js_snippet: Optional[str] = Field(None, description="Inline JS snippet (현재 우선)")
    js_snippet_file: Optional[str] = Field(
        None,
        description="Path to .js file (v1.1 향후 지원, 복잡한 JS 코드용)"
    )
    
    # API Extractor (향후)
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
# PostProcessor Policy (New - v2.0 개선)
# =============================================================================

class PostProcessorRule(BaseModel):
    """PostProcessor 규칙 (fso_utils 통합 + 동적 템플릿 지원)
    
    JS Extractor 결과를 KeyPath로 추출하여 FSOPathBuilder로 저장.
    
    동적 템플릿 지원:
    - fso_name_policy 필드에서 {{item.title}}, {{cas_no}} 등 템플릿 사용 가능
    - dynamic_subdir에서 {{cas_no}}/images 등 동적 폴더명 사용 가능
    - 템플릿 변수는 JS 추출 결과 + runtime_context 결합
    
    Example:
        ```yaml
        rules:
          - kind: "image"
            source: "images"  # JS 결과의 images 필드
            fso_name_policy:
              prefix: "{{item.title}}"  # JS 결과의 title 필드 사용
              suffix: "{{item.price}}"  # JS 결과의 price 필드 사용
              tail_mode: "counter"
              extension: "jpg"
            dynamic_subdir: "{{cas_no}}/images"  # 런타임 인자 cas_no 사용
        ```
    """
    kind: str = Field(..., description="File kind: image/text/file")
    source: str = Field(..., description="KeyPath to extract from JS result (dot notation)")
    allow_empty: bool = Field(False, description="Keep empty values")
    
    # 동적 폴더명 템플릿 (✨ v2.0 신규)
    dynamic_subdir: Optional[str] = Field(
        None,
        description="Dynamic subdirectory template (e.g., '{{cas_no}}/images', '{{item.category}}')"
    )
    
    # FSO policies (명시적 구분)
    fso_name_policy: Dict = Field(
        default_factory=dict,
        description="FSONamePolicy dict (supports templates: {{item.field}}, {{runtime_var}})"
    )
    fso_ops_policy: Optional[Dict] = Field(
        None,
        description="FSOOpsPolicy dict (exist, ext settings)"
    )
    
    # 템플릿 렌더링 옵션
    template_safe_mode: bool = Field(
        True,
        description="If True, missing template vars are replaced with empty string instead of raising error"
    )


class PostProcessorPolicy(BaseModel):
    """PostProcessor 정책 (v2.0 - 동적 템플릿 지원)
    
    PostProcessor는 Extract 단계에서 추출한 Dict를 NormalizedItem으로 변환하고,
    fso_utils를 사용하여 파일로 저장합니다.
    
    주요 기능:
    - KeyPath 기반 데이터 추출 (source 필드)
    - 동적 파일명 생성 (fso_name_policy에서 템플릿 지원)
    - 동적 폴더명 생성 (dynamic_subdir 템플릿)
    - fso_utils 정책 적용 (FSONamePolicy, FSOOpsPolicy)
    
    Example YAML:
        ```yaml
        post_processor:
          target_dir: "{{output_dir}}/crawl"
          use_smart_normalizer: true
          rules:
            - kind: "image"
              source: "images"
              dynamic_subdir: "{{cas_no}}/{{item.category}}"
              fso_name_policy:
                prefix: "{{item.title}}"
                tail_mode: "counter"
                extension: "jpg"
        ```
    """
    target_dir: Path = Field(
        default_factory=lambda: Path.cwd() / "_output" / "crawl",
        description="Base output directory (supports env vars via path_utils.resolve)"
    )
    
    # PostProcessor 모드 선택
    use_smart_normalizer: bool = Field(
        True,
        description="Use SmartNormalizer (auto type inference) instead of rule-based DataNormalizer"
    )
    
    # 템플릿 렌더링 옵션 (전역 설정)
    template_safe_mode: bool = Field(
        True,
        description="If True, missing template vars are replaced with empty string instead of raising error"
    )
    
    rules: List[PostProcessorRule] = Field(
        default_factory=list,
        description="PostProcessor rules (KeyPath extraction + FSO storage)"
    )


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
# Crawl Policy (Adapter)
# =============================================================================

class CrawlPolicy(BaseModel):
    """Crawl(Adapter) 전용 Policy - 순수 크롤링 로직 설정
    
    이 Policy는 Crawl 클래스에서 사용하며, 크롤링 실행에 필요한 설정만 포함합니다.
    - navigation: 페이지 네비게이션 설정 (Optional)
    - scroll: 스크롤 설정
    - extractor: 데이터 추출 설정
    - wait: 대기 설정
    - post_processor: PostProcessor 설정 (KeyPath + FSO)
    - log: 로깅 설정 (Optional, config_loader에서 주입 가능)
    
    Note: URLs는 run() 메서드에서 직접 전달받습니다.
          Site/Method는 PresetManager.analyze_url()로 자동 결정됩니다.
    """
    # Config section name (ConfigLikeLoader용)
    name: str = Field("crawl", description="Config section name for ConfigLikeLoader")
    
    # Site/Method 정보 (PresetManager.analyze_url()로 자동 결정)
    site: str = Field(default="", description="Site identifier (aliexpress, taobao) - auto-detected by PresetManager")
    method: str = Field(default="", description="Method identifier (detail, search) - auto-detected by PresetManager")
    
    # Navigation (Optional - search 메서드에서만 필요)
    navigation: Optional[NavigationPolicy] = Field(
        None,
        description="Page navigation settings (required for search method, optional for detail)"
    )
    
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
# Unified Policy for SyncCrawl Adapter (OTO Pattern)
# =============================================================================

class SyncCrawlPolicy(BaseModel):
    """SyncCrawl Adapter 통합 Policy (OTO 패턴)
    
    translate_utils의 TranslatorPolicy, image_utils의 ImageLoaderPolicy와 동일한 구조:
    - webdriver_manager: WebDriver 설정 (WebDriverManagerPolicy)
    - crawl: 크롤링 설정 (CrawlPolicy)
    
    ConfigLoader 사용 시:
        ```yaml
        # config_loader_crawl.yaml
        source:
          - src: ["{{configs_crawl_dir}}/webdriver_manager.yaml", "webdriver_manager"]
          - src: ["{{configs_crawl_dir}}/sync_crawl.yaml", "crawl"]
          - src: ["{{configs_logs_dir}}/crawl_parent.yaml", "log"]
        ```
    
    Python 사용:
        ```python
        from cfg_utils import ConfigLoader
        from crawl_utils.adapter import SyncCrawl
        
        config = ConfigLoader("configs/loader/config_loader_crawl.yaml")
        crawl = SyncCrawl(cfg_like=config.to_dict())  # ✅ 단일 cfg_like
        ```
    """
    name: str = Field(default="sync_crawl", description="Section name in YAML config")
    webdriver_manager: Any = Field(
        default=None,
        description="WebDriver manager configuration (WebDriverManagerPolicy)"
    )
    crawl: CrawlPolicy = Field(
        default_factory=CrawlPolicy,  # pyright: ignore[reportArgumentType]
        description="Crawl configuration"
    )
    log: Optional[LogPolicy] = Field(None, description="Logging configuration (Optional)")
    
    @model_validator(mode="before")
    @classmethod
    def validate_webdriver_manager(cls, values):
        """WebDriverManagerPolicy 지연 import 및 검증
        
        Circular import 방지를 위해 @model_validator에서 import
        """
        if isinstance(values, dict) and "webdriver_manager" not in values:
            # Import here to avoid circular imports
            from crawl_utils.provider.policy import WebDriverManagerPolicy
            values["webdriver_manager"] = WebDriverManagerPolicy().model_dump()
        
        return values
    
    @model_validator(mode="after")
    def validate_policy(self):
        """WebDriverManagerPolicy 타입 검증 (after mode)"""
        # Import here to avoid circular imports
        from crawl_utils.provider.policy import WebDriverManagerPolicy
        
        if self.webdriver_manager is None:
            self.webdriver_manager = WebDriverManagerPolicy()
        elif isinstance(self.webdriver_manager, dict):
            self.webdriver_manager = WebDriverManagerPolicy(**self.webdriver_manager)
        
        return self


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
