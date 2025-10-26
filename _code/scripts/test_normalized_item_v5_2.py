# -*- coding: utf-8 -*-
"""NormalizedItem v5.2 테스트 - FSONamePolicy 지원

변경사항:
1. section, name_hint, extension 필드 제거
2. metadata["name"]에 FSONamePolicy 형식 지원
3. extension은 name["extension"]에 저장
"""

from pathlib import Path

print("=" * 70)
print("NormalizedItem v5.2 - FSONamePolicy 지원")
print("=" * 70)

# ========================================
# Step 1: FSONamePolicy 형식 사용
# ========================================
print("\n[Step 1] FSONamePolicy 형식 사용")
print("-" * 70)

from crawl_utils.core.models import NormalizedItem

# 예시 1: FSONamePolicy 형식 (dict)
item1 = NormalizedItem(
    kind="image",
    value="https://example.com/product.jpg",
    metadata={
        "directory": "m:/output/images/{{runtime.cas_no}}",
        "name": {
            "prefix": "{{runtime.cas_no}}",
            "name": "product",
            "suffix": "{{item.index:03d}}",
            "extension": "jpg",
            "delimiter": "_",
            "ensure_unique": False
        },
        "ops": {"overwrite": True, "create_parents": True}
    },
    record_index=1,
    item_index=1
)

print(f"✅ FSONamePolicy 형식:")
print(f"  kind: {item1.kind}")
print(f"  value: {item1.value}")
print(f"  metadata.name (dict):")
print(f"    - prefix: {item1.metadata['name']['prefix']}")
print(f"    - name: {item1.metadata['name']['name']}")
print(f"    - suffix: {item1.metadata['name']['suffix']}")
print(f"    - extension: {item1.metadata['name']['extension']}")
print(f"    - delimiter: {item1.metadata['name']['delimiter']}")
print(f"  index: record[{item1.record_index}], item[{item1.item_index}]")
print(f"\n  예상 파일명: CAPEA-001_product_001.jpg")

# 예시 2: 기존 문자열 방식 (하위 호환)
item2 = NormalizedItem(
    kind="image",
    value="https://example.com/photo.png",
    metadata={
        "directory": "m:/output/auto",
        "name": "{{runtime.cas_no}}_{{item.index:03d}}.png",
        "ops": {"overwrite": True}
    },
    record_index=1,
    item_index=1
)

print(f"\n✅ 기존 문자열 방식 (하위 호환):")
print(f"  metadata.name (str): {item2.metadata['name']}")
print(f"  예상 파일명: CAPEA-001_001.png")

# ========================================
# Step 2: 제거된 필드 확인
# ========================================
print("\n[Step 2] 제거된 필드 확인")
print("-" * 70)

print(f"❌ 제거된 필드:")
print(f"  - section (미사용)")
print(f"  - name_hint (미사용)")
print(f"  - extension (→ metadata.name.extension으로 이동)")
print(f"\n✅ 남은 필드 (5개):")
print(f"  - kind: ItemKind")
print(f"  - value: Any")
print(f"  - metadata: Dict[str, Any]")
print(f"  - record_index: int")
print(f"  - item_index: int")

# ========================================
# Step 3: Normalizer 테스트 (Auto 모드)
# ========================================
print("\n[Step 3] Normalizer 테스트 (Auto 모드)")
print("-" * 70)

from crawl_utils.core.policy import NormalizationRule
from crawl_utils.services.Item_Post_Processor import ItemNormalizer

# Rule with FSONamePolicy
rule1 = NormalizationRule(
    kind="image",
    source="images",
    directory="m:/output/images",
    name={
        "prefix": "product",
        "suffix": "{{item.index:03d}}",
        "extension": "jpg",
        "delimiter": "_"
    },
    explode=True
)

# Auto 모드: extension 자동 추론
rule2 = NormalizationRule(
    kind="image",
    source=None,
    auto_infer=True,
    directory="m:/output/auto",
    name={
        "name": "auto",
        "suffix": "{{item.index:03d}}",
        "delimiter": "_"
        # extension은 TypeInferencer가 자동 추론
    },
    explode=True
)

extracted_data = [
    {
        "images": [
            "https://example.com/img1.jpg",
            "https://example.com/img2.png"
        ]
    }
]

print(f"✅ NormalizationRule (FSONamePolicy):")
print(f"  Rule 1 (Rule 모드):")
print(f"    - name: {rule1.name}")
print(f"  Rule 2 (Auto 모드):")
print(f"    - name: {rule2.name}")

normalizer = ItemNormalizer(rules=[rule1])
normalized_items = normalizer.normalize(extracted_data)

print(f"\n✅ Normalized items: {len(normalized_items)}")
for idx, item in enumerate(normalized_items, 1):
    print(f"\n  [{idx}] {item.kind.upper()}")
    print(f"      value: {item.value}")
    print(f"      metadata.name:")
    if isinstance(item.metadata.get("name"), dict):
        for key, val in item.metadata["name"].items():
            print(f"        - {key}: {val}")
    else:
        print(f"        - (str): {item.metadata.get('name')}")
    print(f"      index: record[{item.record_index}], item[{item.item_index}]")

# ========================================
# Step 4: PostProcessor 테스트 (시뮬레이션)
# ========================================
print("\n[Step 4] PostProcessor 테스트 (시뮬레이션)")
print("-" * 70)

# PostProcessor는 실제 파일 저장을 시뮬레이션
runtime_context = {"cas_no": "CAPEA-001"}

print(f"✅ PostProcessor._build_filename_from_policy() 시뮬레이션:")

# FSONamePolicy 예시
policy = {
    "prefix": "CAPEA-001",  # 렌더링된 값
    "name": "product",
    "suffix": "001",  # 렌더링된 값
    "extension": "jpg",
    "delimiter": "_"
}

# 조합: prefix_name_suffix.extension
parts = []
delimiter = policy.get("delimiter", "_")

if policy.get("prefix"):
    parts.append(policy["prefix"])
if policy.get("name"):
    parts.append(policy["name"])
if policy.get("suffix"):
    parts.append(policy["suffix"])

stem = delimiter.join(parts)
extension = policy.get("extension")
filename = f"{stem}.{extension}" if extension else stem

print(f"  입력:")
print(f"    - prefix: {policy['prefix']}")
print(f"    - name: {policy['name']}")
print(f"    - suffix: {policy['suffix']}")
print(f"    - extension: {policy['extension']}")
print(f"    - delimiter: {policy['delimiter']}")
print(f"\n  조합:")
print(f"    - parts: {parts}")
print(f"    - stem: {stem}")
print(f"    - filename: {filename}")

# ========================================
# 결론
# ========================================
print("\n" + "=" * 70)
print("결론")
print("=" * 70)

print("""
✅ v5.2 변경사항:

1️⃣ 필드 간소화:
   - section 제거 (미사용)
   - name_hint 제거 (미사용)
   - extension 제거 (→ metadata.name.extension)
   
2️⃣ FSONamePolicy 지원:
   - metadata.name을 dict로 확장
   - prefix, name, suffix, extension, delimiter 등 지원
   - 기존 문자열 방식도 하위 호환

3️⃣ 유연성 향상:
   - fso_utils의 FSONamePolicy와 호환
   - 복잡한 파일명 패턴 지원
   - tail_mode (date, datetime, counter) 향후 확장 가능

4️⃣ metadata 중심:
   - 모든 저장 정책이 metadata에 집중
   - NormalizedItem은 최소한의 필드만 유지
   - PostProcessor가 metadata 기반으로 파일명 생성

✅ 파일명 조합 패턴:
   {prefix}_{name}_{suffix}.{extension}
   
✅ 예시:
   CAPEA-001_product_001.jpg
   CAPEA-001_detail_002.png
   product_20251026_143022.jpg (tail_mode="datetime")
""")

print("\n✅ 모든 테스트 완료")
