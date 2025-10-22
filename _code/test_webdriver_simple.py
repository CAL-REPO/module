#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebDriverManager 간단 테스트

ConfigLoader를 사용하여 WebDriver를 실행하는 최소 예제
"""

from pathlib import Path
import sys

# PYTHONPATH 추가
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from crawl_utils.adapter import WebDriverManager


def test_basic_webdriver():
    """기본 WebDriver 테스트 (webdriver.yaml)"""
    print("\n" + "=" * 70)
    print("🚀 WebDriver 기본 테스트")
    print("=" * 70)
    
    yaml_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver.yaml"
    
    print(f"📄 Config: {yaml_path.name}")
    
    try:
        # WebDriverManager 생성
        adapter = WebDriverManager(str(yaml_path))
        
        print(f"✅ Adapter 생성 성공")
        print(f"   - Provider: {adapter.config.provider}")
        print(f"   - Region: {adapter.config.region}")
        print(f"   - Headless: {adapter.config.headless}")
        
        # 실제 WebDriver 실행 여부 확인
        response = input("\n🔥 실제 WebDriver를 실행하시겠습니까? (y/N): ")
        
        if response.lower() != 'y':
            print("⏭️  WebDriver 실행을 건너뜁니다.")
            return
        
        # Context Manager로 WebDriver 실행
        print("\n🌐 WebDriver 시작...")
        with adapter:
            # Google 접속
            adapter.driver.get("https://www.google.com")
            print(f"✅ 페이지 로드 성공!")
            print(f"   - URL: {adapter.driver.current_url}")
            print(f"   - Title: {adapter.driver.title}")
            
            # 3초 대기
            import time
            print(f"\n⏳ 3초 대기...")
            time.sleep(3)
        
        print(f"\n✅ WebDriver 종료 완료")
        
    except FileNotFoundError as e:
        print(f"❌ 파일을 찾을 수 없습니다: {e}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def test_china_webdriver():
    """중국 지역 WebDriver 테스트 (webdriver_china.yaml)"""
    print("\n" + "=" * 70)
    print("🇨🇳 WebDriver 중국 지역 테스트")
    print("=" * 70)
    
    yaml_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver_china.yaml"
    
    print(f"📄 Config: {yaml_path.name}")
    
    try:
        # WebDriverManager 생성
        adapter = WebDriverManager(str(yaml_path))
        
        print(f"✅ Adapter 생성 성공")
        print(f"   - Provider: {adapter.config.provider}")
        print(f"   - Region: {adapter.config.region}")
        print(f"   - Accept-Languages: {adapter.config.accept_languages}")
        
        # Firefox Profile 확인
        if adapter.config.firefox and adapter.config.firefox.profile_path:
            print(f"   - Firefox Profile: {adapter.config.firefox.profile_path}")
        
        print("\n💡 이 설정은 중국 지역(Taobao 등)을 위한 WebDriver입니다.")
        
    except FileNotFoundError as e:
        print(f"❌ 파일을 찾을 수 없습니다: {e}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def test_dict_config():
    """dict로 직접 설정 테스트"""
    print("\n" + "=" * 70)
    print("📝 dict 직접 설정 테스트")
    print("=" * 70)
    
    try:
        # dict로 직접 설정
        config_dict = {
            "provider": "firefox",
            "region": "test",
            "headless": True,
            "window_size": [1280, 720],
            "firefox": {
                "binary_path": "C:/Program Files/Mozilla Firefox/firefox.exe",
                "driver_path": "M:/WebDriver/geckodriver_win32.exe",
            }
        }
        
        print(f"📋 설정:")
        print(f"   - Provider: {config_dict['provider']}")
        print(f"   - Region: {config_dict['region']}")
        print(f"   - Headless: {config_dict['headless']}")
        print(f"   - Window Size: {config_dict['window_size']}")
        
        # WebDriverManager 생성
        adapter = WebDriverManager(config_dict)
        
        print(f"\n✅ Adapter 생성 성공")
        print(f"   - Config Type: {type(adapter.config).__name__}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧪 WebDriverManager 간단 테스트")
    print("=" * 70)
    print()
    print("테스트 시나리오:")
    print("  1. webdriver.yaml (기본 글로벌)")
    print("  2. webdriver_china.yaml (중국 지역)")
    print("  3. dict 직접 설정")
    print("=" * 70)
    
    # 테스트 실행
    test_basic_webdriver()
    test_china_webdriver()
    test_dict_config()
    
    print("\n" + "=" * 70)
    print("✅ 모든 테스트 완료!")
    print("=" * 70)
    print()
    print("💡 사용법:")
    print("   from crawl_utils.adapter import WebDriverManager")
    print("   ")
    print("   # YAML 파일 사용")
    print('   with WebDriverManager("configs/webdriver.yaml") as adapter:')
    print('       adapter.driver.get("https://google.com")')
    print("   ")
    print("   # dict 직접 사용")
    print('   adapter = WebDriverManager({"provider": "firefox", ...})')
    print("=" * 70)
