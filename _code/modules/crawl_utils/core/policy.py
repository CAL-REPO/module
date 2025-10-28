# -*- coding: utf-8 -*-
# crawl_utils/core/policy.py
# Crawl utilities policy definitions

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Literal, Any, TYPE_CHECKING, Tuple, Set

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator
from pydantic.dataclasses import dataclass

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
    base_url: Optional[HttpUrl] = None
    url_template: Optional[str] = None
    params: Dict[str, str | int | float] = Field(default_factory=dict)
    page_param: str = Field("page", min_length=1)
    start_page: int = Field(1, ge=1)
    max_pages: int = Field(1, ge=1)

class ScrollStrategy(str, Enum):
    NONE = "none"
    PAGINATE = "paginate"
    STEP = "step"
    INFINITE = "infinite"

class ScrollPolicy(PolicyBase):
    strategy: ScrollStrategy = Field(ScrollStrategy.NONE, description="Scroll strategy")
    scroll_count: Optional[int] = Field(None, ge=0, description="Fixed scroll count (site-specific)")
    max_scrolls: int = Field(0, ge=0, description="Maximum scroll attempts")
    scroll_step_px: int = Field(600, ge=1, description="Scroll distance per step (pixels)")
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
# Item Policy (v7.0 - 정책 분리 및 구조 개선)
# =============================================================================
ItemKind = Literal["image", "text", "file"]

class CrawlItemSourcePolicy(PolicyBase):
    """크롤 아이템 추출 정책 (Source Policy)
    
    책임:
    - 추출 규칙 정의 (어떤 데이터를 추출할 것인가?)
    - KeyPath 기반 source 정의
    - kind 타입 지정
    
    설계 원칙:
    - 추출 규칙에만 집중 (저장 규칙과 분리)
    - Required 필드만 포함 (kind, source)
    - 명확한 책임 (SRP 준수)
    
    Examples:
        >>> # 이미지 추출
        >>> policy = CrawlItemSourcePolicy(
        ...     kind="image",
        ...     source="product__images"
        ... )
        
        >>> # 배열 순회
        >>> policy = CrawlItemSourcePolicy(
        ...     kind="text",
        ...     source="sku__options[*]__name"
        ... )
    """
    
    kind: ItemKind = Field(
        ...,
        description="아이템 종류 (image/text/file)"
    )
    source: str | bytes = Field(
        ...,
        description="KeyPath to extract value (product__images, sku__options[*]__name)"
    )

class CrawlItemSavePolicy(PolicyBase):
    """크롤 아이템 저장 정책 (Save Policy)
    
    책임:
    - 저장 규칙 정의 (어디에, 어떻게 저장할 것인가?)
    - FSO 정책 캡슐화 (FSONamePolicy, FSOOpsPolicy)
    - 저장 위치 지정 (dir_path)
    
    설계 원칙:
    - 저장 규칙에만 집중 (추출 규칙과 분리)
    - FSO 정책을 내부에 캡슐화 (외부에서 직접 참조 안함)
    - 기본값 제공 (default_factory)
    
    후처리 우선순위:
        ItemNormalizer 자동 추론 (filename, extension)
        ← YAML data override
        ← Preset override
        ← Runtime override (최우선)
    
    Examples:
        >>> # 기본 저장 정책
        >>> policy = CrawlItemSavePolicy(
        ...     dir_path=Path("output/images"),
        ...     fso_name=FSONamePolicy(
        ...         prefix="CAPEA",
        ...         name="product",
        ...         extension="jpg"
        ...     ),
        ...     fso_ops=FSOOpsPolicy(overwrite=False)
        ... )
        
        >>> # 자동 추론 활용 (name, extension 비워두기)
        >>> policy = CrawlItemSavePolicy(
        ...     dir_path=None,  # downloads()
        ...     fso_name=FSONamePolicy(
        ...         prefix="CAPEA",
        ...         name="",        # ← ItemNormalizer가 URL에서 추론
        ...         extension=""    # ← ItemNormalizer가 URL에서 추론
        ...     )
        ... )
    """
    
    dir_path: Optional[Path] = Field(
        None,
        description="저장 디렉토리 (None = path_utils.downloads())"
    )
    fso_name: FSONamePolicy = Field(
        default_factory=FSONamePolicy,  # type: ignore
        description="파일명 정책 (FSO 모듈)"
    )
    fso_ops: FSOOpsPolicy = Field(
        default_factory=FSOOpsPolicy,  # type: ignore
        description="파일 작업 정책 (FSO 모듈)"
    )

class CrawlItemPolicy(CrawlItemSourcePolicy, CrawlItemSavePolicy):
    """크롤 아이템 통합 정책 (Item Policy)
    
    책임:
    - 추출 규칙 + 저장 규칙 통합
    - SyncCrawlPolicy.save에 포함
    - 정책 계층 구조 정의
    
    구조:
        CrawlItemPolicy
        ├── source_policy: CrawlItemSourcePolicy (추출 규칙)
        └── save_policy: CrawlItemSavePolicy (저장 규칙)
    
    설계 원칙:
    - 명확한 분리 (source vs save)
    - 독립적 변경 가능 (추출 규칙 ↔ 저장 규칙)
    - 재사용성 (source_policy, save_policy 독립적으로 재사용)
    
    데이터 흐름:
        1. CrawlItemPolicy (정책 정의) → SyncCrawlPolicy.save
        2. ItemPostProcessor (KeyPath 추출) → source_policy.source
        3. ItemNormalizer (자동 추론) → save_policy 보완
        4. Override 적용 (후처리 > YAML > Preset > Runtime)
        5. CrawlItems 생성 (런타임 데이터)
        6. ItemSaver (파일 저장)
    
    Examples:
        >>> # 이미지 크롤링 정책
        >>> policy = CrawlItemPolicy(
        ...     source_policy=CrawlItemSourcePolicy(
        ...         kind="image",
        ...         source="product__images"
        ...     ),
        ...     save_policy=CrawlItemSavePolicy(
        ...         dir_path=Path("output/images"),
        ...         name=FSONamePolicy(
        ...             prefix="CAPEA",
        ...             name="product",
        ...             tail_mode="counter"
        ...         )
        ...     )
        ... )
        
        >>> # YAML 정의
        >>> # save:
        >>> #   - source_policy:
        >>> #       kind: "image"
        >>> #       source: "product__images"
        >>> #     save_policy:
        >>> #       dir_path: null
        >>> #       fso_name:
        >>> #         prefix: "CAPEA"
        >>> #         name: ""  # ItemNormalizer가 자동 추론
    """
    

@dataclass
class CrawlItem:
    """크롤 아이템 런타임 데이터 (v7.0 - Policy와 분리)
    
    책임:
    - 런타임 데이터 저장 (Policy와 분리)
    - 원본 source 보존 (세션 기반 다운로드 지원)
    - 후처리 결과 저장
    
    설계 원칙:
    - Policy(BaseModel) vs Data(dataclass) 명확히 분리
    - source를 원본 그대로 보존 (URL 또는 bytes)
    - 타입 안전성 (TypedDict → dataclass)
    
    후처리 흐름:
        1. Extractor: KeyPath 추출 → raw source
        2. ItemNormalizer: 자동 추론 (filename, extension)
        3. Override 적용: YAML < Preset < Runtime
        4. CrawlItems 생성: 최종 런타임 데이터
        5. ItemSaver: 파일 저장
    
    Attributes:
        kind: 아이템 종류 (image/text/file)
        
        source: 원본 소스 (추출된 그대로)
            - URL (str): 세션 기반 다운로드 필요
            - bytes: 이미 다운로드된 데이터
            - text (str): 텍스트 데이터
            - ⚠️ 원본 보존 필수! (세션 쿠키, 헤더 등 활용)
        
        dir_path: 저장 디렉토리
            - None: path_utils.downloads()
            - Path: 사용자 지정 경로
        
        name: 파일명 정책 (FSONamePolicy)
            - ItemNormalizer가 자동 추론한 값 포함
            - Override 우선순위: Runtime > Preset > YAML > 후처리
        
        ops: 파일 작업 정책 (FSOOpsPolicy)
            - overwrite, unique, mkdir 등
    
    Examples:
        >>> # 이미지 URL (세션 기반 다운로드 필요)
        >>> item = CrawlItems(
        ...     kind="image",
        ...     source="https://example.com/product/image.jpg",
        ...     dir_path=Path("output/images"),
        ...     fso_name=FSONamePolicy(
        ...         prefix="CAPEA",
        ...         name="product",  # ← ItemNormalizer가 URL에서 추론
        ...         extension="jpg"  # ← ItemNormalizer가 URL에서 추론
        ...     ),
        ...     fso_ops=FSOOpsPolicy(overwrite=False),
        ...     record_index=1,
        ...     item_index=1
        ... )
        
        >>> # 텍스트 데이터
        >>> item = CrawlItems(
        ...     kind="text",
        ...     source="상품명: 테스트",
        ...     dir_path=Path("output/text"),
        ...     fso_name=FSONamePolicy(
        ...         prefix="CAPEA",
        ...         name="title",
        ...         extension="txt"
        ...     ),
        ...     fso_ops=FSOOpsPolicy(),
        ...     record_index=1,
        ...     item_index=1
        ... )
        
        >>> # bytes 데이터 (이미 다운로드됨)
        >>> item = CrawlItems(
        ...     kind="image",
        ...     source=b"\x89PNG...",  # bytes
        ...     dir_path=Path("output/images"),
        ...     fso_name=FSONamePolicy(
        ...         prefix="CAPEA",
        ...         name="screenshot",
        ...         extension="png"
        ...     ),
        ...     fso_ops=FSOOpsPolicy(),
        ...     record_index=1,
        ...     item_index=1
        ... )
    """
    source_policy: CrawlItemSourcePolicy = Field(
        default_factory=CrawlItemSourcePolicy, # type: ignore
        description="추출 정책 (kind, source)"
    )
    save_policy: CrawlItemSavePolicy = Field(
        default_factory=CrawlItemSavePolicy,  # type: ignore
        description="저장 정책 (dir_path, fso_name, fso_ops)"
    )
    # runtime indices (set dynamically by ItemsNormalizer)
    record_index: int = 0
    item_index: int = 0

    # Compatibility properties (flattened accessors used by legacy saver/tests)
    @property
    def kind(self) -> ItemKind:
        return self.source_policy.kind

    @kind.setter
    def kind(self, v: ItemKind) -> None:
        try:
            self.source_policy.kind = v
        except Exception:
            pass

    @property
    def source(self) -> str | bytes:
        return self.source_policy.source

    @source.setter
    def source(self, v: str | bytes) -> None:
        try:
            self.source_policy.source = v
        except Exception:
            pass

    @property
    def dir_path(self) -> Optional[Path]:
        return self.save_policy.dir_path

    @dir_path.setter
    def dir_path(self, v: Optional[Path]) -> None:
        try:
            self.save_policy.dir_path = v
        except Exception:
            pass

    @property
    def fso_name(self):
        return self.save_policy.fso_name

    @fso_name.setter
    def fso_name(self, v) -> None:
        try:
            self.save_policy.fso_name = v
        except Exception:
            pass

    @property
    def fso_ops(self):
        return self.save_policy.fso_ops

    @fso_ops.setter
    def fso_ops(self, v) -> None:
        try:
            self.save_policy.fso_ops = v
        except Exception:
            pass

    @property
    def name(self) -> str:
        try:
            return getattr(self.save_policy.fso_name, "name", "")
        except Exception:
            return ""

    @name.setter
    def name(self, v: str) -> None:
        try:
            setattr(self.save_policy.fso_name, "name", v)
        except Exception:
            pass

    @property
    def extension(self) -> str:
        try:
            return getattr(self.save_policy.fso_name, "extension", "")
        except Exception:
            return ""

    @extension.setter
    def extension(self, v: str) -> None:
        try:
            setattr(self.save_policy.fso_name, "extension", v)
        except Exception:
            pass


@dataclass(slots=True)
class ItemSaveResult:
    """파일 저장 결과 (PostProcessor 출력)

    PostProcessor.save_items()가 각 CrawlItems를 파일로 저장한 후,
    저장 결과를 ItemSaveResult로 반환합니다.
    
    ⚠️ v7.0 변경사항:
    - item: ItemList → CrawlItems (타입 변경)
    
    Attributes:
        path: 저장된 파일 경로
            - status="saved": 실제 저장된 경로
            - status="skipped": Path() (빈 경로)
            - status="failed": Path() (빈 경로)
        
        item: 원본 CrawlItems
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
        ...     item=crawl_items,
        ...     status="saved"
        ... )
        
        >>> # 건너뜀
        >>> artifact = ItemSaveResult(
        ...     path=Path(),
        ...     item=crawl_items,
        ...     status="skipped",
        ...     detail="No metadata"
        ... )
        
        >>> # 실패
        >>> artifact = ItemSaveResult(
        ...     path=Path(),
        ...     item=crawl_items,
        ...     status="failed",
        ...     detail="HTTPError: 404 Not Found"
        ... )
    """
    path: Path
    item: CrawlItem  # v7.0: ItemList → CrawlItem
    status: Literal["saved", "skipped", "failed"] = "saved"
    detail: Optional[str] = None


@dataclass(slots=True)
class ItemSaveSummary:
    """파일 저장 결과 요약
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
        default=None,  # pyright: ignore[reportArgumentType]
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

    # Normalization Rules (v7.0 - CrawlItemPolicy 기반)
    items: Optional[List[CrawlItemPolicy]] = Field(
        default_factory=list,
        description="CrawlItemPolicy 리스트 (v7.0)"
    )
    
    # KeyPath Settings (v8.0)
    keypath_separator: str = Field(
        default="__",
        description="KeyPath separator for flattening nested dicts (default: '__')"
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
