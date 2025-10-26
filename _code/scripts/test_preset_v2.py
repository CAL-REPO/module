import sys
sys.path.insert(0, r"m:\CALife\CAShop - 구매대행\_code\modules")

from crawl_utils.presets import get_preset, list_presets

print("\n=== v2.0 Preset Test ===\n")

# 1. 사용 가능한 Preset 목록
presets = list_presets()
print(f"Available Presets: {presets}")

# 2. Aliexpress Detail Preset 로드
preset = get_preset("aliexpress", "detail")
print(f"\nAliexpress Detail Preset Keys: {list(preset.keys())}")
print(f"Save Rules Count: {len(preset['save'])}")
print(f"First Rule Source: {preset['save'][0]['source']}")
print(f"Third Rule Source: {preset['save'][2]['source']}")

# 3. Wildcard KeyPath 확인
for i, rule in enumerate(preset['save'], 1):
    print(f"Rule {i}: {rule['kind']} - {rule['source']}")

print("\n✅ v2.0 Preset 로드 SUCCESS!")
