# -*- coding: utf-8 -*-
# crawl_utils/services/entry_points/detail.py
"""
DetailEntryPoint - 상세페이지 크롤링 전용 엔트리포인트

단일 상품의 상세 URL을 입력받아:
1. 상세페이지 접근
2. JS 실행으로 데이터 추출
3. SmartNormalizer로 자동 타입 추론 정규화
4. FileSaver로 저장

사용 예시:
    >>> from crawl_utils.services.entry_points import DetailEntryPoint
    >>> from crawl_utils.services import SeleniumNavigator, SeleniumAdapter
    >>> from crawl_utils.provider import create_webdriver
    >>> 
    >>> # 브라우저 생성
    >>> driver = create_webdriver("firefox", "configs/firefox.yaml")
    >>> adapter = SeleniumAdapter(driver)
    >>> navigator = SeleniumNavigator(adapter, policy)
    >>> 
    >>> # 상세페이지 크롤링
    >>> entry_point = DetailEntryPoint(navigator, policy)
    >>> summary = await entry_point.run(
    ...     url="https://item.taobao.com/item.htm?id=123456",
    ...     product_id="nike_air_max"
    ... )
    >>> 
    >>> print(f"이미지: {len(summary['image'])}개")
    >>> print(f"텍스트: {len(summary['text'])}개")
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs

from ...core.interfaces import Navigator, ResourceFetcher
from ...core.models import SaveSummary
from ...core.policy import CrawlPolicy, ExtractorType
from ..smart_normalizer import SmartNormalizer
from ..saver import FileSaver
from ..fetcher import HTTPFetcher


class DetailEntryPoint:
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
        policy: CrawlPolicy,
        fetcher: Optional[ResourceFetcher] = None,
    ):
        """
        DetailEntryPoint 초기화
        
        Args:
            navigator: SeleniumNavigator 등 페이지 탐색 담당 객체
            policy: CrawlPolicy (wait, extractor, storage 설정)
            fetcher: HTTPFetcher 등 리소스 다운로드 담당 (None이면 기본 HTTPFetcher 생성)
        """
        self.navigator = navigator
        self.policy = policy
        self.fetcher = fetcher or HTTPFetcher()
        
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
