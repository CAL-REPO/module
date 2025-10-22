# -*- coding: utf-8 -*-
# crawl_utils/browser_version_manager.py
"""
브라우저 버전 관리 및 User-Agent 자동 업데이트

Firefox, Chrome, Edge의 최신 버전을 확인하고
WebDriver YAML 파일의 User-Agent를 자동 업데이트합니다.

Usage:
    from crawl_utils.browser_version_manager import update_all_configs
    
    # 모든 지역별 Config의 UA 업데이트
    update_all_configs()
"""

import re
import subprocess
from pathlib import Path
from typing import Literal, Optional

import yaml

BrowserType = Literal["firefox", "chrome", "edge"]

# =============================================================================
# 브라우저 버전 확인
# =============================================================================

def get_firefox_version() -> Optional[str]:
    """현재 설치된 Firefox 버전 확인 (Windows)
    
    Returns:
        버전 문자열 (예: "144.0") 또는 None
    
    Example:
        >>> get_firefox_version()
        '144.0'
    """
    try:
        # Windows Firefox 기본 경로
        firefox_path = r"C:\Program Files\Mozilla Firefox\firefox.exe"
        if not Path(firefox_path).exists():
            firefox_path = r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
        
        if not Path(firefox_path).exists():
            return None
        
        # PowerShell로 버전 확인
        cmd = f'(Get-Item "{firefox_path}").VersionInfo.ProductVersion'
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            version = result.stdout.strip()
            # "144.0.1.8652" → "144.0"
            match = re.match(r"(\d+\.\d+)", version)
            return match.group(1) if match else None
        
        return None
    
    except Exception as e:
        print(f"⚠️ Failed to get Firefox version: {e}")
        return None


def get_chrome_version() -> Optional[str]:
    """현재 설치된 Chrome 버전 확인 (Windows)
    
    Returns:
        버전 문자열 (예: "130.0.0.0") 또는 None
    """
    try:
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if not Path(chrome_path).exists():
            chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        
        if not Path(chrome_path).exists():
            return None
        
        cmd = f'(Get-Item "{chrome_path}").VersionInfo.ProductVersion'
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            version = result.stdout.strip()
            # "130.0.6723.92" → "130.0.0.0"
            match = re.match(r"(\d+\.\d+)", version)
            if match:
                major_minor = match.group(1)
                return f"{major_minor}.0.0"
            return None
        
        return None
    
    except Exception as e:
        print(f"⚠️ Failed to get Chrome version: {e}")
        return None


def get_edge_version() -> Optional[str]:
    """현재 설치된 Edge 버전 확인 (Windows)
    
    Returns:
        버전 문자열 (예: "131.0.0.0") 또는 None
    """
    try:
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        if not Path(edge_path).exists():
            edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        
        if not Path(edge_path).exists():
            return None
        
        cmd = f'(Get-Item "{edge_path}").VersionInfo.ProductVersion'
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            version = result.stdout.strip()
            match = re.match(r"(\d+\.\d+)", version)
            if match:
                major_minor = match.group(1)
                return f"{major_minor}.0.0"
            return None
        
        return None
    
    except Exception as e:
        print(f"⚠️ Failed to get Edge version: {e}")
        return None


def get_browser_version(browser: BrowserType) -> Optional[str]:
    """브라우저별 버전 확인 통합 함수
    
    Args:
        browser: "firefox", "chrome", "edge"
    
    Returns:
        버전 문자열 또는 None
    """
    if browser == "firefox":
        return get_firefox_version()
    elif browser == "chrome":
        return get_chrome_version()
    elif browser == "edge":
        return get_edge_version()
    else:
        raise ValueError(f"Unknown browser: {browser}")


# =============================================================================
# User-Agent 생성
# =============================================================================

def build_user_agent(browser: BrowserType, version: str, os_info: str = "Windows NT 10.0; Win64; x64") -> str:
    """브라우저 버전으로 User-Agent 생성
    
    Args:
        browser: "firefox", "chrome", "edge"
        version: 버전 문자열 (예: "144.0")
        os_info: OS 정보 (기본값: Windows 10 64bit)
    
    Returns:
        User-Agent 문자열
    
    Example:
        >>> build_user_agent("firefox", "144.0")
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0'
    """
    if browser == "firefox":
        # Firefox UA 형식
        return f"Mozilla/5.0 ({os_info}; rv:{version}) Gecko/20100101 Firefox/{version}"
    
    elif browser == "chrome":
        # Chrome UA 형식
        return f"Mozilla/5.0 ({os_info}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
    
    elif browser == "edge":
        # Edge UA 형식
        chrome_version = version  # Edge는 Chromium 기반
        return f"Mozilla/5.0 ({os_info}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36 Edg/{version}"
    
    else:
        raise ValueError(f"Unknown browser: {browser}")


# =============================================================================
# 자동 업데이트 (site_region_mapping 연동)
# =============================================================================

def auto_update_firefox() -> bool:
    """설치된 Firefox 버전 자동 감지 및 저장
    
    Returns:
        업데이트 성공 여부
    
    Example:
        >>> auto_update_firefox()
        🔍 Detected Firefox version: 145.0
        ✅ Updated firefox version: 145.0
        ✅ Saved to: browser_versions.json
        True
    """
    from crawl_utils.site_region_mapping import update_browser_version
    
    version = get_firefox_version()
    if not version:
        print("❌ Firefox not found")
        return False
    
    print(f"🔍 Detected Firefox version: {version}")
    update_browser_version("firefox", version, save=True)
    return True


def auto_update_chrome() -> bool:
    """설치된 Chrome 버전 자동 감지 및 저장
    
    Returns:
        업데이트 성공 여부
    """
    from crawl_utils.site_region_mapping import update_browser_version
    
    version = get_chrome_version()
    if not version:
        print("❌ Chrome not found")
        return False
    
    print(f"🔍 Detected Chrome version: {version}")
    update_browser_version("chrome", version, save=True)
    return True


def auto_update_edge() -> bool:
    """설치된 Edge 버전 자동 감지 및 저장
    
    Returns:
        업데이트 성공 여부
    """
    from crawl_utils.site_region_mapping import update_browser_version
    
    version = get_edge_version()
    if not version:
        print("❌ Edge not found")
        return False
    
    print(f"🔍 Detected Edge version: {version}")
    update_browser_version("edge", version, save=True)
    return True


def auto_update_all() -> dict[str, bool]:
    """모든 브라우저 버전 자동 감지 및 저장
    
    Returns:
        {브라우저: 성공여부} 딕셔너리
    """
    print("=" * 80)
    print("Auto-detecting browser versions...")
    print("=" * 80)
    
    results = {
        "firefox": auto_update_firefox(),
        "chrome": auto_update_chrome(),
        "edge": auto_update_edge()
    }
    
    print("\n" + "=" * 80)
    success_count = sum(results.values())
    print(f"Summary: {success_count}/3 browsers updated")
    print("=" * 80)
    
    return results


# =============================================================================
# YAML 파일 업데이트 (Deprecated - JSON 사용)
# =============================================================================

def update_yaml_user_agent(
    yaml_path: Path,
    browser: BrowserType,
    new_version: Optional[str] = None,
    dry_run: bool = False
) -> bool:
    """YAML 파일의 User-Agent 업데이트
    
    Args:
        yaml_path: YAML 파일 경로
        browser: "firefox", "chrome", "edge"
        new_version: 새 버전 (None이면 자동 감지)
        dry_run: True면 실제 저장 안 함
    
    Returns:
        업데이트 성공 여부
    
    Example:
        >>> path = Path("configs/webdriver_china.yaml")
        >>> update_yaml_user_agent(path, "firefox", "144.0")
        ✅ Updated: webdriver_china.yaml → Firefox/144.0
        True
    """
    try:
        # 버전 확인
        if new_version is None:
            new_version = get_browser_version(browser)
            if new_version is None:
                print(f"⚠️ Could not detect {browser} version")
                return False
        
        # YAML 읽기
        if not yaml_path.exists():
            print(f"❌ File not found: {yaml_path}")
            return False
        
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        # webdriver 섹션 확인
        if "webdriver" not in data:
            print(f"⚠️ No 'webdriver' section in {yaml_path.name}")
            return False
        
        webdriver_section = data["webdriver"]
        
        # provider 확인
        current_provider = webdriver_section.get("provider", "firefox")
        if current_provider != browser:
            print(f"⚠️ Provider mismatch: {current_provider} != {browser}")
            return False
        
        # User-Agent 업데이트
        new_ua = build_user_agent(browser, new_version)
        old_ua = webdriver_section.get("user_agent", "")
        
        if old_ua == new_ua:
            print(f"✓ Already up-to-date: {yaml_path.name} ({browser}/{new_version})")
            return True
        
        # 변경 사항 출력
        print(f"\n📝 {yaml_path.name}:")
        print(f"  Old: {old_ua}")
        print(f"  New: {new_ua}")
        
        if dry_run:
            print(f"  [DRY RUN] Would update {yaml_path.name}")
            return True
        
        # 실제 업데이트
        webdriver_section["user_agent"] = new_ua
        
        # YAML 저장 (주석 보존)
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        
        print(f"✅ Updated: {yaml_path.name} → {browser}/{new_version}")
        return True
    
    except Exception as e:
        print(f"❌ Failed to update {yaml_path.name}: {e}")
        return False


def update_all_configs(
    config_dir: Optional[Path] = None,
    browser: BrowserType = "firefox",
    dry_run: bool = False
) -> dict[str, bool]:
    """모든 지역별 Config의 User-Agent 업데이트
    
    Args:
        config_dir: Config 디렉토리 (None이면 자동 탐지)
        browser: "firefox", "chrome", "edge"
        dry_run: True면 실제 저장 안 함
    
    Returns:
        {파일명: 성공여부} 딕셔너리
    
    Example:
        >>> results = update_all_configs(browser="firefox")
        >>> results
        {'webdriver_china.yaml': True, 'webdriver_global.yaml': True, ...}
    """
    # Config 디렉토리 자동 탐지
    if config_dir is None:
        # crawl_utils/configs/ 찾기
        current_file = Path(__file__).resolve()
        config_dir = current_file.parent / "configs"
    
    if not config_dir.exists():
        print(f"❌ Config directory not found: {config_dir}")
        return {}
    
    # webdriver_*.yaml 파일 찾기
    yaml_files = list(config_dir.glob("webdriver_*.yaml"))
    
    if not yaml_files:
        print(f"⚠️ No webdriver_*.yaml files found in {config_dir}")
        return {}
    
    print(f"\n{'=' * 80}")
    print(f"Updating User-Agent ({browser})")
    print(f"Config Dir: {config_dir}")
    print(f"Files: {len(yaml_files)}")
    print(f"{'=' * 80}")
    
    # 각 파일 업데이트
    results = {}
    for yaml_file in yaml_files:
        success = update_yaml_user_agent(yaml_file, browser, dry_run=dry_run)
        results[yaml_file.name] = success
    
    # 요약
    print(f"\n{'=' * 80}")
    success_count = sum(results.values())
    total_count = len(results)
    print(f"Summary: {success_count}/{total_count} files updated")
    print(f"{'=' * 80}\n")
    
    return results


# =============================================================================
# CLI & Testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("Browser Version Manager")
    print("=" * 80)
    
    # 1. 브라우저 버전 확인
    print("\n[1] Checking installed browsers:")
    for browser in ["firefox", "chrome", "edge"]:
        version = get_browser_version(browser)  # type: ignore
        if version:
            ua = build_user_agent(browser, version)  # type: ignore
            print(f"\n  {browser.capitalize()}:")
            print(f"    Version: {version}")
            print(f"    UA: {ua}")
        else:
            print(f"\n  {browser.capitalize()}: Not installed")
    
    # 2. 자동 업데이트 테스트 (Dry Run)
    print("\n" + "=" * 80)
    print("[2] Auto-update test:")
    print("=" * 80)
    
    # Firefox 자동 업데이트
    print("\nℹ️  To update browser versions:")
    print("  from crawl_utils.browser_version_manager import auto_update_all")
    print("  auto_update_all()")
    print("\nOr update individually:")
    print("  auto_update_firefox()")
    print("  auto_update_chrome()")
    print("  auto_update_edge()")
    
    print("\n" + "=" * 80)
