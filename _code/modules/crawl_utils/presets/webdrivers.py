# -*- coding: utf-8 -*-
"""crawl_utils.presets.webdrivers
==================================

Region별 WebDriver Override 설정

ConfigLoader의 webdriver section 기본값 위에 region별로 override할 값만 정의합니다.

Override 대상:
- Firefox: profile_path, accept_languages
- Chrome: user_data_dir, accept_languages

사용 예시:
    >>> from crawl_utils.presets import WEBDRIVER_OVERRIDES
    >>> # ConfigLoader로 webdriver section 로드
    >>> webdriver_config = config.to_dict(section="webdriver")
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
            "profile_path": "M:/Firefox_Profile/CRAWL_CHINA",
            "accept_languages": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        },
        "chrome": {
            "user_data_dir": "M:/Chrome_Profile/CRAWL_CHINA",
            "accept_languages": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }
    },
    
    # 글로벌 지역
    "worldwide": {
        "firefox": {
            "profile_path": "M:/Firefox_Profile/CRAWL_GLOBAL",
            "accept_languages": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7"
        },
        "chrome": {
            "user_data_dir": "M:/Chrome_Profile/CRAWL_GLOBAL",
            "accept_languages": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7"
        }
    }
}


__all__ = [
    "WEBDRIVER_OVERRIDES",
]
