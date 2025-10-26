# -*- coding: utf-8 -*-
# crawl_utils/core/policy.py
# Crawl utilities policy definitions

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Literal, Any, TYPE_CHECKING, Tuple, Set

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from modules.logs_utils import LogPolicy
from modules.path_utils import OSPath, downloads
from modules.fso_utils.core.policy import FSONamePolicy, FSOOpsPolicy, ExistencePolicy, FileExtensionPolicy

if TYPE_CHECKING:
    pass

class PolicyBase(BaseModel):
    # ✅ 한 번만 선언 → 모든 정책 모델에 공통 적용
    model_config = ConfigDict(
        extra="forbid",
        validate_default=True,
    )

class SessionBridgePolicy(BaseModel):
    user_agent: Optional[str] = None  # 없으면 WebDriver에서 자동 추출
    proxy: Optional[str] = None       # 없으면 미적용

class HttpSessionPolicy(BaseModel):
    reuse: bool = True
    timeout_connect_sec: float = 8.0
    timeout_read_sec: float = 45.0
    allow_redirects: bool = True
    stream_download: bool = True

class CookieBridgePolicy(BaseModel):
    cookie_sync_domains: List[str] = []  # 비어있으면 lazy-sync만(401/302 때 resync)

class RetryPolicy(BaseModel):
    max_attempts: int = Field(3, ge=0, le=10)
    backoff_base_ms: int = Field(200, ge=0, le=10000)
    backoff_factor: float = Field(2.0, ge=1.0, le=10.0)
    jitter_ms: int = Field(100, ge=0, le=2000)
    retry_status_codes: Set[int] = Field(default_factory=lambda: {500, 502, 503, 504})
    retry_on_auth_like: bool = True

class ExecutionMode(str, Enum):
    """크롤링 실행 모드
    
    - ASYNC: 비동기 실행 (기본값, 고성능)
    - SYNC: 동기 실행 (간단한 스크립트에 적합)
    """
    ASYNC = "async"
    SYNC = "sync"

class NavigationPolicy(PolicyBase):
    base_url: HttpUrl
    url_template: Optional[str] = None
    params: Dict[str, str | int | float] = Field(default_factory=dict)
    page_param: str = Field("page", min_length=1)
    start_page: int = Field(1, ge=1)
    max_pages: int = Field(1, ge=1)

class ScrollStrategy(str, Enum):
    NONE = "none"
    PAGINATE = "paginate"
    INFINITE = "infinite"

class ScrollPolicy(PolicyBase):
    strategy: ScrollStrategy = Field(ScrollStrategy.NONE, description="Scroll strategy")
    scroll_count: Optional[int] = Field(None, ge=0, description="Fixed scroll count (site-specific)")
    max_scrolls: int = Field(0, ge=0, description="Maximum scroll attempts")
    scroll_pause_sec: float = Field(0.5, ge=0.0)

class WaitHook(str, Enum):
    NONE = "none"
    CSS = "css"
    XPATH = "xpath"

class WaitCondition(str, Enum):
    PRESENCE = "presence"
    VISIBILITY = "visibility"

class WaitPolicy(PolicyBase):
    hook: WaitHook = Field(WaitHook.NONE, description="Wait hook type")
    selector: Optional[str] = None
    timeout_sec: float = Field(5.0, ge=0.0)
    condition: WaitCondition = Field(
        WaitCondition.PRESENCE,
        description="Wait condition to satisfy (presence/visibility).",
    )

# =============================================================================
# Execution & Retry Policies (v5.1 - 계층화)
# =============================================================================

class ExecutionPolicy(PolicyBase):
    """실행 정책 (Sync/Async 공통)
    
    크롤링 실행 모드 및 동시성 설정.
    
    Attributes:
        mode: 실행 모드 (async/sync)
        concurrency: 동시 처리 작업 수 (async 모드에서만 유효)
    
    Example:
        ```yaml
        execution:
          mode: "async"
          concurrency: 5
        ```
    """
    mode: ExecutionMode = Field(
        default=ExecutionMode.ASYNC,
        description="실행 모드: async (비동기, 고성능) 또는 sync (동기, 단순)"
    )
    concurrency: int = Field(
        default=2,
        ge=1,
        le=32,
        description="동시 처리 작업 수 (async 모드에서만 유효)"
    )

class ExtractorType(str, Enum):
    DOM = "dom"
    JS = "js"
    API = "api"

class ExtractorPolicy(PolicyBase):
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


# =============================================================================
# PostProcessor Policy (v5.1 - 계층화)
# =============================================================================

# =============================================================================
# Save/Load Models (v5.3)
# ========================================================================
ItemKind = Literal["image", "text", "file"] 

class ItemPostProcessPolicy(PolicyBase):
    """정규화 + 저장 통합 규칙 (v6.0 - KeyPath 기반)
    
    kind: 아이템 종류
        - "image": 이미지 (URL 다운로드 또는 bytes 저장)
        - "text": 텍스트 (str 저장)
        - "file": 파일 (URL 다운로드 또는 bytes 저장)
    
    source: 값을 추출할 KeyPath
        - "product__images": product.images에서 추출
        - "sku__options[*]__name": sku.options 배열의 각 name 추출
        - "__" 구분자 사용 (프로젝트 표준)
    
    Examples:
        >>> policy = ItemPostProcessPolicy(
        ...     kind="image",
        ...     source="product__images",
        ...     directory=Path("output/images")
        ... )
    """
    
    kind: ItemKind = Field(..., description="Item kind (image/text/file)")
    source: str = Field(..., description="KeyPath to extract value (product__images, title)")
    directory: Optional[Path] = Field(
        None, 
        description="Target directory (None = path_utils.downloads())"
    )
    name: FSONamePolicy = Field(
        default_factory=lambda: FSONamePolicy(
            as_type="file",
            suffix="_processed",
            tail_mode="counter",
            ensure_unique=True,
        ),  # type: ignore
        description="FSO name policy for item naming"
    )
    ops: FSOOpsPolicy = Field(
        default_factory=lambda: FSOOpsPolicy(
            as_type="file",
            exist=ExistencePolicy(create_if_missing=True, overwrite=True),  # type: ignore
            ext=FileExtensionPolicy(default_ext=".json"),  # type: ignore
        ),  # type: ignore
        description="FSO operations policy for item"
    )



@dataclass(slots=True)
class ItemList:
    """정규화된 아이템 (Extract → Save 중간 데이터 모델)

    ItemPostProcessor가 Extract 결과(Dict)를 ItemList로 변환하고,
    PostProcessor가 ItemList를 파일로 저장합니다.

    데이터 흐름:
        Extract (Dict) 
            ↓ ItemPostProcessor.process()
        ItemList (타입 + 값 + 메타데이터)
            ↓ PostProcessor.save_items()
        ItemSaveResult (저장 결과)
    
    Attributes:
        kind: 아이템 종류 (image/text/file)
        value: 실제 값 (URL, text, bytes)
        directory: 저장 디렉토리
        name: FSONamePolicy (파일명 정책)
        ops: FSOOpsPolicy (파일 작업 정책)
        
        record_index: Extract 결과의 몇 번째 record인지
            - 1-based index
            - 예: extracted_data[0] → record_index=1
            - Jinja2에서 사용: {{item.record}}
        
        item_index: 해당 record 내에서 몇 번째 item인지
            - 1-based index
            - explode=True로 리스트 분리 시 자동 증가
            - 예: images[0] → item_index=1, images[1] → item_index=2
            - Jinja2에서 사용: {{item.index}}
    
    """
    kind: ItemKind
    value: Any
    directory: Optional[Path]
    name: Any  # FSONamePolicy
    ops: Any  # FSOOpsPolicy
    record_index: int = 0
    item_index: int = 0

@dataclass(slots=True)
class ItemSaveResult:
    """파일 저장 결과 (PostProcessor 출력)

    PostProcessor.save_items()가 각 ItemList를 파일로 저장한 후,
    저장 결과를 ItemSaveResult로 반환합니다.
    
    Attributes:
        path: 저장된 파일 경로
            - status="saved": 실제 저장된 경로
            - status="skipped": Path() (빈 경로)
            - status="failed": Path() (빈 경로)
        
        item: 원본 ItemSaveMeta
            - 저장 대상이었던 아이템 (참조)
            - 실패 시 디버깅용
        
        status: 저장 상태
            - "saved": 성공적으로 저장됨
            - "skipped": 건너뜀 (metadata 없음, 조건 미충족 등)
            - "failed": 실패 (네트워크 오류, 권한 오류 등)
        
        detail: 상세 정보 (선택적)
            - status="saved": None 또는 "Downloaded 1.2MB"
            - status="skipped": "No metadata", "Empty value" 등
            - status="failed": 예외 메시지 (str(exc))
    
    Examples:
        >>> # 성공
        >>> artifact = ItemSaveResult(
        ...     path=Path("m:/output/images/product_001.jpg"),
        ...     item=item_save_meta,
        ...     status="saved"
        ... )
        
        >>> # 건너뜀
        >>> artifact = ItemSaveResult(
        ...     path=Path(),
        ...     item=item_save_meta,
        ...     status="skipped",
        ...     detail="No metadata"
        ... )
        
        >>> # 실패
        >>> artifact = ItemSaveResult(
        ...     path=Path(),
        ...     item=item_save_meta,
        ...     status="failed",
        ...     detail="HTTPError: 404 Not Found"
        ... )
    """
    path: Path
    item: ItemList
    status: Literal["saved", "skipped", "failed"] = "saved"
    detail: Optional[str] = None


@dataclass(slots=True)
class ItemSaveSummary:
    """파일 저장 결과 요약 (PostProcessor 최종 출력)
    
    PostProcessor.save_many()가 여러 NormalizedItem을 저장한 후,
    kind별로 그룹화된 ItemSaveResult 리스트를 ItemSaveSummary로 반환합니다.
    
    Attributes:
        artifacts: kind별 ItemSaveResult 리스트
            - 구조: {"image": [...], "text": [...], "file": [...]}
            - 각 kind별로 저장 결과가 그룹화됨
    
    Methods:
        flatten(): 모든 artifact를 단일 리스트로 평탄화
            Returns: List[ItemSaveResult]
        
        __getitem__(kind): 특정 kind의 artifact만 조회
            Args: kind (ItemKind): "image", "text", "file"
            Returns: List[ItemSaveResult]
    
    Examples:
        >>> summary = ItemSaveSummary(
        ...     artifacts={
        ...         "image": [
        ...             ItemSaveResult(Path("img1.jpg"), item1, "saved"),
        ...             ItemSaveResult(Path("img2.jpg"), item2, "saved"),
        ...         ],
        ...         "text": [
        ...             ItemSaveResult(Path("title.txt"), item3, "saved"),
        ...         ],
        ...         "file": []
        ...     }
        ... )
        
        >>> # 모든 artifact 조회
        >>> all_artifacts = summary.flatten()
        >>> print(len(all_artifacts))  # 3
        
        >>> # 이미지만 조회
        >>> images = summary["image"]
        >>> print(len(images))  # 2
        
        >>> # 저장 성공한 파일 경로만 추출
        >>> saved_paths = [
        ...     a.path for a in summary.flatten() 
        ...     if a.status == "saved"
        ... ]
        
        >>> # 실패한 항목 분석
        >>> failed = [
        ...     (a.item.value, a.detail) 
        ...     for a in summary.flatten() 
        ...     if a.status == "failed"
        ... ]
    """
    artifacts: Dict[str, List[ItemSaveResult]]

    def flatten(self) -> List[ItemSaveResult]:
        """모든 kind의 artifact를 단일 리스트로 평탄화
        
        Returns:
            List[ItemSaveResult]: 모든 artifact (순서: image → text → file)
        """
        return [artifact for group in self.artifacts.values() for artifact in group]

    def __getitem__(self, kind: ItemKind) -> List[ItemSaveResult]:
        """특정 kind의 artifact만 조회
        
        Args:
            kind: "image", "text", "file"
        
        Returns:
            List[ItemSaveResult]: 해당 kind의 artifact (없으면 빈 리스트)
        """
        return self.artifacts.get(kind, [])




# =============================================================================
# Unified Policy for SyncCrawl Adapter (OTO Pattern)
# =============================================================================

class SyncCrawlPolicy(PolicyBase):
    """SyncCrawl Adapter 통합 Policy (OTO 패턴)
    
    translate_utils의 TranslatorPolicy, image_utils의 ImageLoaderPolicy와 동일한 구조:
    - webdriver_manager: WebDriver 설정 (WebDriverManagerPolicy)
    - crawl: 크롤링 설정 (CrawlPolicy)
    - preset: PresetManager에서 사용할 preset 이름 (정책 레벨 기본값)
    
    ConfigLoader 사용 시:
        ```yaml
        # config_loader_crawl.yaml
        source:
          - src: ["{{configs_crawl_dir}}/webdriver_manager.yaml", "webdriver_manager"]
          - src: ["{{configs_crawl_dir}}/sync_crawl.yaml", "crawl"]
          - src: ["{{configs_logs_dir}}/crawl_parent.yaml", "log"]
        
        # sync_crawl.yaml
        preset: "aliexpress_china"  # ✅ 정책 레벨 preset 지정
        ```
    
    Python 사용:
        ```python
        from cfg_utils import ConfigLoader
        from crawl_utils.adapter import SyncCrawl
        
        config = ConfigLoader("configs/loader/config_loader_crawl.yaml")
        crawl = SyncCrawl(cfg_like=config.to_dict())  # ✅ 단일 cfg_like
        
        # Override preset via **overrides
        crawl = SyncCrawl(
            cfg_like=config.to_dict(),
            preset="taobao_fast"  # KeyPath override
        )
        ```
    """
    name: str = Field(default="sync_crawl", description="Section name in YAML config")
    webdriver_manager: Any = Field(
        default=None,
        description="WebDriver manager configuration (WebDriverManagerPolicy)"
    )
    # Site/Method 정보 (PresetManager.analyze_url()로 자동 결정)
    site: str = Field(default="", description="Site identifier (auto-detected)")
    method: str = Field(default="", description="Method identifier (auto-detected)")
    
    # === 계층화된 정책들 ===
    # ✅ 새로 연결: WD 이후 실행 계층 정책들(옵션)
    session_bridge: Optional[SessionBridgePolicy] = Field(
        default=None,
        description="세션 브리지 정책 (없으면 런타임에서 PRESET/URL 기반 자동 추론)"
    )

    http_session: Optional[HttpSessionPolicy] = Field(
        default=None,
        description="HTTP 세션 정책 (없으면 디폴트 세션으로 동작)"
    )

    cookie_bridge: Optional[CookieBridgePolicy] = Field(
        default=None,
        description="쿠키 브리지 정책 (없으면 lazy sync만 수행)"
    )

    # 이미 포함되어 있는 RetryPolicy는 그대로 둡니다.
    retry: Optional[RetryPolicy] = Field(
        default=None,
        description="재시도 정책"
    )
    # Navigation (Optional - search 메서드용)
    navigation: Optional[NavigationPolicy] = Field(
        default=None,
        description="페이지 네비게이션 설정 (search 메서드 필수)"
    )
    
    # Scroll, Extractor, Wait (기본값 제공)
    scroll: ScrollPolicy = Field(
        default_factory=ScrollPolicy,  # pyright: ignore[reportArgumentType]
        description="스크롤 전략 설정"
    )

    wait: WaitPolicy = Field(
        default_factory=WaitPolicy,  # pyright: ignore[reportArgumentType]
        description="대기 조건 설정"
    )

    extractor: ExtractorPolicy = Field(
        default_factory=ExtractorPolicy,  # pyright: ignore[reportArgumentType]
        description="데이터 추출 설정"
    )

    # Normalization Rules (v6.0 - KeyPath 기반)
    save: List[ItemPostProcessPolicy] = Field(
        default_factory=list,
        description="ItemPostProcessPolicy 리스트 (Extract + Save 통합 규칙)"
    )

    # Logging (Optional)
    log: Optional[LogPolicy] = Field(
        None,
        description="로깅 설정 (Optional, config_loader에서 주입 가능)"
    )
    @model_validator(mode="before")
    @classmethod
    def validate_webdriver_manager(cls, values):
        """WebDriverManagerPolicy 지연 import 및 검증
        
        Circular import 방지를 위해 @model_validator에서 import
        """
        if isinstance(values, dict) and "webdriver_manager" not in values:
            # Import here to avoid circular imports
            from crawl_utils.provider.policy import WebDriverManagerPolicy
            values["webdriver_manager"] = WebDriverManagerPolicy().model_dump()  # type: ignore
        
        return values
    
    @model_validator(mode="after")
    def validate_policy(self):
        """WebDriverManagerPolicy 타입 검증 (after mode)"""
        # Import here to avoid circular imports
        from crawl_utils.provider.policy import WebDriverManagerPolicy
        
        if self.webdriver_manager is None:
            self.webdriver_manager = WebDriverManagerPolicy()  # type: ignore
        elif isinstance(self.webdriver_manager, dict):
            self.webdriver_manager = WebDriverManagerPolicy(**self.webdriver_manager)
        
        return self

# class CrawlPolicy(PolicyBase):
#     name: str = Field(default="crawl", description="Section name in YAML config")
#     # Execution (mode, concurrency)
#     execution: ExecutionPolicy = Field(
#         default_factory=lambda: ExecutionPolicy(),
#         description="실행 정책 (mode, concurrency)"
#     )