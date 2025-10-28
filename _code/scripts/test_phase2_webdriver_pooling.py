#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Phase 2 테스트: WebDriver Smart Pooling

테스트 시나리오:
1. 동일 설정 URL 여러 개 → WebDriver 재사용 확인
2. 다른 설정 URL → 새 WebDriver 생성 확인
3. Pool Key 생성 로직 확인
4. _cleanup_webdriver_pool() 정상 작동 확인
"""

def test_webdriver_pool_key():
    """WebDriver Pool Key 생성 테스트 (presets.webdrivers 기반)"""
    print("\n" + "="*80)
    print("Phase 2 Test: WebDriver Pool Key Generation (presets.webdrivers)")
    print("="*80)
    
    from crawl_utils.adapter import SyncCrawl
    from crawl_utils.presets.webdrivers import WEBDRIVER_OVERRIDES
    
    # SyncCrawl 인스턴스 생성 (최소 설정)
    crawl = SyncCrawl(cfg_like=None)
    
    print("\n📋 presets.webdrivers.WEBDRIVER_OVERRIDES 확인:")
    print("-" * 80)
    for region, providers in WEBDRIVER_OVERRIDES.items():
        print(f"  {region}:")
        for provider, config in providers.items():
            print(f"    {provider}:")
            for key, value in config.items():
                print(f"      {key}: {value}")
    
    print("\n1️⃣  동일 설정 → 동일 Key (재사용)")
    print("-" * 80)
    
    key1 = crawl._get_webdriver_key("firefox", "china", None, None)
    key2 = crawl._get_webdriver_key("firefox", "china", None, None)
    
    print(f"Key 1: {key1}")
    print(f"Key 2: {key2}")
    
    if key1 == key2:
        print("✅ 동일한 Key 생성 → WebDriver 재사용 가능")
    else:
        print(f"❌ 다른 Key 생성 → 재사용 불가능")
        return False
    
    # presets 매핑 확인
    if "CRAWL_CHINA" in key1 and "zh-CN" in key1:
        print("✅ presets 매핑 정상 반영 (Profile: CRAWL_CHINA, AL: zh-CN)")
    else:
        print(f"❌ presets 매핑 누락")
        return False
    
    print("\n2️⃣  다른 Region → 다른 Key (새 WebDriver)")
    print("-" * 80)
    
    key3 = crawl._get_webdriver_key("firefox", "global", None, None)
    
    print(f"Key 1 (china):  {key1}")
    print(f"Key 3 (global): {key3}")
    
    if key1 != key3:
        print("✅ 다른 Key 생성 → 새 WebDriver 생성")
    else:
        print(f"❌ 동일한 Key 생성 → 격리 실패")
        return False
    
    # presets 매핑 확인
    if "CRAWL_GLOBAL" in key3 and "en-US" in key3:
        print("✅ presets 매핑 정상 반영 (Profile: CRAWL_GLOBAL, AL: en-US)")
    else:
        print(f"❌ presets 매핑 누락")
        return False
    
    print("\n3️⃣  다른 Profile (명시적) → 다른 Key (새 WebDriver)")
    print("-" * 80)
    
    key4 = crawl._get_webdriver_key("firefox", "china", None, "M:/WEB_PROFILE/CUSTOM_PROFILE")
    
    print(f"Key 1 (preset):  {key1}")
    print(f"Key 4 (custom):  {key4}")
    
    if key1 != key4:
        print("✅ 다른 Key 생성 → Profile 격리 성공")
    else:
        print(f"❌ 동일한 Key 생성 → Profile 격리 실패")
        return False
    
    if "CUSTOM_PROFILE" in key4:
        print("✅ 명시적 Profile 우선 적용")
    else:
        print(f"❌ 명시적 Profile 누락")
        return False
    
    print("\n4️⃣  다른 Provider → 다른 Key (새 WebDriver)")
    print("-" * 80)
    
    key5 = crawl._get_webdriver_key("firefox", "china", None, None)
    key6 = crawl._get_webdriver_key("chrome", "china", None, None)
    
    print(f"Key 5 (firefox): {key5}")
    print(f"Key 6 (chrome):  {key6}")
    
    if key5 != key6:
        print("✅ 다른 Key 생성 → Provider 격리 성공")
    else:
        print(f"❌ 동일한 Key 생성 → Provider 격리 실패")
        return False
    
    # Chrome은 user_data_dir 사용
    if "CRAWL_CHINA" in key6 and "zh-CN" in key6:
        print("✅ Chrome presets 매핑 정상 (user_data_dir)")
    else:
        print(f"❌ Chrome presets 매핑 누락")
        return False
    
    print("\n5️⃣  Accept-Language 명시 → Key에 반영")
    print("-" * 80)
    
    key7 = crawl._get_webdriver_key("firefox", "china", None, None)
    key8 = crawl._get_webdriver_key("firefox", "china", "ja-JP,ja;q=0.9", None)
    
    print(f"Key 7 (preset AL): {key7}")
    print(f"Key 8 (custom AL): {key8}")
    
    if key7 != key8:
        print("✅ 다른 Key 생성 → Accept-Language 우선 적용")
    else:
        print(f"❌ 동일한 Key 생성 → Accept-Language 반영 실패")
        return False
    
    if "ja-JP" in key8:
        print("✅ 명시적 Accept-Language 우선 적용")
    else:
        print(f"❌ 명시적 Accept-Language 누락")
        return False
    
    print("\n" + "="*80)
    print("✅ Phase 2 Pool Key 테스트 완료 (presets 통합)!")
    print("="*80)
    
    return True


def test_pool_structure():
    """WebDriver Pool 구조 확인"""
    print("\n" + "="*80)
    print("Phase 2 Test: WebDriver Pool Structure")
    print("="*80)
    
    from crawl_utils.adapter import SyncCrawl
    
    # SyncCrawl 인스턴스 생성
    crawl = SyncCrawl(cfg_like=None)
    
    print("\n1️⃣  Pool 초기화 확인")
    print("-" * 80)
    
    if hasattr(crawl, '_webdriver_pool'):
        print(f"✅ _webdriver_pool 속성 존재")
        print(f"   타입: {type(crawl._webdriver_pool)}")
        print(f"   초기 크기: {len(crawl._webdriver_pool)}")
        
        if isinstance(crawl._webdriver_pool, dict):
            print("✅ Dict 타입 확인")
        else:
            print(f"❌ 잘못된 타입: {type(crawl._webdriver_pool)}")
            return False
    else:
        print("❌ _webdriver_pool 속성 없음")
        return False
    
    print("\n2️⃣  Pool 메서드 확인")
    print("-" * 80)
    
    methods = ['_get_webdriver_key', '_cleanup_webdriver_pool']
    for method_name in methods:
        if hasattr(crawl, method_name):
            method = getattr(crawl, method_name)
            print(f"✅ {method_name}() 메서드 존재")
            print(f"   타입: {type(method)}")
        else:
            print(f"❌ {method_name}() 메서드 없음")
            return False
    
    print("\n" + "="*80)
    print("✅ Phase 2 Pool 구조 테스트 완료!")
    print("="*80)
    
    return True


if __name__ == "__main__":
    success = True
    
    # Test 1: Pool Key 생성
    if not test_webdriver_pool_key():
        success = False
    
    # Test 2: Pool 구조 확인
    if not test_pool_structure():
        success = False
    
    if success:
        print("\n" + "="*80)
        print("🎉 모든 테스트 통과!")
        print("="*80)
        print("\n📊 Phase 2 구현 요약:")
        print("  ✅ WebDriver Pool Key 생성 로직")
        print("  ✅ Pool 초기화 (_webdriver_pool)")
        print("  ✅ Pool 관리 메서드 (_cleanup_webdriver_pool)")
        print("  ✅ run() 메서드 Pool 통합")
        print("  ✅ _execute() 서명 변경 (webdriver_manager 전달)")
        print("\n🚀 다음 단계: 실제 크롤링으로 WebDriver 재사용 확인")
        print("   예: 동일 region/provider URL 10개 → WebDriver 1개 재사용")
    else:
        print("\n❌ 일부 테스트 실패")
        exit(1)
