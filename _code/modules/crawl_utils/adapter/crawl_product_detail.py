# -*- coding: utf-8 -*-
"""
CrawlProductDetail - 상세페이지 크롤링 전용 어댑터 엔트리포인트

단일 상품 상세 URL을 대상으로 다음을 수행:
1) 페이지 로드 → 2) 대기 → 3) JS 실행으로 데이터 추출 → 4) SmartNormalizer 정규화 → 5) FileSaver 저장

예시:
    >>> from crawl_utils.adapter.crawl_product_detail import CrawlProductDetail, CrawlProductDetailPolicy
    >>> from crawl_utils.services import SeleniumNavigator, SeleniumAdapter
    >>> from crawl_utils.core.policy import StoragePolicy, StorageTargetPolicy
    >>> from crawl_utils.provider import create_webdriver
    >>> driver = create_webdriver("firefox", "configs/firefox.yaml")
    >>> adapter = SeleniumAdapter(driver)
    >>> policy = CrawlProductDetailPolicy(
    ...     storage=StoragePolicy(
    ...         image=StorageTargetPolicy(base_dir="_output/detail/images"),
    ...         text=StorageTargetPolicy(base_dir="_output/detail/text"),
    ...     )
    ... )
    >>> navigator = SeleniumNavigator(adapter, policy)
    >>> entry = CrawlProductDetail(navigator, policy)
    >>> summary = await entry.run("https://item.taobao.com/item.htm?id=123456")
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs

from ..core.interfaces import Navigator, ResourceFetcher
from ..core.models import SaveSummary
from ..core.policy import (
    WaitPolicy,
    ExtractorPolicy,
    StoragePolicy,
    HttpSessionPolicy,
    ExtractorType,
)
from ..services.smart_normalizer import SmartNormalizer
from ..services.saver import FileSaver
from ..services.fetcher import HTTPFetcher
from pydantic import BaseModel, Field


class CrawlProductDetailPolicy(BaseModel):
    """상세페이지 전용 정책 (중복 최소화)

    기존 공용 정책 모델(WaitPolicy, ExtractorPolicy, StoragePolicy, HttpSessionPolicy)을 조합하여
    상세 크롤링에 필요한 설정만 담습니다. SmartNormalizer 사용으로 정규화 규칙은 불필요합니다.

    Fields:
        wait: 콘텐츠 로딩 대기 정책
        extractor: 추출 정책 (기본은 DOM, 권장: JS로 변경)
        storage: 저장 정책 (image/text/file 대상으로 경로/이름 정책)
        http_session: HTTP 페칭에 사용할 헤더/세션 정책
    """

    wait: WaitPolicy = Field(default_factory=WaitPolicy)
    extractor: ExtractorPolicy = Field(default_factory=ExtractorPolicy)
    storage: StoragePolicy
    http_session: HttpSessionPolicy = Field(default_factory=HttpSessionPolicy)


class CrawlProductDetail:
    """
    상세페이지 크롤링 엔트리포인트
    
    단일 상품 URL을 입력받아 자동으로:
    - 페이지 접근 및 대기
    - JS 실행으로 데이터 추출
    - SmartNormalizer로 타입 자동 추론 정규화
    - FileSaver로 파일 저장
    
    Attributes:
        navigator: 페이지 탐색 및 JS 실행 담당
        policy: 크롤링 정책 (wait, extractor, storage 설정)
        fetcher: HTTP 리소스 다운로드 담당
        normalizer: SmartNormalizer (자동 타입 추론)
        saver: FileSaver (파일 저장)
    """
    
    def __init__(
        self,
        navigator: Navigator,
        policy: CrawlProductDetailPolicy,
        fetcher: Optional[ResourceFetcher] = None,
    ):
        """
        CrawlProductDetail 초기화
        
        Args:
            navigator: SeleniumNavigator 등 페이지 탐색 담당 객체
            policy: CrawlProductDetailPolicy (wait, extractor, storage, http_session)
            fetcher: HTTPFetcher 등 리소스 다운로드 담당 (None이면 기본 HTTPFetcher 생성)
        """
        self.navigator = navigator
        self.policy = policy
        self.fetcher = fetcher or self._create_fetcher()
        
        # SmartNormalizer 사용 (자동 타입 추론)
        self.normalizer = SmartNormalizer()
        
        # FileSaver 사용
        self.saver = FileSaver(policy.storage)
    
    async def run(
        self,
        url: str,
        *,
        product_id: Optional[str] = None,
        section: Optional[str] = None,
        name_prefix: Optional[str] = None,
    ) -> SaveSummary:
        """
        상세 URL로 크롤링 실행
        
        전체 파이프라인:
        1. 상세페이지 접근 (load)
        2. 콘텐츠 로딩 대기 (wait)
        3. JS 실행으로 데이터 추출 (extract)
        4. SmartNormalizer로 자동 정규화 (normalize)
        5. FileSaver로 저장 (save)
        
        Args:
            url: 상세페이지 URL (예: https://item.taobao.com/item.htm?id=123456)
            product_id: 상품 ID (None이면 URL에서 자동 추출)
            section: 섹션 이름 (None이면 product_id 사용)
            name_prefix: 파일명 접두사 (None이면 product_id 사용)
        
        Returns:
            SaveSummary: 저장 결과 요약 (kind별 SavedArtifact 리스트)
        
        Examples:
            >>> # 기본 사용
            >>> summary = await entry_point.run("https://item.taobao.com/item.htm?id=123456")
            >>> 
            >>> # product_id 명시
            >>> summary = await entry_point.run(
            ...     "https://item.taobao.com/item.htm?id=123456",
            ...     product_id="nike_air_max_2024"
            ... )
            >>> 
            >>> # 섹션/접두사 커스터마이징
            >>> summary = await entry_point.run(
            ...     "https://item.taobao.com/item.htm?id=123456",
            ...     section="taobao_product_123456",
            ...     name_prefix="nike_shoes"
            ... )
        """
        # 1. 상세페이지 접근
        await self.navigator.load(url)
        
        # 2. 콘텐츠 로딩 대기
        await self._wait_for_content()
        
        # 3. JS 실행으로 데이터 추출
        extracted = await self._extract_detail_data()
        
        # 4. product_id 결정 (명시되지 않으면 URL에서 추출)
        if product_id is None:
            product_id = self._extract_id_from_url(url)
        
        # 5. section/name_prefix 결정
        final_section = section or product_id
        final_name_prefix = name_prefix or product_id
        
        # 6. SmartNormalizer로 자동 정규화
        items = self.normalizer.normalize(
            extracted,
            section=final_section,
            name_prefix=final_name_prefix,
        )
        
        # 7. FileSaver로 저장
        summary = await self.saver.save_many(items, self.fetcher)
        
        return summary
    
    async def _wait_for_content(self) -> None:
        """
        콘텐츠 로딩 대기
        
        CrawlPolicy의 WaitPolicy에 따라 대기:
        - WaitHook.NONE: 대기 안 함
        - WaitHook.CSS: CSS selector로 대기
        - WaitHook.XPATH: XPath로 대기
        """
        await self.navigator.wait(
            self.policy.wait.hook,
            self.policy.wait.selector,
            self.policy.wait.timeout_sec,
            self.policy.wait.condition.value,
        )
    
    async def _extract_detail_data(self) -> Dict[str, Any]:
        """
        JS 실행으로 상세 데이터 추출
        
        CrawlPolicy의 ExtractorPolicy에 따라 추출:
        - ExtractorType.JS: js_snippet 실행 (권장)
        - ExtractorType.DOM: DOM 파싱
        - ExtractorType.API: API 호출
        
        Returns:
            Dict[str, Any]: 추출된 데이터
                예: {"images": [...], "title": "...", "price": "...", ...}
        
        Notes:
            - JS snippet이 Dict를 반환하면 그대로 사용
            - List를 반환하면 첫 번째 요소 사용
            - 그 외는 빈 Dict 반환
        """
        # JS Extractor 사용 (권장)
        if self.policy.extractor.type == ExtractorType.JS:
            snippet = self.policy.extractor.js_snippet
            if snippet:
                result = await self.navigator.execute_js(snippet)
                
                # Dict 반환 → 그대로 사용
                if isinstance(result, dict):
                    return result
                
                # List 반환 → 첫 번째 요소 사용
                if isinstance(result, list) and len(result) > 0:
                    first_item = result[0]
                    if isinstance(first_item, dict):
                        return first_item
        
        # DOM/API Extractor는 상세페이지에서 비권장
        # (검색 결과 페이지에서 주로 사용)
        
        return {}
    
    def _extract_id_from_url(self, url: str) -> str:
        """
        URL에서 상품 ID 추출
        
        다양한 패턴 지원:
        1. Query parameter: ?id=123, ?itemid=456, ?productid=789
        2. Path 숫자: /item/123456/detail
        3. 기본값: "unknown"
        
        Args:
            url: 상세페이지 URL
        
        Returns:
            str: 추출된 상품 ID 또는 "unknown"
        
        Examples:
            >>> _extract_id_from_url("https://item.taobao.com/item.htm?id=123456")
            "123456"
            
            >>> _extract_id_from_url("https://coupang.com/products/123456")
            "123456"
            
            >>> _extract_id_from_url("https://example.com/unknown")
            "unknown"
        """
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        
        # 1. Query parameter에서 ID 추출
        for key in ["id", "itemid", "productid", "pid", "item_id", "product_id"]:
            if key in query:
                return query[key][0]
        
        # 2. Path에서 숫자 추출
        numbers = re.findall(r'\d+', parsed.path)
        if numbers:
            # 가장 긴 숫자 사용 (일반적으로 상품 ID가 길다)
            return max(numbers, key=len)
        
        # 3. 기본값
        return "unknown"

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _create_fetcher(self) -> HTTPFetcher:
        """정책의 http_session 설정을 반영하여 HTTPFetcher 생성"""
        headers = self._load_session_headers()
        return HTTPFetcher(default_headers=headers)

    def _load_session_headers(self) -> Dict[str, str]:
        """HttpSessionPolicy 기반으로 헤더 로드/병합"""
        http_policy = self.policy.http_session
        headers: Dict[str, str] = dict(http_policy.headers)
        path = http_policy.session_json_path
        if http_policy.use_browser_headers and path:
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    source = data.get("headers") if isinstance(data.get("headers"), dict) else data
                    if isinstance(source, dict):
                        headers = {**{k: v for k, v in source.items() if isinstance(v, str)}, **headers}
            except FileNotFoundError:
                pass
            except Exception:
                pass
        return headers
