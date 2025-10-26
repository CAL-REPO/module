# # -*- coding: utf-8 -*-
# """crawl_utils/services/preprocessor.py

# PreProcessor Service - URL 분석 및 크롤링 정책 결정

# 역할:
# 1. URL 분석 → (site, method, region) 추출
# 2. Preset 크롤링 정책 로드 (site별 override)
# 3. WebDriver Override 로드 (region별 설정)
# 4. 최종 CrawlPolicy 생성 (기본값 + Preset + Override 병합)

# 사용 예시:
# ```python
# from crawl_utils.services.preprocessor import PreProcessor
# from crawl_utils.core.policy import CrawlPolicy

# # 기본 정책 로드 (YAML)
# base_policy = CrawlPolicy.from_yaml("configs/sync_crawl.yaml")

# # PreProcessor 생성
# preprocessor = PreProcessor(base_policy)

# # URL 분석 및 정책 결정
# url = "https://www.aliexpress.com/item/1234567890.html"
# final_policy = preprocessor.process(url)

# print(f"Site: {final_policy.site}, Method: {final_policy.method}")
# print(f"Extractor: {final_policy.extractor.type}")
# ```
# """

# from __future__ import annotations

# from typing import Optional, Tuple
# from pathlib import Path

# from ..core.policy import CrawlPolicy
# from ..presets import (
#     analyze_url,
#     get_preset,
#     get_webdriver_override,
# )


# class PreProcessor:
#     """PreProcessor Service - URL 분석 및 정책 결정
    
#     URL을 분석하여 Site/Method/Region을 추출하고,
#     해당 Preset 정책을 로드하여 최종 CrawlPolicy를 생성합니다.
    
#     Attributes:
#         base_policy: 기본 CrawlPolicy (YAML에서 로드)
#         enable_preset: Preset 사용 여부
#     """
    
#     def __init__(
#         self,
#         base_policy: CrawlPolicy,
#         *,
#         enable_preset: bool = True
#     ):
#         """Initialize PreProcessor.
        
#         Args:
#             base_policy: 기본 CrawlPolicy (YAML 로드)
#             enable_preset: Preset 사용 여부 (기본값: True)
#         """
#         self.base_policy = base_policy
#         self.enable_preset = enable_preset
    
#     def process(
#         self,
#         url: str,
#         *,
#         preset_name: Optional[str] = None,
#         provider: str = "firefox"
#     ) -> CrawlPolicy:
#         """URL 분석 및 최종 정책 생성
        
#         처리 순서:
#         1. URL 분석 → (site, method, region)
#         2. Preset 크롤링 정책 로드 (enable_preset=True일 때)
#         3. WebDriver Override 로드 (region별)
#         4. 이름 기반 Preset 로드 (preset_name 지정 시)
#         5. 최종 정책 병합 (base → preset → webdriver → named)
        
#         Args:
#             url: 크롤링할 URL
#             preset_name: 이름 기반 Preset (선택사항)
#             provider: WebDriver provider ("firefox", "chrome" 등)
        
#         Returns:
#             최종 CrawlPolicy (병합 완료)
        
#         Raises:
#             ValueError: URL 분석 실패 시
        
#         Example:
#             >>> preprocessor = PreProcessor(base_policy)
#             >>> policy = preprocessor.process("https://taobao.com/item/123.htm")
#             >>> print(policy.site, policy.method)
#             ('taobao', 'detail')
#         """
#         # 1. URL 분석
#         site, method, region = analyze_url(url)
        
#         # 2. 기본 정책 복사
#         final_policy_dict = self.base_policy.model_dump()
#         final_policy_dict["site"] = site
#         final_policy_dict["method"] = method
        
#         # 3. Preset 크롤링 정책 병합 (enable_preset=True)
#         if self.enable_preset:
#             crawl_preset = get_preset(site, method)
#             if crawl_preset:
#                 final_policy_dict = self._merge_policies(final_policy_dict, crawl_preset)
        
#         # 4. WebDriver Override 병합 (region별)
#         webdriver_override = get_webdriver_override(region, provider)
#         if webdriver_override:
#             # webdriver_override는 provider 전용 설정이므로 직접 사용 가능
#             # (현재 CrawlPolicy에는 webdriver_manager 필드가 없으므로 skip)
#             # TODO: SyncCrawlPolicy와 통합 시 webdriver_manager 필드 추가 필요
#             pass
        
#         # 5. 이름 기반 Preset 병합 (preset_name 지정 시)
#         if preset_name:
#             named_preset = get_named_preset(preset_name)
#             if named_preset:
#                 # KeyPath 형식 (crawl__timeout, webdriver_manager__region 등)
#                 final_policy_dict = self._apply_keypath_overrides(
#                     final_policy_dict,
#                     named_preset
#                 )
        
#         # 6. CrawlPolicy 생성
#         return CrawlPolicy(**final_policy_dict)
    
#     def _merge_policies(
#         self,
#         base: dict,
#         override: dict
#     ) -> dict:
#         """정책 병합 (Deep merge)
        
#         Args:
#             base: 기본 정책 dict
#             override: Override 정책 dict
        
#         Returns:
#             병합된 정책 dict
#         """
#         result = base.copy()
        
#         for key, value in override.items():
#             if key in result and isinstance(result[key], dict) and isinstance(value, dict):
#                 # Nested dict는 재귀 병합
#                 result[key] = self._merge_policies(result[key], value)
#             else:
#                 # 단순 값은 override
#                 result[key] = value
        
#         return result
    
#     def _apply_keypath_overrides(
#         self,
#         base: dict,
#         keypath_overrides: dict
#     ) -> dict:
#         """KeyPath 형식 Override 적용
        
#         KeyPath 형식: "crawl__timeout", "webdriver_manager__region"
        
#         Args:
#             base: 기본 정책 dict
#             keypath_overrides: KeyPath 형식 override dict
        
#         Returns:
#             Override 적용된 정책 dict
        
#         Example:
#             >>> base = {"crawl": {"timeout": 10}}
#             >>> overrides = {"crawl__timeout": 30}
#             >>> result = self._apply_keypath_overrides(base, overrides)
#             >>> print(result)
#             {"crawl": {"timeout": 30}}
#         """
#         result = base.copy()
        
#         for keypath, value in keypath_overrides.items():
#             keys = keypath.split("__")
#             current = result
            
#             # Nested dict 탐색
#             for key in keys[:-1]:
#                 if key not in current:
#                     current[key] = {}
#                 current = current[key]
            
#             # 마지막 키에 값 설정
#             current[keys[-1]] = value
        
#         return result
    
#     def analyze(self, url: str) -> Tuple[str, str, str]:
#         """URL 분석만 수행 (정책 로드 없음)
        
#         Args:
#             url: 크롤링할 URL
        
#         Returns:
#             (site, method, region)
        
#         Example:
#             >>> preprocessor = PreProcessor(base_policy)
#             >>> site, method, region = preprocessor.analyze(url)
#             >>> print(site, method, region)
#             ('aliexpress', 'detail', 'global')
#         """
#         return analyze_url(url)
    
#     def get_preset_policy(
#         self,
#         site: str,
#         method: str
#     ) -> Optional[dict]:
#         """Preset 정책 조회 (캐싱용)
        
#         Args:
#             site: Site identifier
#             method: Method identifier
        
#         Returns:
#             Preset 정책 dict or None
#         """
#         return get_preset(site, method)


# __all__ = ["PreProcessor"]
