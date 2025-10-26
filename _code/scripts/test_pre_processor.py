# -*- coding: utf-8 -*-
"""crawl_utils/services/pre_processor.py - Test Script

PreProcessor 테스트 스크립트

테스트 항목:
1. URL 분석 (analyze_url)
2. Preset 정책 로드 (get_crawl_policy)
3. 정책 병합 (process)
4. 이름 기반 Preset (preset_name)
"""

from pathlib import Path
import sys

# PYTHONPATH 설정
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from crawl_utils.services.pre_processor import PreProcessor
from crawl_utils.core.policy import CrawlPolicy
from crawl_utils.presets import (
    analyze_url,
    get_crawl_policy,
    register_named_preset,
)


def test_url_analysis():
    """URL 분석 테스트"""
    print("=" * 80)
    print("Test 1: URL 분석")
    print("=" * 80)
    
    test_urls = [
        "https://www.aliexpress.com/item/1005004567890123.html",
        "https://item.taobao.com/item.htm?id=123456789012",
        "https://detail.tmall.com/item.htm?id=987654321098",
    ]
    
    for url in test_urls:
        try:
            site, method, region = analyze_url(url)
            print(f"\n✅ URL: {url}")
            print(f"   Site: {site}, Method: {method}, Region: {region}")
        except ValueError as e:
            print(f"\n❌ URL: {url}")
            print(f"   Error: {e}")


def test_preset_policy():
    """Preset 정책 로드 테스트"""
    print("\n" + "=" * 80)
    print("Test 2: Preset 정책 로드")
    print("=" * 80)
    
    test_cases = [
        ("aliexpress", "detail"),
        ("taobao", "detail"),
        ("amazon", "detail"),  # 없는 Preset
    ]
    
    for site, method in test_cases:
        policy = get_crawl_policy(site, method)
        if policy:
            print(f"\n✅ Preset: ({site}, {method})")
            print(f"   Scroll max_scrolls: {policy.get('scroll', {}).get('max_scrolls', 'N/A')}")
            print(f"   Extractor type: {policy.get('extractor', {}).get('type', 'N/A')}")
        else:
            print(f"\n❌ Preset not found: ({site}, {method})")


def test_preprocessor_basic():
    """PreProcessor 기본 테스트 (정책 병합)"""
    print("\n" + "=" * 80)
    print("Test 3: PreProcessor 기본 테스트")
    print("=" * 80)
    
    # 기본 정책 생성 (간단한 기본값)
    base_policy = CrawlPolicy(
        site="",
        method="",
        scroll={
            "strategy": "infinite",
            "max_scrolls": 10,
            "scroll_pause_sec": 0.5
        },
        extractor={
            "type": "dom",
        }
    )
    
    print("\n📋 기본 정책:")
    print(f"   Scroll max_scrolls: {base_policy.scroll.max_scrolls}")
    print(f"   Extractor type: {base_policy.extractor.type}")
    
    # PreProcessor 생성
    preprocessor = PreProcessor(base_policy, enable_preset=True)
    
    # URL 처리
    url = "https://www.aliexpress.com/item/1005004567890123.html"
    final_policy = preprocessor.process(url)
    
    print(f"\n✅ URL 처리 완료: {url}")
    print(f"   Site: {final_policy.site}, Method: {final_policy.method}")
    print(f"   Scroll max_scrolls: {final_policy.scroll.max_scrolls} (Preset override)")
    print(f"   Extractor type: {final_policy.extractor.type} (Preset override)")
    
    # Preset 비활성화 테스트
    preprocessor_no_preset = PreProcessor(base_policy, enable_preset=False)
    final_policy_no_preset = preprocessor_no_preset.process(url)
    
    print(f"\n📋 Preset 비활성화:")
    print(f"   Scroll max_scrolls: {final_policy_no_preset.scroll.max_scrolls} (기본값 유지)")
    print(f"   Extractor type: {final_policy_no_preset.extractor.type} (기본값 유지)")


def test_named_preset():
    """이름 기반 Preset 테스트"""
    print("\n" + "=" * 80)
    print("Test 4: 이름 기반 Preset")
    print("=" * 80)
    
    # 이름 기반 Preset 등록
    register_named_preset("taobao_fast", {
        "scroll__max_scrolls": 5,  # KeyPath 형식
        "extractor__type": "js",
        "retries": 1,
    })
    
    print("\n📋 등록된 Named Preset: taobao_fast")
    print("   scroll__max_scrolls: 5")
    print("   extractor__type: js")
    print("   retries: 1")
    
    # 기본 정책
    base_policy = CrawlPolicy(
        site="",
        method="",
        scroll={"max_scrolls": 10},
        extractor={"type": "dom"},
        retries=3
    )
    
    # PreProcessor로 처리
    preprocessor = PreProcessor(base_policy, enable_preset=True)
    url = "https://item.taobao.com/item.htm?id=123456789012"
    
    # Named Preset 없이
    policy_without_named = preprocessor.process(url)
    print(f"\n✅ Named Preset 없이:")
    print(f"   Scroll max_scrolls: {policy_without_named.scroll.max_scrolls}")
    print(f"   Extractor type: {policy_without_named.extractor.type}")
    print(f"   Retries: {policy_without_named.retries}")
    
    # Named Preset 적용
    policy_with_named = preprocessor.process(url, preset_name="taobao_fast")
    print(f"\n✅ Named Preset 적용 (taobao_fast):")
    print(f"   Scroll max_scrolls: {policy_with_named.scroll.max_scrolls} (Override)")
    print(f"   Extractor type: {policy_with_named.extractor.type} (Override)")
    print(f"   Retries: {policy_with_named.retries} (Override)")


def test_merge_policy():
    """정책 병합 테스트"""
    print("\n" + "=" * 80)
    print("Test 5: 정책 병합 (Deep Merge)")
    print("=" * 80)
    
    base_policy = CrawlPolicy(
        site="",
        method="",
        scroll={
            "strategy": "infinite",
            "max_scrolls": 10,
            "scroll_pause_sec": 0.5
        },
        extractor={
            "type": "dom",
        },
        retries=3
    )
    
    preprocessor = PreProcessor(base_policy)
    
    # Test Deep Merge
    base_dict = {
        "scroll": {"max_scrolls": 10, "scroll_pause_sec": 0.5},
        "extractor": {"type": "dom"},
        "retries": 3
    }
    
    override_dict = {
        "scroll": {"max_scrolls": 20},  # scroll_pause_sec는 유지
        "extractor": {"type": "js", "js_snippet": "..."},
    }
    
    merged = preprocessor._merge_policies(base_dict, override_dict)
    
    print("\n📋 기본 정책:")
    print(f"   scroll: {base_dict['scroll']}")
    print(f"   extractor: {base_dict['extractor']}")
    print(f"   retries: {base_dict['retries']}")
    
    print("\n📋 Override 정책:")
    print(f"   scroll: {override_dict['scroll']}")
    print(f"   extractor: {override_dict['extractor']}")
    
    print("\n✅ 병합 결과:")
    print(f"   scroll: {merged['scroll']}")
    print(f"   extractor: {merged['extractor']}")
    print(f"   retries: {merged['retries']} (유지)")


if __name__ == "__main__":
    print("\n" + "🔬 PreProcessor 테스트 시작\n")
    
    try:
        test_url_analysis()
        test_preset_policy()
        test_preprocessor_basic()
        test_named_preset()
        test_merge_policy()
        
        print("\n" + "=" * 80)
        print("✅ 모든 테스트 완료!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
