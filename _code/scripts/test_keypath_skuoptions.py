# -*- coding: utf-8 -*-
"""
KeyPath 추출 테스트 - skuOptions__url 확인
"""

import sys
sys.path.insert(0, r"m:\CALife\CAShop - 구매대행\_code\modules")

from keypath_utils.core.accessor import KeyPathAccessor

# Mock Data
data = {
    "images": [
        "https://ae01.alicdn.com/kf/IMAGE_1.png",
        "https://ae01.alicdn.com/kf/IMAGE_2.png"
    ],
    "skuOptions": [
        {"url": "https://ae01.alicdn.com/kf/SKU_OPTION_1.png", "title": "Red"},
        {"url": "https://ae01.alicdn.com/kf/SKU_OPTION_2.png", "title": "Blue"},
        {"url": "https://ae01.alicdn.com/kf/SKU_OPTION_3.png", "title": "Green"}
    ]
}

print("=" * 80)
print("KeyPath 추출 테스트")
print("=" * 80)

accessor = KeyPathAccessor(data)

# Test 1: images (배열)
print("\n[Test 1] KeyPath: images")
result = accessor.get("images")
print(f"  Result Type: {type(result)}")
print(f"  Result: {result}")

# Test 2: skuOptions (배열)
print("\n[Test 2] KeyPath: skuOptions")
result = accessor.get("skuOptions")
print(f"  Result Type: {type(result)}")
print(f"  Result: {result}")

# Test 3: skuOptions__url (배열 내 객체의 필드)
print("\n[Test 3] KeyPath: skuOptions__url")
result = accessor.get("skuOptions__url")
print(f"  Result Type: {type(result)}")
print(f"  Result: {result}")

# Test 4: skuOptions[0]__url (특정 인덱스)
print("\n[Test 4] KeyPath: skuOptions[0]__url")
result = accessor.get("skuOptions[0]__url")
print(f"  Result Type: {type(result)}")
print(f"  Result: {result}")

# Test 5: skuOptions[*]__url (와일드카드)
print("\n[Test 5] KeyPath: skuOptions[*]__url")
try:
    result = accessor.get("skuOptions[*]__url")
    print(f"  Result Type: {type(result)}")
    print(f"  Result: {result}")
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 80)
print("결론:")
print("=" * 80)
print("""
KeyPathAccessor는:
1. "images" → [url1, url2] (배열 전체 반환)
2. "skuOptions" → [{...}, {...}] (배열 전체 반환)
3. "skuOptions__url" → ??? (어떻게 처리?)
   - 옵션 A: None (배열 내 객체는 자동 순회 안함)
   - 옵션 B: [url1, url2, url3] (자동 순회)
4. "skuOptions[*]__url" → [url1, url2, url3] (명시적 와일드카드)

⚠️  만약 3번이 None을 반환하면:
   → ItemPostProcessor._process_rule()이 빈 리스트 반환
   → skuOptions__url이 완전히 무시됨
""")
