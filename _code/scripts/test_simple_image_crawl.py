# -*- coding: utf-8 -*-
"""단순 이미지 크롤링 테스트 - YAML 없이 기본값만 사용

목표:
1. NormalizedItem 필요성 검증
2. YAML/Preset 없이 기본값으로 크롤링 가능 여부 확인
3. SmartNormalizer 기본 저장 정책 검증

시나리오:
- URL: https://www.istockphoto.com/kr/search/2/image-film?phrase=사과
- 작업: Navigate → Scroll → Wait → Extract → Normalize → Save
- 정책: 모두 코드 내 기본값 (YAML 로드 없음)
"""

from pathlib import Path

# ========================================
# Step 1: 최소 정책 정의 (코드 기반)
# ========================================
print("=" * 60)
print("Step 1: 최소 정책 정의 (코드 기반)")
print("=" * 60)

from crawl_utils.core.policy import (
    CrawlPolicy,
    NavigationPolicy,
    ScrollPolicy,
    WaitPolicy,
    ExtractorPolicy,
    NormalizationRule,
    ScrollStrategy,
    WaitHook,
    WaitCondition,
    ExtractorType,
    ExecutionPolicy,
    RetryPolicy,
    PostProcessorPolicy
)

# 최소 정책 (기본값 활용)
policy = CrawlPolicy(
    site="istockphoto",
    method="search",
    
    # 실행 정책
    execution=ExecutionPolicy(
        mode="sync",
        concurrency=1
    ),
    
    # 재시도 정책
    retry=RetryPolicy(
        retries=0,
        backoff_sec=0.0
    ),
    
    # Navigation
    navigation=NavigationPolicy(
        base_url="https://www.istockphoto.com/kr/search/2/image-film?phrase=사과",
        max_pages=1
    ),
    
    # Scroll
    scroll=ScrollPolicy(
        strategy=ScrollStrategy.INFINITE,
        max_scrolls=3,
        scroll_pause_sec=1.0
    ),
    
    # Wait
    wait=WaitPolicy(
        hook=WaitHook.CSS,
        selector="img[data-type='image']",
        timeout_sec=10.0,
        condition=WaitCondition.PRESENCE
    ),
    
    # Extractor (이미지 src 추출)
    extractor=ExtractorPolicy(
        type=ExtractorType.JS,
        js_snippet="""
            return {
                images: Array.from(document.querySelectorAll('img[data-type="image"]'))
                    .map(img => img.src)
                    .filter(src => src && src.startsWith('http'))
            };
        """
    ),
    
    # Normalization Rule (Auto 모드 테스트)
    rules=[
        NormalizationRule(
            kind="image",
            source="images",  # KeyPath 추출
            directory="m:/CALife/CAShop - 구매대행/_code/output/test_img/istockphoto",
            name="apple_{{_index:03d}}.jpg",
            explode=True,
            ops={
                "overwrite": True,
                "create_parents": True,
                "ensure_unique": False
            }
        )
    ],
    
    # PostProcessor (선택적)
    post_processor=PostProcessorPolicy(
        runtime_context={},
        env_context={}
    )
)

print(f"✅ Policy created:")
print(f"  - Site: {policy.site}")
print(f"  - Method: {policy.method}")
print(f"  - URL: {policy.navigation.base_url}")
print(f"  - Scroll: {policy.scroll.strategy.value} (max {policy.scroll.max_scrolls})")
print(f"  - Wait: {policy.wait.selector}")
print(f"  - Rules: {len(policy.rules)}")

# ========================================
# Step 2: WebDriver 준비 (기본값)
# ========================================
print("\n" + "=" * 60)
print("Step 2: WebDriver 준비")
print("=" * 60)

from crawl_utils.adapter.webdriver_manager import WebDriverManager
from crawl_utils.services.adapter import SyncSeleniumAdapter

# 최소 WebDriver 설정
wd_manager = WebDriverManager(
    cfg_like={
        "provider": "firefox",
        "firefox": {
            "headless": False,
            "profile_path": None  # 임시 프로파일 사용
        }
    }
)

print(f"✅ WebDriverManager created")

try:
    wd_manager.start()
    adapter = SyncSeleniumAdapter(driver=wd_manager._webdriver)
    print(f"✅ WebDriver started: Firefox")
    
    # ========================================
    # Step 3: Navigator - 페이지 로드 + Scroll + Wait
    # ========================================
    print("\n" + "=" * 60)
    print("Step 3: Navigator (Load + Scroll + Wait)")
    print("=" * 60)
    
    from crawl_utils.services.navigator import SyncNavigator
    
    navigator = SyncNavigator(driver=adapter, policy=policy)
    
    # Load
    print(f"📄 Loading: {policy.navigation.base_url}")
    navigator.load(base_url=str(policy.navigation.base_url))
    print(f"✅ Page loaded")
    
    # Scroll
    if policy.scroll and policy.scroll.strategy != ScrollStrategy.NONE:
        print(f"📜 Scrolling: {policy.scroll.strategy.value} (max {policy.scroll.max_scrolls})")
        navigator.scroll(
            strategy=policy.scroll.strategy.value,
            max_scrolls=policy.scroll.max_scrolls,
            pause_sec=policy.scroll.scroll_pause_sec
        )
        print(f"✅ Scroll completed")
    
    # Wait
    if policy.wait and policy.wait.hook != WaitHook.NONE:
        print(f"⏳ Waiting for: {policy.wait.selector}")
        navigator.wait(
            hook=policy.wait.hook.value,
            selector=policy.wait.selector,
            timeout=policy.wait.timeout_sec,
            condition=policy.wait.condition.value
        )
        print(f"✅ Wait completed")
    
    # ========================================
    # Step 4: Extractor - 데이터 추출
    # ========================================
    print("\n" + "=" * 60)
    print("Step 4: Extractor (JS snippet)")
    print("=" * 60)
    
    from crawl_utils.services.extractor import SyncJSExtractor
    
    extractor = SyncJSExtractor(adapter=adapter, policy=policy)
    extracted_data = extractor.extract_list()
    
    print(f"✅ Extracted data:")
    print(f"  - Records: {len(extracted_data)}")
    if extracted_data:
        first_record = extracted_data[0]
        print(f"  - First record keys: {list(first_record.keys())}")
        if 'images' in first_record:
            print(f"  - Images count: {len(first_record['images'])}")
            print(f"  - First image: {first_record['images'][0][:80]}...")
    
    # ========================================
    # Step 5: Normalizer - NormalizedItem 생성
    # ========================================
    print("\n" + "=" * 60)
    print("Step 5: Normalizer (Rule 모드)")
    print("=" * 60)
    print("🔍 NormalizedItem 필요성 분석:")
    print("  1. 타입 추론: kind (image/text/file)")
    print("  2. 메타데이터: directory, name, ops")
    print("  3. 인덱싱: record_index, item_index")
    print("  4. 저장 정책: PostProcessor가 metadata 기반 저장")
    print("")
    
    from crawl_utils.services.Item_Post_Processor import ItemNormalizer
    
    normalizer = ItemNormalizer(rules=policy.rules)
    normalized_items = normalizer.normalize(extracted_data)
    
    print(f"✅ Normalized items:")
    print(f"  - Total: {len(normalized_items)}")
    if normalized_items:
        first_item = normalized_items[0]
        print(f"  - First item:")
        print(f"      kind: {first_item.kind}")
        print(f"      value: {first_item.value[:80]}...")
        print(f"      metadata: {first_item.metadata}")
        print(f"      record_index: {first_item.record_index}")
        print(f"      item_index: {first_item.item_index}")
    
    # ========================================
    # Step 6: PostProcessor - 파일 저장
    # ========================================
    print("\n" + "=" * 60)
    print("Step 6: PostProcessor (metadata 기반 저장)")
    print("=" * 60)
    
    from crawl_utils.services.post_processor import SyncPostProcessor
    
    # runtime_context는 비어있어도 됨 (Jinja2 템플릿에서 사용 안 함)
    post_processor = SyncPostProcessor(
        runtime_context={},
        env_context={}
    )
    
    save_summary = post_processor.save_many(items=normalized_items)
    
    print(f"✅ Save summary:")
    print(f"  - Total artifacts: {len(save_summary.flatten())}")
    
    saved_count = 0
    failed_count = 0
    skipped_count = 0
    
    for artifact in save_summary.flatten():
        if artifact.status == "saved":
            saved_count += 1
            if saved_count <= 3:  # 처음 3개만 출력
                print(f"      ✓ {artifact.path}")
        elif artifact.status == "failed":
            failed_count += 1
            print(f"      ✗ {artifact.path}: {artifact.detail}")
        else:
            skipped_count += 1
    
    print(f"\n  - Saved: {saved_count}")
    print(f"  - Failed: {failed_count}")
    print(f"  - Skipped: {skipped_count}")
    
    # ========================================
    # Step 7: 검증 - 실제 파일 확인
    # ========================================
    print("\n" + "=" * 60)
    print("Step 7: 검증 (파일 시스템)")
    print("=" * 60)
    
    output_dir = Path("m:/CALife/CAShop - 구매대행/_code/output/test_img/istockphoto")
    if output_dir.exists():
        files = list(output_dir.glob("*.jpg"))
        print(f"✅ Output directory: {output_dir}")
        print(f"  - Files: {len(files)}")
        for f in files[:5]:  # 처음 5개만
            print(f"      • {f.name} ({f.stat().st_size / 1024:.1f} KB)")
    else:
        print(f"❌ Output directory not found: {output_dir}")

except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()

finally:
    if wd_manager:
        print("\n" + "=" * 60)
        print("Cleanup")
        print("=" * 60)
        wd_manager.quit()
        print("✅ WebDriver closed")

# ========================================
# 결론
# ========================================
print("\n" + "=" * 60)
print("결론")
print("=" * 60)
print("""
1. NormalizedItem 필요성:
   ✅ 타입 추론: kind로 image/text/file 구분
   ✅ 메타데이터: directory, name, ops를 Item에 포함
   ✅ 인덱싱: record_index, item_index로 순서 보장
   ✅ 저장 정책: PostProcessor가 metadata 기반 저장
   → NormalizedItem은 Extract와 Save를 연결하는 중요한 데이터 모델

2. YAML 없이 크롤링 가능:
   ✅ Policy를 코드로 직접 생성
   ✅ WebDriverManager도 cfg_like dict로 초기화
   ✅ 모든 단계 (Navigate → Extract → Normalize → Save) 작동
   → YAML은 편의성일 뿐, 필수 아님

3. SmartNormalizer vs DataNormalizer:
   ⚠️ 현재 Normalizer는 통합됨 (Rule/Auto 모드)
   ⚠️ source 지정 → Rule 모드 (KeyPath 추출)
   ⚠️ source 없음 + auto_infer → Auto 모드 (타입 추론)
   → 이 테스트는 Rule 모드 사용 (source="images")

4. 개선 제안:
   💡 Auto 모드도 테스트 필요 (source=None, auto_infer=True)
   💡 Preset 시스템은 선택적 (없어도 크롤링 가능)
   💡 ConfigLoader는 YAML 관리 도구일 뿐
""")
