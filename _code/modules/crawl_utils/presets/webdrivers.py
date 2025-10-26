# -*- coding: utf-8 -*-
"""crawl_utils.presets.webdrivers
==================================

Region별 WebDriver Override 설정

ConfigLoader의 webdriver_manager section 기본값 위에 region별로 override할 값만 정의합니다.

Override 대상:
- Firefox: profile_path, accept_languages
- Chrome: user_data_dir, accept_languages

사용 예시:
    >>> from crawl_utils.presets import WEBDRIVER_OVERRIDES
    >>> from cfg_utils.services.section_extractor import SectionExtractor
    >>> from crawl_utils.provider.policy import WebDriverManagerPolicy
    >>> 
    >>> # ConfigLoader로 webdriver_manager section 로드 (SectionExtractor 사용)
    >>> section_name = SectionExtractor.get_policy_name(WebDriverManagerPolicy)
    >>> webdriver_config = config.to_dict(section=section_name)
    >>> 
    >>> # region/provider별 override 적용
    >>> region = "china"
    >>> provider = "firefox"
    >>> override = WEBDRIVER_OVERRIDES.get(region, {}).get(provider, {})
    >>> 
    >>> # keypath 기반 override
    >>> from keypath_utils import set_keypath
    >>> for key, value in override.items():
    ...     set_keypath(webdriver_config, f"{provider}.{key}", value)
"""

# =============================================================================
# Region별 WebDriver Override
# =============================================================================

WEBDRIVER_OVERRIDES = {
    # 중국 지역
    "china": {
        "firefox": {
            "profile_path": "M:/WEB_PROFILE/CRAWL_CHINA",
            "accept_languages": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        },
        "chrome": {
            "user_data_dir": "M:/WEB_PROFILE/CRAWL_CHINA",
            "accept_languages": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }
    },
    
    # 글로벌 지역
    "global": {
        "firefox": {
            "profile_path": "M:/WEB_PROFILE/CRAWL_GLOBAL",
            "accept_languages": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        },
        "chrome": {
            "user_data_dir": "M:/WEB_PROFILE/CRAWL_GLOBAL",
            "accept_languages": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        },
    },
}

# =============================================================================
# Provider별 전용 필드 정의
# =============================================================================
# webdriver_manager YAML 구조:
#   webdriver_manager:
#     accept_languages: ""          # ← 공통 필드 (모든 provider)
#     firefox:
#       profile_path: ""            # ← Firefox 전용
#       driver_path: ""
#       binary_path: ""
#     chrome:
#       user_data_dir: ""           # ← Chrome 전용
#       driver_path: ""
#       binary_path: ""
#
# Override 시:
# - 전용 필드: {provider}__{field} 형식으로 전달 (예: firefox__profile_path)
# - 공통 필드: prefix 없이 전달 (예: accept_languages)

PROVIDER_SPECIFIC_FIELDS = {
    "firefox": ["profile_path", "driver_path", "binary_path"],
    "chrome": ["user_data_dir", "driver_path", "binary_path"],
}


__all__ = [
    "WEBDRIVER_OVERRIDES",
    "PROVIDER_SPECIFIC_FIELDS",
]
