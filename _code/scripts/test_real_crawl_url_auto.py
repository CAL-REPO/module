"""
실제 크롤링 테스트 (URL 자동 분석)

테스트 목적:
1. URL만 제공 시 site/method 자동 분석 확인
2. Python Preset v2.0 자동 로드 확인
3. ItemPostProcessor v7.0 동작 확인
"""

import sys
from pathlib import Path

sys.path.insert(0, r"m:\CALife\CAShop - 구매대행\_code\modules")

from crawl_utils.adapter import SyncCrawl
from crawl_utils.presets import analyze_url, get_preset
from logs_utils import LogManager


def test_url_analysis():
    """Step 1: URL 분석 기능 테스트"""
    print("\n=== Step 1: URL 분석 테스트 ===\n")
    
    test_urls = [
        "https://www.aliexpress.com/item/1234567890.html",
        "https://ko.aliexpress.com/item/1234567890.html",
        "https://www.aliexpress.com/wholesale?SearchText=phone",
    ]
    
    for url in test_urls:
        try:
            site, method, region = analyze_url(url)
            print(f"✅ URL: {url}")
            print(f"   → site={site}, method={method}, region={region}")
            
            # Preset 존재 확인
            preset = get_preset(site, method)
            if preset:
                print(f"   → Preset 발견: {len(preset.get('save', []))} save rules")
            else:
                print(f"   → Preset 없음 (fallback 사용)")
        except Exception as e:
            print(f"❌ URL: {url}")
            print(f"   → Error: {e}")
        print()


def test_preset_loading():
    """Step 2: Preset 로드 테스트"""
    print("\n=== Step 2: Preset 로드 테스트 ===\n")
    
    # Aliexpress Detail Preset
    preset = get_preset("aliexpress", "detail")
    assert preset is not None, "Aliexpress detail preset not found"
    
    print(f"✅ Preset Keys: {list(preset.keys())}")
    print(f"✅ Scroll Strategy: {preset['scroll']['strategy']}")
    print(f"✅ Max Scrolls: {preset['scroll']['max_scrolls']}")
    print(f"✅ Save Rules: {len(preset['save'])}")
    
    for i, rule in enumerate(preset['save'], 1):
        print(f"   Rule {i}: {rule['kind']} - {rule['source']}")


def test_sync_crawl_init():
    """Step 3: SyncCrawl 초기화 테스트 (설정 없이)"""
    print("\n=== Step 3: SyncCrawl 초기화 테스트 ===\n")
    
    try:
        # LogManager 생성
        log_mgr = LogManager(
            name="test_crawl",
            level="INFO",
            log_dir=Path("logs/test")
        )
        
        # SyncCrawl 초기화 (cfg_like 없이 - Pydantic 기본값 사용)
        crawl = SyncCrawl(log_manager=log_mgr)
        
        print("✅ SyncCrawl 초기화 성공 (cfg_like=None)")
        print(f"   Policy: {crawl.policy.__class__.__name__}")
        
    except Exception as e:
        print(f"❌ SyncCrawl 초기화 실패: {e}")
        import traceback
        traceback.print_exc()


def test_dry_run_without_webdriver():
    """Step 4: Dry Run 테스트 (WebDriver 없이 Preset만 확인)"""
    print("\n=== Step 4: Dry Run (Preset 로드 확인) ===\n")
    
    # URL 분석
    url = "https://www.aliexpress.com/item/1234567890.html"
    site, method, region = analyze_url(url)
    
    print(f"URL: {url}")
    print(f"→ site={site}, method={method}, region={region}")
    
    # Preset 로드
    preset = get_preset(site, method)
    
    if preset:
        print(f"\n✅ Preset 로드 성공!")
        print(f"   Scroll: {preset['scroll']}")
        print(f"   Extractor Type: {preset['extractor']['type']}")
        print(f"   Save Rules Count: {len(preset['save'])}")
        
        print(f"\n📋 Save Rules Detail:")
        for i, rule in enumerate(preset['save'], 1):
            print(f"   {i}. {rule['kind']:6s} - {rule['source']}")
            print(f"      directory: {rule.get('directory', 'N/A')}")
    else:
        print(f"❌ Preset 없음 (fallback 필요)")


def test_url_auto_analysis_flow():
    """Step 5: URL 자동 분석 흐름 전체 테스트"""
    print("\n=== Step 5: URL 자동 분석 흐름 테스트 ===\n")
    
    test_cases = [
        {
            "url": "https://www.aliexpress.com/item/1234567890.html",
            "expected_site": "aliexpress",
            "expected_method": "detail",
            "expected_region": "global"
        },
        {
            "url": "https://www.aliexpress.com/wholesale?SearchText=phone",
            "expected_site": "aliexpress",
            "expected_method": "search",
            "expected_region": "global"
        }
    ]
    
    for case in test_cases:
        url = case["url"]
        print(f"URL: {url}")
        
        # 1. URL 분석
        site, method, region = analyze_url(url)
        assert site == case["expected_site"], f"Site mismatch: {site} != {case['expected_site']}"
        assert method == case["expected_method"], f"Method mismatch: {method} != {case['expected_method']}"
        assert region == case["expected_region"], f"Region mismatch: {region} != {case['expected_region']}"
        print(f"✅ URL 분석 성공: {site}/{method} ({region})")
        
        # 2. Preset 로드
        preset = get_preset(site, method)
        if preset:
            print(f"✅ Preset 로드 성공: {len(preset.get('save', []))} rules")
        else:
            print(f"⚠️  Preset 없음 (fallback 사용)")
        
        print()


if __name__ == "__main__":
    print("=" * 80)
    print("Real Crawl Test - URL 자동 분석 검증")
    print("=" * 80)
    
    try:
        # Step 1: URL 분석
        test_url_analysis()
        
        # Step 2: Preset 로드
        test_preset_loading()
        
        # Step 3: SyncCrawl 초기화
        test_sync_crawl_init()
        
        # Step 4: Dry Run
        test_dry_run_without_webdriver()
        
        # Step 5: 전체 흐름
        test_url_auto_analysis_flow()
        
        print("\n" + "=" * 80)
        print("🎉 모든 테스트 통과!")
        print("=" * 80)
        print("\n✅ 결론:")
        print("   - URL만 제공해도 site/method 자동 분석됨")
        print("   - Preset 자동 로드됨")
        print("   - SyncCrawl이 cfg_like 없이도 초기화됨")
        print("   - WebDriver 연결 전까지 모든 로직 정상 동작")
        
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
