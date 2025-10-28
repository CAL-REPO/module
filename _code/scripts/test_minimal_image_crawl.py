# -*- coding: utf-8 -*-
"""최소 코드로 이미지 크롤링 - Auto 모드 (SmartNormalizer 스타일)

목표:
- YAML 없음
- Preset 없음
- source 없음 (Auto 모드)
- 최소한의 코드로 이미지만 저장
"""

from pathlib import Path

print("=" * 60)
print("최소 코드 이미지 크롤링 - Auto 모드")
print("=" * 60)

# ========================================
# 1. 정책 정의 (Auto 모드)
# ========================================
from crawl_utils.core.policy import (
    CrawlPolicy, NavigationPolicy, ScrollPolicy, WaitPolicy,
    ExtractorPolicy, NormalizationRule, ExecutionPolicy, RetryPolicy,
    PostProcessorPolicy, ScrollStrategy, WaitHook, ExtractorType
)

policy = CrawlPolicy(
    site="istockphoto",
    method="search",
    execution=ExecutionPolicy(mode="sync", concurrency=1),
    retry=RetryPolicy(retries=0, backoff_sec=0.0),
    
    navigation=NavigationPolicy(
        base_url="https://www.istockphoto.com/kr/search/2/image-film?phrase=사과",
        max_pages=1
    ),
    
    scroll=ScrollPolicy(
        strategy=ScrollStrategy.INFINITE,
        max_scrolls=2,
        scroll_pause_sec=1.0
    ),
    
    wait=WaitPolicy(
        hook=WaitHook.CSS,
        selector="img[data-type='image']",
        timeout_sec=10.0
    ),
    
    extractor=ExtractorPolicy(
        type=ExtractorType.JS,
        js_snippet="""
            return Array.from(document.querySelectorAll('img[data-type="image"]'))
                .map(img => img.src)
                .filter(src => src && src.startsWith('http'));
        """
    ),
    
    # Auto 모드: source 없음, auto_infer=True
    rules=[
        NormalizationRule(
            kind="image",
            source=None,  # Auto 모드
            auto_infer=True,
            directory="m:/CALife/CAShop - 구매대행/_code/output/test_img/auto_mode",
            name="auto_{{_index:03d}}",  # 확장자 자동 추론
            explode=True,
            ops={"overwrite": True, "create_parents": True}
        )
    ],
    
    post_processor=PostProcessorPolicy(
        runtime_context={},
        env_context={}
    )
)

print(f"✅ Policy: Auto 모드 (source=None, auto_infer=True)")

# ========================================
# 2. WebDriver 시작
# ========================================
from crawl_utils.adapter.webdriver_manager import WebDriverManager
from crawl_utils.services.adapter import SyncSeleniumAdapter

wd_manager = WebDriverManager(
    cfg_like={"provider": "firefox", "firefox": {"headless": False}}
)

try:
    wd_manager.start()
    adapter = SyncSeleniumAdapter(driver=wd_manager._webdriver)
    print(f"✅ WebDriver: Firefox")
    
    # ========================================
    # 3. Navigate + Scroll + Wait
    # ========================================
    from crawl_utils.services.navigator import SyncNavigator
    
    navigator = SyncNavigator(driver=adapter, policy=policy)
    navigator.load(base_url=str(policy.navigation.base_url))
    print(f"✅ Page loaded")
    
    navigator.scroll(
        strategy=policy.scroll.strategy.value,
        max_scrolls=policy.scroll.max_scrolls,
        pause_sec=policy.scroll.scroll_pause_sec,
        scroll_count=policy.scroll.scroll_count,
        step_px=policy.scroll.scroll_step_px,
    )
    print(f"✅ Scrolled {policy.scroll.max_scrolls} times")
    
    navigator.wait(
        hook=policy.wait.hook.value,
        selector=policy.wait.selector,
        timeout=policy.wait.timeout_sec
    )
    print(f"✅ Wait completed")
    
    # ========================================
    # 4. Extract (JS snippet → List[str])
    # ========================================
    from crawl_utils.services.extractor import SyncJSExtractor
    
    extractor = SyncJSExtractor(adapter=adapter, policy=policy)
    result = extractor.execute_js(policy.extractor.js_snippet)
    
    print(f"✅ Extracted: {len(result)} image URLs")
    
    # List[str]을 List[Dict]로 변환 (Normalizer 입력 형식)
    extracted_data = [{"value": url} for url in result[:10]]  # 최대 10개
    
    # ========================================
    # 5. Normalize (Auto 모드)
    # ========================================
    print("\n🔍 Auto 모드 동작:")
    print("  - source=None → record 전체를 value로 사용")
    print("  - auto_infer=True → TypeInferencer로 타입 추론")
    print("  - kind='image' → 확장자 자동 추론 (.jpg)")
    
    from crawl_utils.services.Item_Post_Processor import ItemNormalizer
    
    normalizer = ItemNormalizer(rules=policy.rules)
    normalized_items = normalizer.normalize(extracted_data)
    
    print(f"✅ Normalized: {len(normalized_items)} items")
    if normalized_items:
        first = normalized_items[0]
        print(f"  - First item:")
        print(f"      kind: {first.kind}")
        print(f"      metadata: {first.metadata}")
    
    # ========================================
    # 6. Save
    # ========================================
    from crawl_utils.services.post_processor import SyncPostProcessor
    
    post_processor = SyncPostProcessor(runtime_context={}, env_context={})
    save_summary = post_processor.save_many(items=normalized_items)
    
    saved = [a for a in save_summary.flatten() if a.status == "saved"]
    print(f"✅ Saved: {len(saved)} files")
    
    for artifact in saved[:3]:
        print(f"  • {artifact.path.name}")
    
    # ========================================
    # 7. 검증
    # ========================================
    output_dir = Path("m:/CALife/CAShop - 구매대행/_code/output/test_img/auto_mode")
    if output_dir.exists():
        files = list(output_dir.glob("*"))
        print(f"\n✅ Files in {output_dir}:")
        for f in files:
            print(f"  • {f.name} ({f.stat().st_size / 1024:.1f} KB)")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    if wd_manager:
        wd_manager.quit()
        print("\n✅ WebDriver closed")

print("\n" + "=" * 60)
print("결론: Auto 모드 (SmartNormalizer 스타일)")
print("=" * 60)
print("""
✅ source=None, auto_infer=True로 자동 추론 가능
✅ YAML/Preset 없이 코드만으로 크롤링 가능
✅ NormalizedItem은 metadata를 통해 저장 정책 전달
⚠️ 현재 Auto 모드는 record 전체를 value로 사용
   → List[str] 입력 시 각 str을 NormalizedItem으로 변환
""")
