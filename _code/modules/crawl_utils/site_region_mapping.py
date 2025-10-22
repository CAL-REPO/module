# -*- coding: utf-8 -*-
# crawl_utils/site_region_mapping.py
"""
사이트별 지역 매핑 및 브라우저 설정 관리

크롤링 스크립트에서 사이트 이름을 기반으로
적절한 WebDriver 지역 설정을 자동 선택합니다.

**UA/AL 중앙 관리:**
- BROWSER_VERSIONS: 브라우저별 최신 버전 (수동 업데이트)
- REGION_ACCEPT_LANGUAGES: 지역별 Accept-Language
- YAML 파일은 정책만 정의, 실제 값은 여기서 관리

Usage:
    from crawl_utils.site_region_mapping import (
        get_config_path_for_site,
        get_user_agent,
        get_accept_languages
    )
    
    site = "taobao"
    region = get_region_for_site(site)
    ua = get_user_agent("firefox", region)
    al = get_accept_languages(region)
"""

import re
import json
from pathlib import Path
from typing import Literal, Optional

RegionType = Literal["china", "global", "us", "eu"]
BrowserType = Literal["firefox", "chrome", "edge"]

# =============================================================================
# 브라우저 버전 관리 (JSON 파일에서 로드)
# =============================================================================

def _load_browser_versions() -> dict[str, str]:
    """browser_versions.json에서 브라우저 버전 로드
    
    Returns:
        브라우저 버전 딕셔너리
    """
    json_path = Path(__file__).parent / "configs" / "browser_versions.json"
    
    if not json_path.exists():
        # 기본값
        return {
            "firefox": "144.0",
            "chrome": "130.0.0.0",
            "edge": "131.0.0.0"
        }
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("versions", {})
    except Exception as e:
        print(f"⚠️  Failed to load browser versions: {e}")
        return {
            "firefox": "144.0",
            "chrome": "130.0.0.0",
            "edge": "131.0.0.0"
        }


# 브라우저 버전 (JSON 파일에서 로드)
BROWSER_VERSIONS = _load_browser_versions()

# =============================================================================
# 지역별 Accept-Language (참고용 - YAML 파일에 있음)
# =============================================================================

# Note: Accept-Language는 지역별 고정값이므로 YAML 파일에서 관리됨
# 이 딕셔너리는 참고용 또는 YAML 없이 사용 시 기본값
REGION_ACCEPT_LANGUAGES = {
    "china": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "global": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "us": "en-US,en;q=0.9",
    "eu": "en-GB,en;q=0.9,fr;q=0.8,de;q=0.7"
}

# =============================================================================
# 사이트 → 지역 매핑
# =============================================================================

SITE_TO_REGION: dict[str, RegionType] = {
    # 중국 내수 사이트
    "taobao": "china",
    "tmall": "china",
    "1688": "china",
    "jd": "china",
    "jingdong": "china",
    "vvic": "china",
    
    # 글로벌 사이트
    "aliexpress": "global",
    "alibaba": "global",
    
    # 미국 사이트 (향후)
    "amazon_us": "us",
    "amazon.com": "us",
    "ebay_us": "us",
    "walmart": "us",
    
    # 유럽 사이트 (향후)
    "amazon_uk": "eu",
    "amazon.co.uk": "eu",
    "amazon_de": "eu",
    "amazon.de": "eu",
}

# =============================================================================
# 지역별 메타 정보 (ConfigLoader 사용 전 참고용)
# =============================================================================

REGION_INFO = {
    "china": {
        "name": "China",
        "description": "Chinese domestic e-commerce sites",
        "sites": ["taobao", "tmall", "1688", "jd", "vvic"],
    },
    "global": {
        "name": "Global",
        "description": "International e-commerce platforms",
        "sites": ["aliexpress", "alibaba"],
    },
    "us": {
        "name": "United States",
        "description": "US-based e-commerce sites",
        "sites": ["amazon_us", "ebay_us", "walmart"],
    },
    "eu": {
        "name": "Europe",
        "description": "European e-commerce sites",
        "sites": ["amazon_uk", "amazon_de"],
    }
}

# =============================================================================
# Helper Functions
# =============================================================================

def get_region_for_site(site: str) -> RegionType:
    """사이트 이름으로 지역 반환
    
    Args:
        site: 사이트 이름 (예: "taobao", "aliexpress")
    
    Returns:
        지역 이름 ("china", "global", "us", "eu")
    
    Raises:
        ValueError: 알 수 없는 사이트
    
    Example:
        >>> get_region_for_site("taobao")
        'china'
        >>> get_region_for_site("aliexpress")
        'global'
    """
    region = SITE_TO_REGION.get(site.lower())
    if not region:
        available = ", ".join(list(SITE_TO_REGION.keys())[:10])
        raise ValueError(
            f"Unknown site: '{site}'. "
            f"Available sites: {available}..."
        )
    return region


def get_config_path_for_region(region: RegionType, base_dir: str = "modules/crawl_utils/configs") -> str:
    """지역 이름으로 Config 경로 반환
    
    Args:
        region: 지역 이름 ("china", "global", "us", "eu")
        base_dir: Config 디렉토리 경로 (기본값: "modules/crawl_utils/configs")
    
    Returns:
        Config 파일 경로
    
    Example:
        >>> get_config_path_for_region("china")
        'modules/crawl_utils/configs/webdriver_china.yaml'
    """
    return f"{base_dir}/webdriver_{region}.yaml"


def get_config_path_for_site(site: str, base_dir: str = "modules/crawl_utils/configs") -> str:
    """사이트 이름으로 Config 경로 반환 (get_region_for_site + get_config_path_for_region)
    
    Args:
        site: 사이트 이름 (예: "taobao")
        base_dir: Config 디렉토리 경로
    
    Returns:
        Config 파일 경로
    
    Example:
        >>> get_config_path_for_site("taobao")
        'modules/crawl_utils/configs/webdriver_china.yaml'
    """
    region = get_region_for_site(site)
    return get_config_path_for_region(region, base_dir)


def get_region_info(region: RegionType) -> dict:
    """지역 메타 정보 반환 (이름, 설명, 사이트 목록만)
    
    Note:
        실제 설정값(profile_path, session_path 등)은 ConfigLoader 사용!
    
    Args:
        region: 지역 이름 ("china", "global", "us", "eu")
    
    Returns:
        지역 메타 정보 딕셔너리 (name, description, sites)
    
    Example:
        >>> info = get_region_info("china")
        >>> info["name"]
        'China'
        >>> info["sites"]
        ['taobao', 'tmall', '1688', 'jd', 'vvic']
    """
    return REGION_INFO.get(region, {})


def list_sites_by_region(region: RegionType) -> list[str]:
    """지역별 사이트 목록 반환
    
    Args:
        region: 지역 이름
    
    Returns:
        사이트 목록
    
    Example:
        >>> list_sites_by_region("china")
        ['taobao', 'tmall', '1688', 'jd', 'vvic']
    """
    return REGION_INFO.get(region, {}).get("sites", [])


def list_all_regions() -> list[RegionType]:
    """모든 지역 목록 반환
    
    Returns:
        지역 목록
    """
    return list(REGION_INFO.keys())  # type: ignore


def list_all_sites() -> list[str]:
    """모든 사이트 목록 반환
    
    Returns:
        사이트 목록
    """
    return list(SITE_TO_REGION.keys())


# =============================================================================
# User-Agent 생성
# =============================================================================

def build_user_agent(
    browser: BrowserType,
    version: Optional[str] = None,
    os_info: str = "Windows NT 10.0; Win64; x64"
) -> str:
    """브라우저 버전으로 User-Agent 생성
    
    Args:
        browser: "firefox", "chrome", "edge"
        version: 버전 문자열 (None이면 BROWSER_VERSIONS 사용)
        os_info: OS 정보 (기본값: Windows 10 64bit)
    
    Returns:
        User-Agent 문자열
    
    Example:
        >>> build_user_agent("firefox")
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0'
    """
    if version is None:
        version = BROWSER_VERSIONS.get(browser, "1.0")
    
    if browser == "firefox":
        return f"Mozilla/5.0 ({os_info}; rv:{version}) Gecko/20100101 Firefox/{version}"
    elif browser == "chrome":
        return f"Mozilla/5.0 ({os_info}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
    elif browser == "edge":
        return f"Mozilla/5.0 ({os_info}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36 Edg/{version}"
    else:
        raise ValueError(f"Unknown browser: {browser}")


def get_user_agent(browser: BrowserType, region: Optional[RegionType] = None) -> str:
    """브라우저별 User-Agent 반환 (BROWSER_VERSIONS 기준)
    
    Args:
        browser: "firefox", "chrome", "edge"
        region: 지역 (현재 미사용, 향후 지역별 UA 분기 시 사용)
    
    Returns:
        User-Agent 문자열
    
    Example:
        >>> get_user_agent("firefox", "china")
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0'
    """
    return build_user_agent(browser)


def get_accept_languages(region: RegionType) -> str:
    """지역별 Accept-Language 반환
    
    Args:
        region: 지역 이름 ("china", "global", "us", "eu")
    
    Returns:
        Accept-Language 문자열
    
    Example:
        >>> get_accept_languages("china")
        'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
    """
    return REGION_ACCEPT_LANGUAGES.get(region, "en-US,en;q=0.9")


def get_browser_version(browser: BrowserType) -> str:
    """브라우저 버전 반환
    
    Args:
        browser: "firefox", "chrome", "edge"
    
    Returns:
        버전 문자열
    
    Example:
        >>> get_browser_version("firefox")
        '144.0'
    """
    return BROWSER_VERSIONS.get(browser, "1.0")


def get_session_path(region: RegionType, base_dir: str = "data/sessions") -> str:
    """지역별 세션 파일 경로 반환
    
    Args:
        region: 지역 이름 ("china", "global", "us", "eu")
        base_dir: 세션 디렉토리 (기본값: "data/sessions")
    
    Returns:
        세션 파일 경로
    
    Example:
        >>> get_session_path("china")
        'data/sessions/webdriver_china.json'
    """
    return f"{base_dir}/webdriver_{region}.json"


def get_profile_path(region: RegionType, base_dir: str = "M:/Firefox_Profile") -> str:
    """지역별 프로필 경로 반환
    
    Args:
        region: 지역 이름 ("china", "global", "us", "eu")
        base_dir: 프로필 디렉토리 (기본값: "M:/Firefox_Profile")
    
    Returns:
        프로필 경로
    
    Example:
        >>> get_profile_path("china")
        'M:/Firefox_Profile/CRAWL_CHINA'
    """
    return f"{base_dir}/CRAWL_{region.upper()}"


def update_browser_version(browser: BrowserType, version: str, save: bool = True) -> None:
    """브라우저 버전 업데이트 (JSON 파일에 저장)
    
    Args:
        browser: "firefox", "chrome", "edge"
        version: 새 버전 문자열
        save: JSON 파일에 저장할지 여부 (기본값: True)
    
    Example:
        >>> update_browser_version("firefox", "145.0")
        ✅ Updated firefox version: 145.0
        ✅ Saved to: browser_versions.json
    """
    from datetime import datetime
    
    # 메모리 업데이트
    BROWSER_VERSIONS[browser] = version
    print(f"✅ Updated {browser} version: {version}")
    
    # JSON 파일 저장
    if save:
        json_path = Path(__file__).parent / "configs" / "browser_versions.json"
        
        try:
            # 기존 데이터 로드 (주석 유지)
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {
                    "_comment": "Browser versions for User-Agent generation",
                    "_last_updated": "",
                    "versions": {}
                }
            
            # 버전 업데이트
            data["versions"][browser] = version
            data["_last_updated"] = datetime.now().strftime("%Y-%m-%d")
            
            # 저장
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved to: {json_path.name}")
        
        except Exception as e:
            print(f"❌ Failed to save: {e}")


# =============================================================================
# CLI & Testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("Site → Region Mapping & Browser Settings")
    print("=" * 80)
    
    # 1. 브라우저 버전 확인
    print("\n[1] Browser Versions (Managed in Code):")
    for browser in ["firefox", "chrome", "edge"]:
        version = get_browser_version(browser)  # type: ignore
        ua = get_user_agent(browser)  # type: ignore
        print(f"\n  {browser.capitalize()}:")
        print(f"    Version: {version}")
        print(f"    UA: {ua}")
    
    # 2. 지역별 Accept-Language
    print("\n" + "=" * 80)
    print("[2] Region Accept-Languages:")
    for region in list_all_regions():
        al = get_accept_languages(region)  # type: ignore
        print(f"  {region}: {al}")
    
    # 3. 사이트 매핑 테스트
    print("\n" + "=" * 80)
    print("[3] Site Mapping Test:")
    test_sites = ["taobao", "tmall", "aliexpress", "alibaba", "jd"]
    
    for site in test_sites:
        try:
            region = get_region_for_site(site)
            config_path = get_config_path_for_site(site)
            info = get_region_info(region)
            al = get_accept_languages(region)
            ua = get_user_agent("firefox", region)
            session_path = get_session_path(region)
            profile_path = get_profile_path(region)
            
            print(f"\nSite: {site}")
            print(f"  Region: {region} ({info.get('name', 'Unknown')})")
            print(f"  Config: {config_path}")
            print(f"  Profile: {profile_path}")
            print(f"  Session: {session_path}")
            print(f"  Accept-Language: {al}")
            print(f"  User-Agent: {ua[:60]}...")
        except ValueError as e:
            print(f"\n❌ Error: {e}")
    
    # 4. 사용 예제
    print("\n" + "=" * 80)
    print("[4] Usage Example:")
    print("""
from cfg_utils import ConfigLoader
from crawl_utils.site_region_mapping import (
    get_config_path_for_site,
    get_region_for_site,
    get_user_agent,
    get_accept_languages,
    get_session_path,
    get_profile_path
)

# 1. 사이트 → 지역 → Config 경로
site = "taobao"
region = get_region_for_site(site)
config_path = get_config_path_for_site(site)

# 2. ConfigLoader로 YAML 로드 (정책만)
config = ConfigLoader(config_path)
webdriver_config = config.to_dict(section="webdriver")

# 3. 런타임 값 주입 (site_region_mapping에서)
webdriver_config["user_agent"] = get_user_agent("firefox", region)
webdriver_config["accept_languages"] = get_accept_languages(region)
webdriver_config["session_path"] = get_session_path(region)
webdriver_config["firefox"]["profile_path"] = get_profile_path(region)

# 4. Provider에 전달
provider = FirefoxProvider(webdriver_config)
driver = provider.create_driver()
""")
    print("=" * 80)
    
    # 5. 버전 업데이트 안내
    print("\n" + "=" * 80)
    print("[5] How to Update Browser Version:")
    print("""
방법 1: Python 코드에서 (자동 저장)
    from crawl_utils.site_region_mapping import update_browser_version
    
    update_browser_version("firefox", "145.0")
    # ✅ Updated firefox version: 145.0
    # ✅ Saved to: browser_versions.json

방법 2: JSON 파일 직접 수정
    # configs/browser_versions.json
    {
      "versions": {
        "firefox": "145.0",  # ← 여기만 변경
        "chrome": "130.0.0.0",
        "edge": "131.0.0.0"
      }
    }

방법 3: browser_version_manager.py 사용 (자동 감지)
    from crawl_utils.browser_version_manager import auto_update_firefox
    
    auto_update_firefox()  # 설치된 Firefox 버전 자동 감지 및 저장
""")
    print("=" * 80)
