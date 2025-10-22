#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ConfigLoader를 사용한 WebDriver 3개 정책 테스트

3개의 YAML 정책 파일로 WebDriver 실행:
1. webdriver.yaml - 기본 글로벌 설정
2. webdriver_china.yaml - 중국 지역 설정
3. webdriver_global.yaml - 글로벌 지역 설정 (명시적)
"""

from pathlib import Path
import sys

# PYTHONPATH 추가
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from cfg_utils import ConfigLoader
from crawl_utils.adapter.firefox import FirefoxWebDriver


def test_webdriver_base():
    """Test 1: webdriver.yaml (기본 글로벌 설정)"""
    print("=" * 80)
    print("Test 1: webdriver.yaml (기본 글로벌 설정)")
    print("=" * 80)
    
    try:
        # ConfigLoader로 webdriver_config_loader.yaml 로드
        config_loader_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver_config_loader.yaml"
        
        if not config_loader_path.exists():
            print(f"❌ ConfigLoader YAML 파일을 찾을 수 없습니다: {config_loader_path}")
            return
        
        # ConfigLoader 생성
        config = ConfigLoader(config_loader_cfg_path=str(config_loader_path))
        
        # 'webdriver' 섹션 추출
        webdriver_config = config.to_dict(section="webdriver")
        
        print(f"✅ ConfigLoader로 설정 로드 성공")
        print(f"   - Provider: {webdriver_config.get('provider')}")
        print(f"   - Region: {webdriver_config.get('region')}")
        print(f"   - Headless: {webdriver_config.get('headless')}")
        print(f"   - Accept-Languages: {webdriver_config.get('accept_languages')}")
        
        # FirefoxWebDriver 생성
        # ConfigLoader에서 추출한 dict를 직접 사용하는 대신
        # YAML 파일 경로를 전달 (ConfigLikeLoader가 처리)
        print(f"\n📋 FirefoxWebDriver 설정 확인:")
        
        yaml_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver.yaml"
        driver = FirefoxWebDriver(str(yaml_path))
        
        print(f"   - Config Provider: {driver.config.provider}")
        print(f"   - Config Region: {driver.config.region}")
        print(f"   - Firefox Binary: {driver.config.firefox.binary_path if driver.config.firefox else 'N/A'}")
        print(f"   - Firefox Profile: {driver.config.firefox.profile_path if driver.config.firefox else 'N/A'}")
        
        # 실제 WebDriver 실행 (옵션)
        # print(f"\n🚀 WebDriver 실행 중...")
        # with driver:
        #     driver.driver.get("https://www.google.com")
        #     print(f"   - Title: {driver.driver.title}")
        
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()


def test_webdriver_china():
    """Test 2: webdriver_china.yaml (중국 지역 설정)"""
    print("\n" + "=" * 80)
    print("Test 2: webdriver_china.yaml (중국 지역 설정)")
    print("=" * 80)
    
    try:
        # ConfigLoader로 webdriver_config_loader.yaml 로드
        config_loader_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver_config_loader.yaml"
        
        if not config_loader_path.exists():
            print(f"❌ ConfigLoader YAML 파일을 찾을 수 없습니다: {config_loader_path}")
            return
        
        # ConfigLoader 생성
        config = ConfigLoader(config_loader_cfg_path=str(config_loader_path))
        
        # 'webdriver_china' 섹션 추출
        webdriver_china_config = config.to_dict(section="webdriver_china")
        
        print(f"✅ ConfigLoader로 설정 로드 성공")
        print(f"   - Provider: {webdriver_china_config.get('provider')}")
        print(f"   - Region: {webdriver_china_config.get('region')}")
        print(f"   - Headless: {webdriver_china_config.get('headless')}")
        print(f"   - Accept-Languages: {webdriver_china_config.get('accept_languages')}")
        
        # FirefoxWebDriver 생성
        print(f"\n📋 FirefoxWebDriver 설정 확인:")
        
        yaml_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver_china.yaml"
        driver = FirefoxWebDriver(str(yaml_path))
        
        print(f"   - Config Provider: {driver.config.provider}")
        print(f"   - Config Region: {driver.config.region}")
        print(f"   - Firefox Binary: {driver.config.firefox.binary_path if driver.config.firefox else 'N/A'}")
        print(f"   - Firefox Profile: {driver.config.firefox.profile_path if driver.config.firefox else 'N/A'}")
        
        # 실제 WebDriver 실행 (옵션)
        # print(f"\n🚀 WebDriver 실행 중...")
        # with driver:
        #     driver.driver.get("https://www.taobao.com")
        #     print(f"   - Title: {driver.driver.title}")
        
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()


def test_webdriver_global():
    """Test 3: webdriver_global.yaml (글로벌 지역 설정)"""
    print("\n" + "=" * 80)
    print("Test 3: webdriver_global.yaml (글로벌 지역 설정)")
    print("=" * 80)
    
    try:
        # ConfigLoader로 webdriver_config_loader.yaml 로드
        config_loader_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver_config_loader.yaml"
        
        if not config_loader_path.exists():
            print(f"❌ ConfigLoader YAML 파일을 찾을 수 없습니다: {config_loader_path}")
            return
        
        # ConfigLoader 생성
        config = ConfigLoader(config_loader_cfg_path=str(config_loader_path))
        
        # 'webdriver_global' 섹션 추출
        webdriver_global_config = config.to_dict(section="webdriver_global")
        
        print(f"✅ ConfigLoader로 설정 로드 성공")
        print(f"   - Provider: {webdriver_global_config.get('provider')}")
        print(f"   - Region: {webdriver_global_config.get('region')}")
        print(f"   - Headless: {webdriver_global_config.get('headless')}")
        print(f"   - Accept-Languages: {webdriver_global_config.get('accept_languages')}")
        
        # FirefoxWebDriver 생성
        print(f"\n📋 FirefoxWebDriver 설정 확인:")
        
        yaml_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver_global.yaml"
        driver = FirefoxWebDriver(str(yaml_path))
        
        print(f"   - Config Provider: {driver.config.provider}")
        print(f"   - Config Region: {driver.config.region}")
        print(f"   - Firefox Binary: {driver.config.firefox.binary_path if driver.config.firefox else 'N/A'}")
        print(f"   - Firefox Profile: {driver.config.firefox.profile_path if driver.config.firefox else 'N/A'}")
        
        # 실제 WebDriver 실행 (옵션)
        # print(f"\n🚀 WebDriver 실행 중...")
        # with driver:
        #     driver.driver.get("https://www.aliexpress.com")
        #     print(f"   - Title: {driver.driver.title}")
        
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()


def test_compare_configs():
    """Test 4: 3개 설정 비교"""
    print("\n" + "=" * 80)
    print("Test 4: 3개 WebDriver 설정 비교")
    print("=" * 80)
    
    try:
        # ConfigLoader로 webdriver_config_loader.yaml 로드
        config_loader_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver_config_loader.yaml"
        
        if not config_loader_path.exists():
            print(f"❌ ConfigLoader YAML 파일을 찾을 수 없습니다: {config_loader_path}")
            return
        
        # ConfigLoader 생성
        config = ConfigLoader(config_loader_cfg_path=str(config_loader_path))
        
        # 3개 섹션 추출
        configs = {
            "webdriver": config.to_dict(section="webdriver"),
            "webdriver_china": config.to_dict(section="webdriver_china"),
            "webdriver_global": config.to_dict(section="webdriver_global"),
        }
        
        print("\n📊 설정 비교:")
        print("-" * 80)
        print(f"{'항목':<25} | {'webdriver':<20} | {'webdriver_china':<20} | {'webdriver_global':<20}")
        print("-" * 80)
        
        # 주요 항목 비교
        keys = ["provider", "region", "headless", "accept_languages"]
        for key in keys:
            row = f"{key:<25}"
            for name in ["webdriver", "webdriver_china", "webdriver_global"]:
                value = configs[name].get(key, "N/A")
                if isinstance(value, str) and len(value) > 18:
                    value = value[:15] + "..."
                row += f" | {str(value):<20}"
            print(row)
        
        # Firefox Profile 비교
        print("-" * 80)
        print("\n🦊 Firefox Profile 경로 비교:")
        for name in ["webdriver", "webdriver_china", "webdriver_global"]:
            firefox_config = configs[name].get("firefox", {})
            profile_path = firefox_config.get("profile_path", "N/A")
            print(f"   - {name:<20}: {profile_path}")
        
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()


def test_actual_webdriver_run():
    """Test 5: 실제 WebDriver 실행 (선택사항)"""
    print("\n" + "=" * 80)
    print("Test 5: 실제 WebDriver 실행 (webdriver.yaml)")
    print("=" * 80)
    print("⚠️  이 테스트는 실제 Firefox WebDriver를 실행합니다.")
    print("⚠️  geckodriver와 Firefox가 설치되어 있어야 합니다.")
    
    response = input("\n실제 WebDriver를 실행하시겠습니까? (y/N): ")
    
    if response.lower() != 'y':
        print("❌ 테스트를 건너뜁니다.")
        return
    
    try:
        # ConfigLoader로 webdriver_config_loader.yaml 로드
        config_loader_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver_config_loader.yaml"
        
        if not config_loader_path.exists():
            print(f"❌ ConfigLoader YAML 파일을 찾을 수 없습니다: {config_loader_path}")
            return
        
        # ConfigLoader 생성
        config = ConfigLoader(config_loader_cfg_path=str(config_loader_path))
        
        # 'webdriver' 섹션 추출
        webdriver_config = config.to_dict(section="webdriver")
        
        print(f"\n🚀 FirefoxWebDriver 실행 중...")
        
        # YAML 파일 경로로 FirefoxWebDriver 생성
        yaml_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver.yaml"
        
        # FirefoxWebDriver 실행 (Context Manager)
        with FirefoxWebDriver(str(yaml_path)) as driver:
            # Google 접속
            driver.driver.get("https://www.google.com")
            print(f"✅ Google 접속 성공")
            print(f"   - URL: {driver.driver.current_url}")
            print(f"   - Title: {driver.driver.title}")
            
            # 3초 대기
            import time
            print(f"\n⏳ 3초 대기 중...")
            time.sleep(3)
        
        print(f"\n✅ WebDriver 종료 성공 (Context Manager)")
        
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 ConfigLoader WebDriver 3개 정책 테스트")
    print("=" * 80)
    print("테스트 파일:")
    print("  1. webdriver.yaml - 기본 글로벌 설정")
    print("  2. webdriver_china.yaml - 중국 지역 설정")
    print("  3. webdriver_global.yaml - 글로벌 지역 설정 (명시적)")
    print("=" * 80)
    print()
    
    # 테스트 실행
    test_webdriver_base()
    test_webdriver_china()
    test_webdriver_global()
    test_compare_configs()
    test_actual_webdriver_run()
    
    print("\n" + "=" * 80)
    print("✅ 모든 테스트 완료!")
    print("=" * 80)
