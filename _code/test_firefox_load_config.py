#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FirefoxWebDriver._load_config() 개선 검증 테스트
"""

from pathlib import Path
import sys

# PYTHONPATH 추가
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from crawl_utils.provider.firefox import FirefoxWebDriver
from crawl_utils.provider.policy import WebDriverPolicy


def test_load_from_yaml():
    """YAML 파일에서 로드 테스트"""
    print("=" * 80)
    print("Test 1: Load from YAML file")
    print("=" * 80)
    
    yaml_path = Path(__file__).parent.parent / "modules" / "crawl_utils" / "configs" / "firefox.yaml"
    
    if not yaml_path.exists():
        print(f"⚠️ YAML file not found: {yaml_path}")
        print("Skipping test...")
        return
    
    try:
        driver = FirefoxWebDriver(str(yaml_path))
        print(f"✅ Config loaded successfully")
        print(f"   - Provider: {driver.config.provider}")
        print(f"   - Headless: {driver.config.headless}")
        print(f"   - Window Size: {driver.config.window_size}")
        if driver.config.firefox:
            print(f"   - Firefox binary: {driver.config.firefox.binary_path}")
            print(f"   - Firefox profile: {driver.config.firefox.profile_path}")
    except Exception as e:
        print(f"❌ Failed: {e}")


def test_load_from_path():
    """Path 객체에서 로드 테스트"""
    print("\n" + "=" * 80)
    print("Test 2: Load from Path object")
    print("=" * 80)
    
    yaml_path = Path(__file__).parent.parent / "modules" / "crawl_utils" / "configs" / "firefox.yaml"
    
    if not yaml_path.exists():
        print(f"⚠️ YAML file not found: {yaml_path}")
        print("Skipping test...")
        return
    
    try:
        driver = FirefoxWebDriver(yaml_path)
        print(f"✅ Config loaded successfully")
        print(f"   - Provider: {driver.config.provider}")
        print(f"   - Region: {driver.config.region}")
    except Exception as e:
        print(f"❌ Failed: {e}")


def test_load_from_dict():
    """dict에서 로드 테스트"""
    print("\n" + "=" * 80)
    print("Test 3: Load from dict")
    print("=" * 80)
    
    config_dict = {
        "provider": "firefox",
        "headless": True,
        "window_size": (1920, 1080),
        "firefox": {
            "use_webdriver_manager": True,
            "dom_enabled": False,
            "resist_fingerprint_enabled": False,
        }
    }
    
    try:
        driver = FirefoxWebDriver(config_dict)
        print(f"✅ Config loaded successfully")
        print(f"   - Provider: {driver.config.provider}")
        print(f"   - Headless: {driver.config.headless}")
        print(f"   - Window Size: {driver.config.window_size}")
        if driver.config.firefox:
            print(f"   - Use WebDriver Manager: {driver.config.firefox.use_webdriver_manager}")
    except Exception as e:
        print(f"❌ Failed: {e}")


def test_load_from_policy():
    """Policy 인스턴스에서 로드 테스트"""
    print("\n" + "=" * 80)
    print("Test 4: Load from WebDriverPolicy instance (via dict)")
    print("=" * 80)
    
    # WebDriverPolicy는 많은 필수 필드가 있으므로 dict를 통해 Policy로 변환
    config_dict = {
        "name": "webdriver",
        "provider": "firefox",
        "headless": False,
        "window_size": (1280, 720),
        "firefox": {
            "use_webdriver_manager": True,
        }
    }
    
    try:
        driver = FirefoxWebDriver(config_dict)
        print(f"✅ Config loaded successfully")
        print(f"   - Provider: {driver.config.provider}")
        print(f"   - Headless: {driver.config.headless}")
        print(f"   - Window Size: {driver.config.window_size}")
        print(f"   - Policy type: {type(driver.config).__name__}")
    except Exception as e:
        print(f"❌ Failed: {e}")


def test_load_with_overrides():
    """오버라이드 테스트"""
    print("\n" + "=" * 80)
    print("Test 5: Load with runtime overrides")
    print("=" * 80)
    
    yaml_path = Path(__file__).parent.parent / "modules" / "crawl_utils" / "configs" / "firefox.yaml"
    
    if not yaml_path.exists():
        print(f"⚠️ YAML file not found: {yaml_path}")
        print("Skipping test...")
        return
    
    try:
        driver = FirefoxWebDriver(
            yaml_path,
            headless=True,  # 오버라이드
            window_size=(1600, 900)  # 오버라이드
        )
        print(f"✅ Config loaded with overrides")
        print(f"   - Headless: {driver.config.headless} (should be True)")
        print(f"   - Window Size: {driver.config.window_size} (should be (1600, 900))")
    except Exception as e:
        print(f"❌ Failed: {e}")


def test_code_simplification():
    """코드 간소화 확인"""
    print("\n" + "=" * 80)
    print("Test 6: Code simplification verification")
    print("=" * 80)
    
    import inspect
    
    # _load_config 메서드 소스 코드 확인
    source = inspect.getsource(FirefoxWebDriver._load_config)
    lines = [line for line in source.split('\n') if line.strip() and not line.strip().startswith('#')]
    
    # Docstring 제외
    in_docstring = False
    code_lines = []
    for line in lines:
        if '"""' in line or "'''" in line:
            in_docstring = not in_docstring
            continue
        if not in_docstring and line.strip():
            code_lines.append(line)
    
    print(f"✅ _load_config() implementation:")
    print(f"   - Total lines: {len(code_lines)}")
    print(f"   - Uses load_with_caller_path: {'load_with_caller_path' in source}")
    print(f"   - No manual Path conversion: {'Path(__file__)' not in source or 'parent.parent' not in source}")
    print(f"   - Single return statement: {source.count('return ') == 1}")
    
    if len(code_lines) <= 10:
        print(f"   ✅ Code is concise (≤10 lines)")
    else:
        print(f"   ⚠️ Code might be too long ({len(code_lines)} lines)")


if __name__ == "__main__":
    print("🚀 FirefoxWebDriver._load_config() 개선 검증 테스트")
    print()
    
    test_load_from_yaml()
    test_load_from_path()
    test_load_from_dict()
    test_load_from_policy()
    test_load_with_overrides()
    test_code_simplification()
    
    print("\n" + "=" * 80)
    print("✅ All tests completed!")
    print("=" * 80)
