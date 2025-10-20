# -*- coding: utf-8 -*-
"""XlCrawl Policy - Excel + Crawl Pipeline Integration.

책임:
1. Excel 설정 (XlController)
2. Crawl 파이프라인 설정 (WebDriver, Navigation, Extractor, PostProcessor)
3. URL Preset Mapping (site + method → snippet + storage)
4. 통합 로그 정책
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from logs_utils.core.policy import LogPolicy
from crawl_utils.core.policy import (
    CrawlPolicy,
    NavigationPolicy,
    ScrollPolicy,
    ExtractorPolicy,
    WaitPolicy,
    HttpSessionPolicy,
    ExecutionMode,
)
from fso_utils.core.policy import FSONamePolicy, FSOOpsPolicy


# =============================================================================
# PostProcessor Policy (crawl_utils 확장)
# =============================================================================

class PostProcessorRule(BaseModel):
    """PostProcessor 규칙
    
    JS Extractor 결과를 KeyPath로 추출하여 FSOPathBuilder로 저장.
    
    Attributes:
        kind: 파일 종류 (image/text/file)
        source: JS 결과에서 추출할 KeyPath (예: 'items[*].url')
        static_section: 고정 섹션명 (파일 그룹화)
        allow_empty: 빈 값 허용 여부
        dynamic_subdir: 동적 하위 디렉토리 템플릿 (예: '{cas_no}')
        fso_name_policy: 파일명 생성 정책 (FSONamePolicy)
        fso_ops_policy: 파일 작업 정책 (FSOOpsPolicy)
    
    Examples:
        >>> rule = PostProcessorRule(
        ...     kind="image",
        ...     source="items[*].url",
        ...     static_section="ali_detail",
        ...     dynamic_subdir="{cas_no}",
        ...     fso_name_policy=FSONamePolicy(
        ...         prefix="DETAILED",
        ...         tail_mode="counter_datetime"
        ...     )
        ... )
    """
    kind: str = Field(..., description="File kind: image/text/file")
    source: str = Field(..., description="KeyPath to extract from JS result (e.g., 'items[*].url')")
    static_section: Optional[str] = Field(None, description="Fixed section name for grouping")
    allow_empty: bool = Field(False, description="Keep empty values")
    
    # Dynamic directory (CAS No 등)
    dynamic_subdir: Optional[str] = Field(
        None,
        description="Dynamic subdirectory template (e.g., '{cas_no}')"
    )
    
    # FSO 정책 (명시적 상속)
    fso_name_policy: FSONamePolicy = Field(..., description="File naming policy from fso_utils")
    fso_ops_policy: Optional[FSOOpsPolicy] = Field(None, description="File operations policy from fso_utils")


class PostProcessorPolicy(BaseModel):
    """PostProcessor 정책
    
    JS 추출 결과를 파일로 저장하는 정책.
    
    Attributes:
        target_dir: 기본 저장 디렉토리 (동적 CAS No 추가 가능)
        rules: PostProcessor 규칙 리스트
    
    Examples:
        >>> policy = PostProcessorPolicy(
        ...     target_dir=Path("_output/crawl/images"),
        ...     rules=[
        ...         PostProcessorRule(
        ...             kind="image",
        ...             source="items[*].url",
        ...             static_section="ali_detail",
        ...             dynamic_subdir="{cas_no}",
        ...             fso_name_policy=FSONamePolicy(prefix="DETAILED")
        ...         )
        ...     ]
        ... )
    """
    target_dir: Path = Field(
        default_factory=lambda: Path.cwd() / "_output" / "crawl",
        description="Base output directory (can be combined with dynamic_subdir)"
    )
    rules: List[PostProcessorRule] = Field(default_factory=list, description="PostProcessor rules")


# =============================================================================
# XlCrawl-specific Policies
# =============================================================================

class XlCrawlFilterPolicy(BaseModel):
    """Excel DataFrame 필터링 정책
    
    download 컬럼이 공백인 행의 CAS No를 추출합니다.
    
    Attributes:
        cas_column: CAS No 컬럼 별칭
        download_column: Download 컬럼 별칭
        url_column: URL 컬럼 별칭 (크롤링 대상)
    
    Examples:
        >>> filter_policy = XlCrawlFilterPolicy(
        ...     cas_column="CAS No",
        ...     download_column="download",
        ...     url_column="URL"
        ... )
    """
    cas_column: str = Field(default="CAS No", description="CAS No column alias")
    download_column: str = Field(default="download", description="Download column alias (should be blank)")
    url_column: str = Field(default="URL", description="URL column alias for crawling")


class PresetMappingRule(BaseModel):
    """URL Preset Mapping 규칙
    
    URL 패턴을 분석하여 site + method를 식별하고,
    해당하는 WebDriver/Crawl 설정을 선택합니다.
    
    Attributes:
        domain_pattern: 도메인 패턴 (예: "taobao\\.com", "aliexpress\\.com")
        site: 사이트명 (예: "taobao", "aliexpress")
        method: 크롤링 방법 (예: "detail", "search")
        crawl_config: Crawl 설정 파일 경로
        webdriver_config: WebDriver 설정 파일 경로
    
    Examples:
        >>> rule = PresetMappingRule(
        ...     domain_pattern="taobao\\\\.com",
        ...     site="taobao",
        ...     method="detail",
        ...     crawl_config="modules/crawl_utils/configs/crawl_site_taobao_detail.yaml",
        ...     webdriver_config="modules/crawl_utils/configs/firefox_taobao.yaml"
        ... )
    """
    domain_pattern: str = Field(..., description="Domain pattern (regex)")
    site: str = Field(..., description="Site name (e.g., 'taobao', 'aliexpress')")
    method: str = Field(..., description="Crawl method (e.g., 'detail', 'search')")
    crawl_config: str = Field(..., description="Crawl config file path")
    webdriver_config: str = Field(..., description="WebDriver config file path")


class PresetMappingPolicy(BaseModel):
    """URL Preset Mapping 정책
    
    xlcrawl_crawl.yaml의 구조를 파싱하여 URL → Preset 매핑을 관리합니다.
    
    Attributes:
        rules: Preset Mapping 규칙 리스트
    
    Examples:
        >>> mapping_policy = PresetMappingPolicy(
        ...     rules=[
        ...         PresetMappingRule(
        ...             domain_pattern="item.taobao.com",
        ...             site="taobao",
        ...             method="product_detail",
        ...             webdriver_config="firefox_taobao.yaml",
        ...             crawl_config="crawl_taobao_detail.yaml"
        ...         )
        ...     ]
        ... )
    """
    rules: List[PresetMappingRule] = Field(default_factory=list, description="Preset mapping rules")


# =============================================================================
# XlCrawl Policy (통합)
# =============================================================================

class XlCrawlPolicy(BaseModel):
    """XlCrawl Pipeline 통합 정책
    
    Excel에서 CAS No + URL 추출 → 크롤링 → 파일 저장 → Excel 업데이트
    
    XLOTO 패턴 참고:
    - filter: Excel 필터링 정책
    - preset_mapping: URL → Preset 매핑
    - log: 통합 로그 정책
    
    CrawlPolicy 상속 대신 조합 사용:
    - crawl: CrawlPolicy (기본 크롤링 설정)
    
    Attributes:
        name: Policy 이름
        filter: Excel 필터링 정책
        preset_mapping: URL Preset Mapping 정책
        crawl: 기본 Crawl 정책 (개별 preset에서 override)
        log: 통합 로그 정책
    
    Examples:
        >>> policy = XlCrawlPolicy(
        ...     name="xlcrawl",
        ...     filter=XlCrawlFilterPolicy(),
        ...     preset_mapping=PresetMappingPolicy(rules=[...]),
        ...     crawl=CrawlPolicy(...),
        ...     log=LogPolicy(...)
        ... )
    """
    name: str = Field("xlcrawl", description="Policy name")
    
    # XlCrawl 전용 정책
    filter: XlCrawlFilterPolicy = Field(
        default=XlCrawlFilterPolicy(),
        description="Excel filtering policy"
    )
    preset_mapping: PresetMappingPolicy = Field(
        default=PresetMappingPolicy(),
        description="URL → Preset mapping policy"
    )
    
    # 기본 Crawl 정책 (개별 preset에서 override 가능)
    # Note: CrawlPolicy를 직접 상속하지 않고 조합으로 사용
    # 각 preset(taobao_detail, aliexpress_search 등)이 개별 CrawlPolicy를 가짐
    crawl: Optional[CrawlPolicy] = Field(
        None,
        description="Default crawl policy (overridden by preset-specific configs)"
    )
    
    # 통합 로그 정책
    log: LogPolicy = Field(
        default_factory=lambda: LogPolicy(),
        description="XlCrawl integrated logging policy"
    )


__all__ = [
    # PostProcessor
    "PostProcessorRule",
    "PostProcessorPolicy",
    # XlCrawl
    "XlCrawlFilterPolicy",
    "PresetMappingRule",
    "PresetMappingPolicy",
    "XlCrawlPolicy",
]
