# -*- coding: utf-8 -*-
"""sync_crawl.py v5.1 테스트

v5.1 변경사항:
1. Normalizer 통합 (Rule/Auto 모드)
2. PostProcessor 단순화 (metadata 기반)
3. 정책 계층화 (ExecutionPolicy, RetryPolicy, PostProcessorPolicy)
"""

from pathlib import Path

# ========================================
# Step 1: ConfigLoader로 xlcrawl_sync_crawl.yaml 로드
# ========================================
from cfg_utils import ConfigLoader

config_path = Path(__file__).parent.parent / "configs" / "xlcrawl" / "xlcrawl_sync_crawl.yaml"
print(f"✅ Loading config: {config_path}")

config = ConfigLoader(cfg_like=config_path)

# ========================================
# Step 2: SyncCrawl 초기화
# ========================================
from crawl_utils.adapter.sync_crawl import SyncCrawl

# cfg_like에 ConfigLoader 인스턴스 전달
crawl_service = SyncCrawl(
    cfg_like=config,
    log_section="log"
)

print(f"✅ SyncCrawl initialized")
print(f"  - Preset: {crawl_service.policy.preset}")
print(f"  - Site: {crawl_service.policy.crawl.site}")
print(f"  - Method: {crawl_service.policy.crawl.method}")

# ========================================
# Step 3: 크롤링 실행 (테스트 URL)
# ========================================
test_url = "https://www.aliexpress.com/item/1005007883068118.html"

# runtime_context 오버라이드
overrides = {
    "cas_no": "CAPEA-TEST-001",
    "site": "aliexpress",
    "method": "detail"
}

print(f"\n✅ Running crawl...")
print(f"  - URL: {test_url}")
print(f"  - Overrides: {overrides}")

try:
    results = crawl_service.run(urls=[test_url], **overrides)
    
    print(f"\n✅ Crawl completed!")
    print(f"  - Total results: {len(results)}")
    
    for idx, result in enumerate(results, 1):
        print(f"\n  Result #{idx}:")
        print(f"    - Success: {result.get('success', False)}")
        print(f"    - URL: {result.get('url', 'N/A')}")
        print(f"    - Site: {result.get('site', 'N/A')}")
        print(f"    - Method: {result.get('method', 'N/A')}")
        
        if result.get('success'):
            data = result.get('data', [])
            normalized = result.get('normalized_items', [])
            saved = result.get('saved_files', [])
            
            print(f"    - Extracted records: {len(data)}")
            print(f"    - Normalized items: {len(normalized)}")
            print(f"    - Saved files: {len(saved)}")
            
            if saved:
                print(f"    - Files:")
                for file_path in saved[:5]:  # 최대 5개만 출력
                    print(f"        • {file_path}")
        else:
            error = result.get('error', 'Unknown error')
            print(f"    - Error: {error}")

except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
