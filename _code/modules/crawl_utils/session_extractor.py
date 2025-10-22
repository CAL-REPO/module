# -*- coding: utf-8 -*-
# crawl_utils/session_extractor.py
"""
WebDriver 세션 정보 추출 및 복원

설정 파일(YAML/JSON)이 아닌, 실제 WebDriver가 사용하는 값을 직접 추출합니다.

Usage:
    # 크롤링 후
    from crawl_utils.session_extractor import extract_session_info, save_session
    
    session_info = extract_session_info(driver, site="taobao", region="china")
    save_session(session_info, "taobao_session.json")
    
    # 다운로드 시
    from crawl_utils.session_extractor import load_session, create_driver_from_session
    
    session_info = load_session("taobao_session.json")
    driver = create_driver_from_session(session_info)
"""

import json
from pathlib import Path
from typing import Optional, Any
from datetime import datetime


def extract_session_info(
    driver,
    site: str,
    region: str,
    additional_data: Optional[dict] = None
) -> dict:
    """WebDriver에서 실제 사용 중인 세션 정보 추출
    
    ⚠️  쿠키는 저장하지 않음! (Profile이 자동 관리)
    
    Args:
        driver: WebDriver 인스턴스
        site: 사이트 이름 (예: "taobao")
        region: 지역 이름 (예: "china")
        additional_data: 추가 메타 정보 (선택)
    
    Returns:
        세션 메타 정보 딕셔너리 (쿠키 제외!)
        {
            "user_agent": "실제 사용된 UA",
            "accept_languages": "실제 사용된 AL",
            "profile_path": "실제 사용된 프로필 경로",  // ← 쿠키는 여기에!
            "site": "taobao",
            "region": "china",
            "timestamp": "2025-10-21T12:00:00",
            "browser": "firefox"
        }
    
    Example:
        >>> session_info = extract_session_info(driver, "taobao", "china")
        >>> print(session_info["profile_path"])
        'M:/Firefox_Profile/CRAWL_CHINA'
    """
    # 기본 정보 추출
    session_info = {
        # WebDriver에서 직접 추출 (설정값 아님!)
        "user_agent": driver.execute_script("return navigator.userAgent;"),
        "accept_languages": driver.execute_script("return navigator.languages ? navigator.languages.join(',') : '';"),
        
        # ❌ 쿠키는 저장 안 함! (Profile이 관리)
        # "cookies": driver.get_cookies(),  # 보안 위험!
        
        # 메타 정보
        "site": site,
        "region": region,
        "timestamp": datetime.now().isoformat(),
        "browser": "firefox",  # TODO: capabilities에서 추출
    }
    
    # Firefox 특정 정보
    try:
        if hasattr(driver, "capabilities"):
            caps = driver.capabilities
            session_info["profile_path"] = caps.get("moz:profile", "")
            session_info["browser_version"] = caps.get("browserVersion", "")
            session_info["platform"] = caps.get("platformName", "")
    except Exception as e:
        print(f"⚠️  Failed to extract capabilities: {e}")
    
    # ❌ localStorage도 저장 안 함! (Profile이 관리)
    # try:
    #     session_info["local_storage"] = driver.execute_script(
    #         "return Object.assign({}, localStorage);"
    #     )
    # except Exception as e:
    #     session_info["local_storage"] = {}
    
    # 추가 데이터 병합
    if additional_data:
        session_info.update(additional_data)
    
    return session_info


def save_session(
    session_info: dict,
    file_path: str | Path,
    pretty: bool = True
) -> None:
    """세션 정보를 JSON 파일로 저장
    
    Args:
        session_info: extract_session_info()로 추출한 정보
        file_path: 저장할 파일 경로
        pretty: 들여쓰기 포맷 (기본값: True)
    
    Example:
        >>> save_session(session_info, "data/sessions/taobao_session.json")
        ✅ Session saved: taobao_session.json
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(session_info, f, indent=2, ensure_ascii=False)
        else:
            json.dump(session_info, f, ensure_ascii=False)
    
    print(f"✅ Session saved: {file_path.name}")


def load_session(file_path: str | Path) -> dict:
    """세션 정보를 JSON 파일에서 로드
    
    Args:
        file_path: 세션 파일 경로
    
    Returns:
        세션 정보 딕셔너리
    
    Example:
        >>> session_info = load_session("data/sessions/taobao_session.json")
        ✅ Session loaded: taobao_session.json
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Session file not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        session_info = json.load(f)
    
    print(f"✅ Session loaded: {file_path.name}")
    return session_info


def create_driver_from_session(session_info: dict):
    """세션 정보로 WebDriver 재생성 (실제 사용했던 값으로)
    
    ⚠️  쿠키는 Profile에서 자동 로드됨!
    
    Args:
        session_info: extract_session_info()로 저장한 정보
    
    Returns:
        WebDriver 인스턴스 (쿠키 자동 복원!)
    
    Example:
        >>> session_info = load_session("taobao_session.json")
        >>> driver = create_driver_from_session(session_info)
        ✅ WebDriver created from session: taobao (china)
        ✅ Cookies auto-loaded from profile!
    """
    from cfg_utils import ConfigLoader
    from crawl_utils.site_region_mapping import get_config_path_for_region
    from crawl_utils.providers import FirefoxProvider
    
    # 1. 지역 정보로 YAML 로드 (기본 설정)
    region = session_info["region"]
    config_path = get_config_path_for_region(region)
    config = ConfigLoader(config_path)
    webdriver_config = config.to_dict(section="webdriver")
    
    # 2. 세션 정보로 덮어쓰기 (실제 사용했던 값!)
    webdriver_config["user_agent"] = session_info["user_agent"]
    webdriver_config["accept_languages"] = session_info.get("accept_languages", "")
    
    # 3. 프로필 경로 (세션에서 사용했던 경로 = 쿠키 저장 위치!)
    if "profile_path" in session_info and session_info["profile_path"]:
        webdriver_config["firefox"]["profile_path"] = session_info["profile_path"]
    
    # 4. WebDriver 생성
    provider = FirefoxProvider(webdriver_config)
    driver = provider.create_driver()
    
    print(f"✅ WebDriver created from session: {session_info['site']} ({session_info['region']})")
    print(f"✅ Cookies auto-loaded from profile: {session_info.get('profile_path', 'N/A')}")
    
    # ✅ 쿠키는 Profile에서 자동 로드됨!
    # restore_cookies() 호출 불필요!
    
    return driver


def restore_cookies(driver, session_info: dict, url: Optional[str] = None) -> None:
    """쿠키 복원 (Deprecated - Profile이 자동 관리)
    
    ⚠️  이 함수는 더 이상 필요하지 않습니다!
    ⚠️  Firefox Profile이 쿠키를 자동으로 로드합니다!
    
    Args:
        driver: WebDriver 인스턴스
        session_info: 세션 정보
        url: 쿠키 설정을 위한 초기 URL
    
    Note:
        이 함수는 하위 호환성을 위해 남겨둠
        실제로는 Profile이 쿠키를 자동 관리함
    """
    print("⚠️  restore_cookies() is deprecated!")
    print("⚠️  Firefox Profile automatically manages cookies!")
    print(f"✅ Cookies are already loaded from: {session_info.get('profile_path', 'N/A')}")
    
    # Profile이 이미 쿠키를 로드했으므로 아무것도 안 함
    return


# =============================================================================
# CLI & Testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("Session Extractor")
    print("=" * 80)
    
    print("""
✅ Usage Pattern:

# 1. 크롤링 후 세션 저장 (메타 정보만!)
from crawl_utils.session_extractor import extract_session_info, save_session

driver = create_driver(...)
# ... 크롤링 ...

# ✅ UA, AL, profile_path만 저장 (쿠키 제외!)
session_info = extract_session_info(driver, site="taobao", region="china")
save_session(session_info, "data/sessions/taobao_session.json")
driver.quit()  # ← Profile에 쿠키 자동 저장!

# 2. 다운로드 시 세션 복원
from crawl_utils.session_extractor import load_session, create_driver_from_session

session_info = load_session("data/sessions/taobao_session.json")
driver = create_driver_from_session(session_info)
# ✅ Profile에서 쿠키 자동 로드!

# ... 다운로드 ...
driver.quit()
""")
    
    print("=" * 80)
    print("Key Features:")
    print("""
✅ WebDriver에서 직접 추출
   - 실제 사용된 UA/AL (설정값 아님!)
   - 실제 사용된 프로필 경로

✅ 쿠키는 Profile이 관리
   - session.json에 쿠키 저장 안 함! (보안!)
   - Profile이 자동으로 저장/로드

✅ 완벽한 세션 복원
   - 크롤링 시 사용했던 Profile 재사용
   - 쿠키 자동 복원 (Profile 덕분!)

✅ 보안
   - 평문 쿠키 저장 안 함
   - Firefox가 암호화 관리
""")
    print("=" * 80)
