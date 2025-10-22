#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebDriverAdapter 테스트 - ImageLoad 패턴

3개의 YAML 파일로 WebDriver 실행:
1. webdriver.yaml - 기본 글로벌 설정
2. webdriver_china.yaml - 중국 지역 설정
3. webdriver_global.yaml - 글로벌 지역 설정 (명시적)
"""

from pathlib import Path
import sys

# PYTHONPATH 추가
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from crawl_utils.adapter import WebDriverAdapter


def test_webdriver_base():
    """Test 1: webdriver.yaml (기본 글로벌 설정)"""
    print("=" * 80)
    print("Test 1: webdriver.yaml (기본 글로벌 설정)")
    print("=" * 80)
    
    yaml_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver.yaml"
    
    if not yaml_path.exists():
        print(f"❌ YAML 파일을 찾을 수 없습니다: {yaml_path}")
        return
    
    try:
        adapter = WebDriverAdapter(str(yaml_path))
        print(f"✅ WebDriverAdapter 생성 성공")
        print(f"   - Provider: {adapter.provider}")
        print(f"   - Region: {adapter.region}")
        print(f"   - Headless: {adapter.config.headless}")
        print(f"   - Window Size: {adapter.config.window_size}")
        
        if adapter.config.firefox:
            print(f"   - Firefox Binary: {adapter.config.firefox.binary_path}")
            print(f"   - Firefox Profile: {adapter.config.firefox.profile_path or 'default'}")
        
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()


def test_webdriver_china():
    """Test 2: webdriver_china.yaml (중국 지역 설정)"""
    print("\n" + "=" * 80)
    print("Test 2: webdriver_china.yaml (중국 지역 설정)")
    print("=" * 80)
    
    yaml_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver_china.yaml"
    
    if not yaml_path.exists():
        print(f"❌ YAML 파일을 찾을 수 없습니다: {yaml_path}")
        return
    
    try:
        adapter = WebDriverAdapter(str(yaml_path))
        print(f"✅ WebDriverAdapter 생성 성공")
        print(f"   - Provider: {adapter.provider}")
        print(f"   - Region: {adapter.region}")
        print(f"   - Accept-Languages: {adapter.config.accept_languages}")
        
        if adapter.config.firefox:
            print(f"   - Firefox Profile: {adapter.config.firefox.profile_path}")
        
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()


def test_webdriver_global():
    """Test 3: webdriver_global.yaml (글로벌 지역 설정)"""
    print("\n" + "=" * 80)
    print("Test 3: webdriver_global.yaml (글로벌 지역 설정)")
    print("=" * 80)
    
    yaml_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver_global.yaml"
    
    if not yaml_path.exists():
        print(f"❌ YAML 파일을 찾을 수 없습니다: {yaml_path}")
        return
    
    try:
        adapter = WebDriverAdapter(str(yaml_path))
        print(f"✅ WebDriverAdapter 생성 성공")
        print(f"   - Provider: {adapter.provider}")
        print(f"   - Region: {adapter.region}")
        print(f"   - Accept-Languages: {adapter.config.accept_languages}")
        
        if adapter.config.firefox:
            print(f"   - Firefox Profile: {adapter.config.firefox.profile_path}")
        
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()


def test_actual_webdriver_run():
    """Test 4: 실제 WebDriver 실행 (선택사항)"""
    print("\n" + "=" * 80)
    print("Test 4: 실제 WebDriver 실행 (webdriver_china.yaml)")
    print("=" * 80)
    print("⚠️  이 테스트는 실제 Firefox WebDriver를 실행합니다.")
    print("⚠️  geckodriver와 Firefox가 설치되어 있어야 합니다.")
    
    response = input("\n실제 WebDriver를 실행하시겠습니까? (y/N): ")
    
    if response.lower() != 'y':
        print("❌ 테스트를 건너뜁니다.")
        return
    
    yaml_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver_china.yaml"
    
    if not yaml_path.exists():
        print(f"❌ YAML 파일을 찾을 수 없습니다: {yaml_path}")
        return
    
    try:
        print(f"\n🚀 WebDriverAdapter 실행 중...")
        
        # Context Manager 사용
        with WebDriverAdapter(str(yaml_path)) as adapter:
            # Google 접속
            adapter.driver.get("https://www.google.com")
            print(f"✅ Google 접속 성공")
            print(f"   - URL: {adapter.driver.current_url}")
            print(f"   - Title: {adapter.driver.title}")
            
            # 3초 대기
            import time
            print(f"\n⏳ 3초 대기 중...")
            time.sleep(3)
        
        print(f"\n✅ WebDriver 종료 성공 (Context Manager)")
        
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()


def test_pattern_consistency():
    """Test 5: ImageLoad 패턴 일관성 확인"""
    print("\n" + "=" * 80)
    print("Test 5: ImageLoad 패턴 일관성 확인")
    print("=" * 80)
    
    import inspect
    from crawl_utils.adapter.webdriver import WebDriverAdapter
    
    try:
        from image_utils.adapter.load import ImageLoad
        
        # _load_config 메서드 비교
        webdriver_source = inspect.getsource(WebDriverAdapter._load_config)
        imageload_source = inspect.getsource(ImageLoad._load_config)
        
        webdriver_uses_pattern = 'ConfigLikeLoader.load_with_caller_path' in webdriver_source
        imageload_uses_pattern = 'ConfigLikeLoader.load_with_caller_path' in imageload_source
        
        print(f"\n✅ 패턴 분석:")
        print(f"   - WebDriverAdapter: {webdriver_uses_pattern}")
        print(f"   - ImageLoad: {imageload_uses_pattern}")
        
        if webdriver_uses_pattern and imageload_uses_pattern:
            print("\n🎉 두 adapter가 동일한 ConfigLikeLoader 패턴을 사용합니다!")
            print("   ✅ ImageLoad 패턴 일관성 유지!")
        
    except ImportError:
        print("\n⚠️ ImageLoad를 import할 수 없습니다. 패턴 비교를 건너뜁니다.")


if __name__ == "__main__":
    print("\n🚀 WebDriverAdapter 테스트 (ImageLoad 패턴)")
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
    test_actual_webdriver_run()
    test_pattern_consistency()
    
    print("\n" + "=" * 80)
    print("✅ 모든 테스트 완료!")
    print("=" * 80)
    print("\n💡 사용법:")
    print("   from crawl_utils.adapter import WebDriverAdapter")
    print('   with WebDriverAdapter("configs/webdriver_china.yaml") as adapter:')
    print('       adapter.driver.get("https://taobao.com")')
    print("=" * 80)
