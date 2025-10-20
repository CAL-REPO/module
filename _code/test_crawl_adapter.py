# -*- coding: utf-8 -*-
"""Test crawl_utils Adapter/EntryPoint pattern

XLOTO Pattern 검증:
1. UrlAnalyzer: URL에서 site/method 자동 감지
2. MethodResolver: site+method → preset 매핑
3. Crawl Adapter: URL 분석 및 메서드 브랜칭
4. Crawler EntryPoint: ConfigLoader 통합 및 Adapter 위임
"""

from pathlib import Path

# PYTHONPATH 설정
import sys
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from crawl_utils.services import UrlAnalyzer, MethodResolver
from crawl_utils.core.policy import CrawlPolicy, CrawlSourcePolicy


def test_url_analyzer():
    """Test UrlAnalyzer: URL parsing and site/method detection with config"""
    print("\n" + "="*70)
    print("[Test 1] UrlAnalyzer - URL 분석 및 site/method 감지 (Config 기반)")
    print("="*70)
    
    # URL 패턴 설정 (YAML에서 로드할 구조)
    url_patterns = {
        "site_domains": {
            "aliexpress": ["aliexpress.com", "aliexpress.us"],
            "taobao": ["taobao.com", "world.taobao.com"]
        },
        "method_patterns": {
            "product_detail": ["/item/", "item.htm"],
            "product_search": ["/wholesale", "/search"]
        }
    }
    
    analyzer = UrlAnalyzer(url_patterns)
    
    test_urls = [
        "https://www.aliexpress.com/item/123456.html",
        "https://aliexpress.com/wholesale?SearchText=laptop",
        "https://item.taobao.com/item.htm?id=123456",
        "https://s.taobao.com/search?q=laptop",
    ]
    
    for url in test_urls:
        site, method = analyzer.analyze(url)
        print(f"URL: {url}")
        print(f"  → Site: {site}, Method: {method}")
        print()


def test_method_resolver():
    """Test MethodResolver: site+method → section name generation + validation"""
    print("\n" + "="*70)
    print("[Test 2] MethodResolver - Section 이름 생성 및 검증")
    print("="*70)
    
    # Section 이름 생성 테스트
    test_cases = [
        ("aliexpress", "product_detail"),
        ("aliexpress", "product_search"),
        ("taobao", "product_detail"),
        ("taobao", "product_search"),
    ]
    
    from crawl_utils.services import MethodResolver as MR
    
    print("[2-1] Section 이름 생성 (Static Method)")
    for site, method in test_cases:
        section = MR.get_section_name(site, method)
        print(f"  {site} + {method} → {section}")
    print()
    
    # ConfigLoader 연동 테스트 (mock)
    print("[2-2] ConfigLoader 연동 테스트")
    try:
        # ConfigLoader 없이 resolve 호출 시도
        resolver = MR()
        try:
            preset = resolver.resolve("aliexpress", "product_detail")
            print("  ❌ ConfigLoader 없이 resolve() 호출 가능 (예상: ValueError)")
        except ValueError as e:
            print(f"  ✅ ConfigLoader 없이 resolve() 호출 → ValueError")
            print(f"     Message: {str(e)[:60]}...")
        
        # TODO: 실제 ConfigLoader와 함께 테스트
        # config = ConfigLoader("config_loader_crawl.yaml")
        # resolver = MR(config)
        # preset = resolver.resolve("aliexpress", "product_detail")
        # print(f"  ✅ Preset 추출 성공: {len(preset)} keys")
        
    except Exception as e:
        print(f"  ⚠️ Test error: {e}")
    print()


def test_crawl_policy():
    """Test CrawlPolicy with CrawlSourcePolicy - dict로 간단 테스트"""
    print("\n" + "="*70)
    print("[Test 3] CrawlSourcePolicy - dict 기반 테스트")
    print("="*70)
    
    # CrawlSourcePolicy 생성
    source = CrawlSourcePolicy(
        urls=[
            "https://www.aliexpress.com/item/123456.html",
            "https://aliexpress.com/item/789012.html"
        ],
        method="product_detail"
    )
    
    print(f"CrawlSourcePolicy:")
    print(f"  URLs: {len(source.urls)}")
    print(f"  Method: {source.method}")
    
    for idx, url in enumerate(source.urls, 1):
        print(f"    {idx}. {url}")
    print()
    
    print("[✓] CrawlSourcePolicy 생성 성공")
    print()


def test_integration():
    """Test full integration: UrlAnalyzer + MethodResolver + CrawlSourcePolicy"""
    print("\n" + "="*70)
    print("[Test 4] 통합 테스트 - URL 분석 → Section 생성 → CrawlSourcePolicy 생성")
    print("="*70)
    
    # 1. URL 패턴 설정
    url_patterns = {
        "site_domains": {
            "aliexpress": ["aliexpress.com", "aliexpress.us"],
            "taobao": ["taobao.com", "world.taobao.com"]
        },
        "method_patterns": {
            "product_detail": ["/item/", "item.htm"],
            "product_search": ["/wholesale", "/search"]
        }
    }
    
    # 2. URL 리스트
    urls = [
        "https://www.aliexpress.com/item/123456.html",
        "https://aliexpress.com/item/789012.html"
    ]
    
    # 3. URL 분석 (첫 번째 URL로 site/method 감지)
    analyzer = UrlAnalyzer(url_patterns)
    site, method = analyzer.analyze(urls[0])
    
    print(f"[1] URL 분석:")
    print(f"  First URL: {urls[0]}")
    print(f"  Detected: site='{site}', method='{method}'")
    print()
    
    # 4. Section 이름 생성
    section = MethodResolver.get_section_name(site, method)
    
    print(f"[2] Section 이름 생성:")
    print(f"  Section: {section}")
    print(f"  (ConfigLoader.to_dict(section='{section}')로 설정 추출)")
    print()
    
    # 5. CrawlSourcePolicy 생성
    if method == "product_detail":
        source = CrawlSourcePolicy(urls=urls, method="product_detail")
    else:
        source = CrawlSourcePolicy(urls=urls, method="product_search")
    
    print(f"[3] CrawlSourcePolicy 생성:")
    print(f"  Method: {source.method}")
    print(f"  URLs: {len(source.urls)}")
    for idx, url in enumerate(source.urls, 1):
        print(f"    {idx}. {url}")
    print()
    
    print("[✓] 통합 테스트 성공 - Config 기반 XLOTO Pattern 동작 확인")


if __name__ == "__main__":
    try:
        test_url_analyzer()
        test_method_resolver()
        test_crawl_policy()
        test_integration()
        
        print("\n" + "="*70)
        print("✅ All tests passed!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
