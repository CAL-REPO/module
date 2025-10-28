#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Phase 1 테스트: UA 캐싱 및 개선사항 검증

테스트 항목:
1. WebDriverManager.start()에서 UA 자동 캐싱
2. browser_version.json 파일 생성 확인
3. Stealth Mode 적용 확인 (navigator.webdriver = false)
4. RandomScroll 파라미터 확인
"""

from pathlib import Path
import json

def test_ua_caching():
    """UA 캐싱 테스트"""
    print("\n" + "="*80)
    print("Phase 1 Test: UA Caching & Improvements")
    print("="*80)
    
    # 캐시 파일 경로
    cache_path = Path(__file__).parent.parent / "modules" / "crawl_utils" / "configs" / "browser_version.json"
    
    # 기존 캐시 삭제 (테스트 초기화)
    if cache_path.exists():
        print(f"🗑️  기존 캐시 삭제: {cache_path}")
        cache_path.unlink()
    
    print("\n1️⃣  WebDriverManager 시작 (UA 자동 캐싱)")
    print("-" * 80)
    
    try:
        from crawl_utils.adapter import WebDriverManager
        
        # WebDriver 시작 (UA 캐싱 자동 실행)
        # 기본 설정 파일 사용 (webdriver_manager.yaml)
        manager = WebDriverManager(
            cfg_like=Path(__file__).parent.parent / "modules" / "crawl_utils" / "configs" / "webdriver_manager.yaml",
            provider="firefox",
            region="korea",
            headless=True
        )
        
        print("⏳ WebDriver 시작 중...")
        manager.start()
        print("✅ WebDriver 시작 완료")
        
        # Stealth Mode 확인
        print("\n2️⃣  Stealth Mode 확인 (navigator.webdriver)")
        print("-" * 80)
        try:
            result = manager.driver.execute_script("return navigator.webdriver;")
            if result is False or result is None:
                print(f"✅ Stealth Mode 활성화: navigator.webdriver = {result}")
            else:
                print(f"⚠️  Stealth Mode 미적용: navigator.webdriver = {result}")
        except Exception as e:
            print(f"⚠️  Stealth Mode 확인 실패: {e}")
        
        # UA 캐싱 확인
        print("\n3️⃣  UA 캐싱 확인")
        print("-" * 80)
        
        if cache_path.exists():
            print(f"✅ 캐시 파일 생성 확인: {cache_path}")
            
            cache_data = json.loads(cache_path.read_text(encoding="utf-8"))
            
            if "firefox" in cache_data:
                firefox_data = cache_data["firefox"]
                print(f"✅ Provider: firefox")
                print(f"   - Version: {firefox_data.get('version')}")
                print(f"   - User-Agent: {firefox_data.get('user_agent')[:80]}...")
                print(f"   - Updated: {firefox_data.get('updated_at')}")
                print(f"   - Source: {firefox_data.get('source')}")
            else:
                print(f"⚠️  Firefox 데이터 없음")
        else:
            print(f"❌ 캐시 파일 생성 실패: {cache_path}")
        
        # WebDriver 종료
        print("\n4️⃣  WebDriver 종료")
        print("-" * 80)
        manager.quit()
        print("✅ WebDriver 종료 완료")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # RandomScroll 파라미터 확인
    print("\n5️⃣  RandomScroll 파라미터 확인")
    print("-" * 80)
    try:
        from crawl_utils.services import SyncNavigator
        import inspect
        
        scroll_signature = inspect.signature(SyncNavigator.scroll)
        params = list(scroll_signature.parameters.keys())
        
        if "randomness" in params:
            print(f"✅ randomness 파라미터 존재: {scroll_signature.parameters['randomness']}")
        else:
            print(f"⚠️  randomness 파라미터 없음")
        
        print(f"   전체 파라미터: {params}")
        
    except Exception as e:
        print(f"⚠️  RandomScroll 확인 실패: {e}")
    
    print("\n" + "="*80)
    print("✅ Phase 1 테스트 완료!")
    print("="*80)
    
    return True


if __name__ == "__main__":
    test_ua_caching()
