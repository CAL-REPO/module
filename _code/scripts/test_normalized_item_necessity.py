# -*- coding: utf-8 -*-
"""NormalizedItem 필요성 검증 - Unit Test (WebDriver 불필요)

목표:
1. NormalizedItem이 Extract와 Save를 어떻게 연결하는지 검증
2. YAML 없이 Policy 생성 가능 여부 확인
3. Normalizer의 Rule/Auto 모드 동작 확인
"""

from pathlib import Path
import json

print("=" * 70)
print("NormalizedItem 필요성 검증 - Unit Test")
print("=" * 70)

# ========================================
# Step 1: Extract 결과 시뮬레이션
# ========================================
print("\n[Step 1] Extract 결과 시뮬레이션")
print("-" * 70)

# 실제 크롤링 결과 예시
extracted_data = [
    {
        "title": "사과 - 신선한 과일",
        "images": [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
            "https://example.com/image3.jpg"
        ],
        "price": 1000,
        "pdf_url": "https://example.com/catalog.pdf"
    }
]

print(f"✅ Extract 결과:")
print(f"  - Records: {len(extracted_data)}")
print(f"  - Keys: {list(extracted_data[0].keys())}")
print(f"  - Images: {len(extracted_data[0]['images'])} URLs")

# ========================================
# Step 2: YAML 없이 Policy 생성
# ========================================
print("\n[Step 2] YAML 없이 Policy 생성")
print("-" * 70)

from crawl_utils.core.policy import (
    CrawlPolicy, NavigationPolicy, ExtractorPolicy,
    NormalizationRule, ExecutionPolicy, RetryPolicy,
    PostProcessorPolicy, ExtractorType
)

# 코드로 직접 정책 생성 (YAML 불필요)
policy = CrawlPolicy(
    site="example",
    method="detail",
    
    execution=ExecutionPolicy(mode="sync", concurrency=1),
    retry=RetryPolicy(retries=0, backoff_sec=0.0),
    
    navigation=NavigationPolicy(
        base_url="https://example.com",
        max_pages=1
    ),
    
    extractor=ExtractorPolicy(
        type=ExtractorType.JS,
        js_snippet="return {};"
    ),
    
    # Rule 모드: source 지정
    rules=[
        # 이미지 저장 규칙
        NormalizationRule(
            kind="image",
            source="images",  # KeyPath
            directory="m:/CALife/CAShop - 구매대행/_code/output/test/images",
            name="product_{{_index:03d}}.jpg",
            explode=True,  # 리스트 분리
            ops={"overwrite": True, "create_parents": True}
        ),
        # 텍스트 저장 규칙
        NormalizationRule(
            kind="text",
            source="title",
            directory="m:/CALife/CAShop - 구매대행/_code/output/test/texts",
            name="title.txt",
            ops={"overwrite": True, "create_parents": True}
        ),
        # PDF 저장 규칙
        NormalizationRule(
            kind="file",
            source="pdf_url",
            directory="m:/CALife/CAShop - 구매대행/_code/output/test/files",
            name="catalog.pdf",
            ops={"overwrite": True, "create_parents": True}
        )
    ],
    
    post_processor=PostProcessorPolicy(
        runtime_context={},
        env_context={}
    )
)

print(f"✅ Policy 생성 완료:")
print(f"  - Site: {policy.site}")
print(f"  - Method: {policy.method}")
print(f"  - Rules: {len(policy.rules)}")
print(f"  - YAML 사용: ❌ (코드로 직접 생성)")

# ========================================
# Step 3: Normalizer 실행 (Rule 모드)
# ========================================
print("\n[Step 3] Normalizer 실행 (Rule 모드)")
print("-" * 70)

from crawl_utils.services.Item_Post_Processor import ItemNormalizer

normalizer = ItemNormalizer(rules=policy.rules)
normalized_items = normalizer.normalize(extracted_data)

print(f"✅ Normalization 완료:")
print(f"  - Input records: {len(extracted_data)}")
print(f"  - Output items: {len(normalized_items)}")
print(f"\n  📦 NormalizedItem 상세:")

for idx, item in enumerate(normalized_items, 1):
    print(f"\n  [{idx}] {item.kind.upper()}")
    print(f"      value: {str(item.value)[:60]}...")
    print(f"      metadata:")
    print(f"        - directory: {item.metadata.get('directory', 'N/A')}")
    print(f"        - name: {item.metadata.get('name', 'N/A')}")
    print(f"        - ops: {item.metadata.get('ops', {})}")
    print(f"      index: record[{item.record_index}], item[{item.item_index}]")

# ========================================
# Step 4: NormalizedItem의 역할 분석
# ========================================
print("\n[Step 4] NormalizedItem의 역할 분석")
print("-" * 70)

print("""
🔍 NormalizedItem이 해결하는 문제:

1️⃣ 타입 추론 결과 저장:
   - Extract: {"images": [...], "title": "...", "pdf_url": "..."}
   - Normalize: [NormalizedItem(kind="image"), NormalizedItem(kind="text"), ...]
   → kind 필드로 image/text/file 명확히 구분

2️⃣ 저장 정책 전달:
   - NormalizationRule: directory, name, ops 정의
   - NormalizedItem.metadata: 렌더링된 저장 경로 포함
   → PostProcessor는 metadata만 읽고 파일 저장

3️⃣ 인덱싱:
   - explode=True → 리스트를 개별 Item으로 분리
   - item_index로 순서 추적
   → 파일명에 인덱스 자동 포함 (product_000.jpg, product_001.jpg, ...)

4️⃣ Extract와 Save 연결:
   - Normalizer: Dict → NormalizedItem (타입 + 메타데이터)
   - PostProcessor: NormalizedItem → File (메타데이터 기반)
   → 두 단계의 책임 명확히 분리
""")

# ========================================
# Step 5: PostProcessor 시뮬레이션 (파일 저장 없이)
# ========================================
print("\n[Step 5] PostProcessor 시뮬레이션")
print("-" * 70)

print("📁 저장될 파일 경로 예상:")
for item in normalized_items:
    if item.metadata.get("directory") and item.metadata.get("name"):
        file_path = Path(item.metadata["directory"]) / item.metadata["name"]
        print(f"  • {file_path}")

# ========================================
# Step 6: Auto 모드 테스트
# ========================================
print("\n[Step 6] Auto 모드 테스트 (source=None)")
print("-" * 70)

# Auto 모드 규칙
auto_rule = NormalizationRule(
    kind="image",
    source=None,  # Auto 모드
    auto_infer=True,
    directory="m:/CALife/CAShop - 구매대행/_code/output/test/auto",
    name="auto_{{_index:03d}}",  # 확장자 자동 추론
    explode=True,
    ops={"overwrite": True, "create_parents": True}
)

# Auto 모드용 데이터 (record 전체를 value로 사용)
auto_data = [
    {"value": "https://example.com/auto1.jpg"},
    {"value": "https://example.com/auto2.png"},
    {"value": "텍스트 데이터"}
]

auto_normalizer = ItemNormalizer(rules=[auto_rule])
auto_items = auto_normalizer.normalize(auto_data)

print(f"✅ Auto 모드 결과:")
print(f"  - Input records: {len(auto_data)}")
print(f"  - Output items: {len(auto_items)}")
for idx, item in enumerate(auto_items, 1):
    print(f"  [{idx}] kind={item.kind}, extension={item.extension}")

# ========================================
# Step 7: 대안 검토
# ========================================
print("\n[Step 7] 대안 검토: NormalizedItem 없이 가능한가?")
print("-" * 70)

print("""
❌ 대안 1: Dict로 전달
   - 타입 안정성 없음 (Pydantic 검증 불가)
   - IDE 자동완성 불가
   - 런타임 에러 가능성

❌ 대안 2: Normalizer가 직접 저장
   - SRP 위반 (정규화 + 저장 = 2가지 책임)
   - 테스트 어려움
   - 유연성 감소

❌ 대안 3: 저장 정책을 별도 인자로 전달
   - 인자 폭발 (parameter explosion)
   - 순서 불일치 가능성

✅ NormalizedItem 사용:
   - 타입 안정성 (dataclass with type hints)
   - 단일 책임 (Normalizer: 변환, PostProcessor: 저장)
   - 메타데이터 전달 (저장 정책을 Item에 포함)
""")

# ========================================
# 결론
# ========================================
print("\n" + "=" * 70)
print("결론")
print("=" * 70)

print("""
✅ NormalizedItem은 필수적인 중간 데이터 모델입니다.

1. 타입 추론: kind로 image/text/file 구분
2. 메타데이터: directory, name, ops 전달
3. 인덱싱: record_index, item_index로 순서 보장
4. 책임 분리: Normalizer(변환) ↔ PostProcessor(저장)

✅ YAML 없이 크롤링 가능:
- Policy를 코드로 직접 생성
- Preset은 선택사항 (편의성)
- ConfigLoader는 YAML 관리 도구일 뿐

✅ 현재 dataclass 유지:
- 성능 우선 (대량 Item 생성)
- slots=True (메모리 최적화)
- 향후 __post_init__, to_dict() 추가 고려
""")

print("\n✅ 모든 테스트 완료 (WebDriver 불필요)")
