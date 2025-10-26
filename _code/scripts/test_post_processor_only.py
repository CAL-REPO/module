# -*- coding: utf-8 -*-
"""
후단 테스트 (WebDriver 없이)
=============================

Extract 결과를 직접 생성하여 ItemPostProcessor → ItemSaver 테스트

목적:
1. skuOptions가 정상적으로 처리되는지 확인
2. ItemNormalizer의 KeyPath 추출 확인
3. ItemSaver의 저장 로직 확인
"""

import sys
from pathlib import Path

sys.path.insert(0, r"m:\CALife\CAShop - 구매대행\_code\modules")

# ========================================
# Mock Extract 결과 (AliExpress Detail)
# ========================================
extracted_data = [
    {
        "images": [
            "https://ae01.alicdn.com/kf/S98a18bcd33c34d28a0e5276b0aa20f48e/64x64.png",
            "https://ae01.alicdn.com/kf/S5efe9a37755e44cfa878e2e714900709h/48x48.png",
            "https://ae01.alicdn.com/kf/Sca75952228bb4507ac311d1b43e10721q/48x48.png"
        ],
        "skuOptions": [
            {
                "url": "https://ae01.alicdn.com/kf/SKU_OPTION_1.png",
                "title": "Red"
            },
            {
                "url": "https://ae01.alicdn.com/kf/SKU_OPTION_2.png",
                "title": "Blue"
            },
            {
                "url": "https://ae01.alicdn.com/kf/SKU_OPTION_3.png",
                "title": "Green"
            }
        ],
        "imageDebug": {
            "hasShadowRoot": False,
            "globalImgsCount": 281
        }
    }
]

print("=" * 80)
print("후단 테스트 (WebDriver 없이)")
print("=" * 80)
print(f"\n📦 Mock Data:")
print(f"  - images: {len(extracted_data[0]['images'])} items")
print(f"  - skuOptions: {len(extracted_data[0]['skuOptions'])} items")

# ========================================
# Step 1: Preset 로드
# ========================================
from crawl_utils.presets import get_preset

preset = get_preset("aliexpress", "detail")
save_rules = preset.get("save", [])

print(f"\n📋 Preset Save Rules: {len(save_rules)}")
for idx, rule in enumerate(save_rules, 1):
    print(f"  {idx}. kind={rule['kind']}, source={rule['source']}, directory={rule.get('directory', 'None')}")

# ========================================
# Step 2: ItemPostProcessPolicy 생성
# ========================================
from crawl_utils.core.policy import ItemPostProcessPolicy

policies = []
for rule in save_rules:
    policy = ItemPostProcessPolicy(**rule)
    policies.append(policy)
    print(f"\n✅ Policy Created: {policy.kind} - {policy.source}")
    print(f"   directory: {policy.directory}")

# ========================================
# Step 3: ItemPostProcessor로 변환
# ========================================
from crawl_utils.services.Item_Post_Processor import ItemPostProcessor

processor = ItemPostProcessor(rules=policies)
normalized_items = processor.process(extracted_data)

print(f"\n🔄 ItemPostProcessor 결과:")
print(f"  - Total items: {len(normalized_items)}")

# kind별 분류
from collections import defaultdict
by_kind = defaultdict(list)
for item in normalized_items:
    by_kind[item.kind].append(item)

for kind, items in by_kind.items():
    print(f"  - {kind}: {len(items)} items")
    for idx, item in enumerate(items[:3], 1):  # 처음 3개만
        print(f"      {idx}. directory={item.directory}, value={str(item.value)[:80]}...")

# ========================================
# Step 4: ItemSaver로 저장
# ========================================
from crawl_utils.services.Item_Saver import SyncItemSaver

saver = SyncItemSaver()
summary = saver.save_items(normalized_items)

print(f"\n💾 ItemSaver 저장 결과:")
print(f"  - image: {len(summary.artifacts.get('image', []))} files")
print(f"  - text: {len(summary.artifacts.get('text', []))} files")
print(f"  - file: {len(summary.artifacts.get('file', []))} files")

# 저장 성공/실패 확인
all_results = summary.flatten()
saved = [r for r in all_results if r.status == "saved"]
failed = [r for r in all_results if r.status == "failed"]
skipped = [r for r in all_results if r.status == "skipped"]

print(f"\n📊 저장 상태:")
print(f"  ✅ Saved: {len(saved)}")
print(f"  ❌ Failed: {len(failed)}")
print(f"  ⏭️  Skipped: {len(skipped)}")

if saved:
    print(f"\n✅ 저장된 파일 (처음 5개):")
    for result in saved[:5]:
        print(f"  • {result.path.name} ({result.path.stat().st_size} bytes)")

if failed:
    print(f"\n❌ 실패한 파일:")
    for result in failed:
        print(f"  • {result.detail}")

if skipped:
    print(f"\n⏭️  스킵된 파일:")
    for result in skipped:
        print(f"  • {result.detail}")

# ========================================
# Step 5: 실제 파일 확인
# ========================================
print(f"\n🔍 Downloads 폴더 확인:")
from path_utils import downloads

downloads_dir = downloads()
print(f"  Path: {downloads_dir}")

detailed_files = list(downloads_dir.glob("DETAILED_TEST_*.png"))
option_files = list(downloads_dir.glob("OPTION_TEST_*.png"))

print(f"  - DETAILED_TEST_*.png: {len(detailed_files)} files")
print(f"  - OPTION_TEST_*.png: {len(option_files)} files")

if option_files:
    print(f"\n✅ OPTION 파일 발견:")
    for f in option_files[:5]:
        print(f"  • {f.name} ({f.stat().st_size} bytes)")
else:
    print(f"\n⚠️  OPTION 파일이 없습니다!")
    print(f"   → skuOptions__url KeyPath가 제대로 추출되지 않았을 가능성")

print("\n" + "=" * 80)
print("결론:")
print("=" * 80)
print("""
1. Mock Data로 Extract 결과 생성 ✅
2. Preset 로드 및 Policy 생성 ✅
3. ItemPostProcessor 실행 (KeyPath 추출) → 확인 필요
4. ItemSaver 실행 (파일 저장) → 확인 필요
5. 실제 파일 확인 → OPTION 파일 존재 여부 확인

⚠️  skuOptions__url이 정상 추출되지 않으면:
   - ItemPostProcessor의 KeyPath 추출 로직 확인
   - skuOptions 배열 내 url 필드 접근 확인
""")
