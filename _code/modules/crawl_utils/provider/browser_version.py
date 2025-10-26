# -*- coding: utf-8 -*-
# crawl_utils/provider/browser_version.py
"""
브라우저 버전 감지 및 User-Agent 생성

Firefox, Chrome, Edge의 설치된 버전을 확인하고
UA 문자열을 생성합니다.

Usage:
    from crawl_utils.provider.browser_version import get_firefox_version, build_user_agent
    
    version = get_firefox_version()
    ua = build_user_agent("firefox", version)
"""

import re
import subprocess
from pathlib import Path
from typing import Literal, Optional

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
# CLI & Testing
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("Browser Version Manager")
    print("=" * 80)
    
    # 브라우저 버전 확인
    print("\nChecking installed browsers:")
    for browser in ["firefox", "chrome", "edge"]:
        version = get_browser_version(browser)  # type: ignore
        if version:
            ua = build_user_agent(browser, version)  # type: ignore
            print(f"\n  {browser.capitalize()}:")
            print(f"    Version: {version}")
            print(f"    UA: {ua[:70]}...")
        else:
            print(f"\n  {browser.capitalize()}: Not installed")
    
    print("\n" + "=" * 80)
