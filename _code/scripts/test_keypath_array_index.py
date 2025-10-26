# -*- coding: utf-8 -*-
"""KeyPath 배열 인덱스 기능 테스트"""

from keypath_utils import KeyPathAccessor, KeyPathNormalizer
from keypath_utils.core.policy import KeyPathNormalizePolicy


def test_normalizer_array_index():
    """KeyPathNormalizer 배열 인덱스 파싱 테스트"""
    print("\n" + "="*60)
    print("1. KeyPathNormalizer 배열 인덱스 파싱 테스트")
    print("="*60)
    
    policy = KeyPathNormalizePolicy(sep="__", enable_list_index=True)
    normalizer = KeyPathNormalizer(policy)
    
    test_cases = [
        ("sku__options[*]__name", ["sku", "options", "[*]", "name"]),
        ("items[0]__title", ["items", "[0]", "title"]),
        ("data[1][2]", ["data", "[1]", "[2]"]),
        ("values[*]", ["values", "[*]"]),
        ("a__b__c", ["a", "b", "c"]),
    ]
    
    for path, expected in test_cases:
        result = normalizer.apply(path)
        status = "✅" if result == expected else "❌"
        print(f"{status} {path:30s} → {result}")
        if result != expected:
            print(f"   Expected: {expected}")


def test_accessor_array_get():
    """KeyPathAccessor 배열 접근 테스트 (GET)"""
    print("\n" + "="*60)
    print("2. KeyPathAccessor 배열 접근 테스트 (GET)")
    print("="*60)
    
    # 테스트 데이터
    data = {
        "product": {
            "sku": "ABC-123",
            "options": [
                {"name": "Color", "value": "Red"},
                {"name": "Size", "value": "M"},
                {"name": "Material", "value": "Cotton"}
            ]
        },
        "items": [
            {"title": "Item A", "price": 100},
            {"title": "Item B", "price": 200}
        ]
    }
    
    # KeyPathNormalizer 설정 (enable_list_index=True)
    policy = KeyPathNormalizePolicy(sep="__", enable_list_index=True)
    
    # KeyPathAccessor는 내부적으로 normalizer 생성하므로
    # policy를 전달할 방법이 필요... 일단 직접 테스트
    accessor = KeyPathAccessor(data)
    
    # Normalizer를 교체 (임시 방법)
    accessor._normalizer = KeyPathNormalizer(policy)
    
    test_cases = [
        ("product__options__[0]__name", "Color"),
        ("product__options__[1]__value", "M"),
        ("product__options__[2]__name", "Material"),
        ("items__[0]__title", "Item A"),
        ("items__[1]__price", 200),
        # [*] 패턴은 전체 배열 반환
        ("product__options__[*]", data["product"]["options"]),
        ("items__[*]", data["items"]),
    ]
    
    for path, expected in test_cases:
        result = accessor.get(path)
        status = "✅" if result == expected else "❌"
        print(f"{status} {path:40s} → {result}")
        if result != expected:
            print(f"   Expected: {expected}")


def test_accessor_array_set():
    """KeyPathAccessor 배열 설정 테스트 (SET)"""
    print("\n" + "="*60)
    print("3. KeyPathAccessor 배열 설정 테스트 (SET)")
    print("="*60)
    
    data = {}
    policy = KeyPathNormalizePolicy(sep="__", enable_list_index=True)
    accessor = KeyPathAccessor(data)
    accessor._normalizer = KeyPathNormalizer(policy)
    
    # 배열 생성 및 값 설정
    test_cases = [
        ("items__[0]__name", "First Item"),
        ("items__[1]__name", "Second Item"),
        ("items__[0]__price", 100),
        ("nested__data__[0]__[1]", "Value"),
    ]
    
    for path, value in test_cases:
        try:
            accessor.set(path, value)
            result = accessor.get(path)
            status = "✅" if result == value else "❌"
            print(f"{status} SET {path:35s} = {value}")
        except Exception as e:
            print(f"❌ SET {path:35s} → ERROR: {e}")
    
    print("\n최종 데이터 구조:")
    import json
    print(json.dumps(data, indent=2, ensure_ascii=False))


def test_wildcard_in_middle():
    """중간 경로에 [*] 사용 테스트"""
    print("\n" + "="*60)
    print("4. 중간 경로 [*] 패턴 테스트")
    print("="*60)
    
    data = {
        "products": [
            {
                "options": [
                    {"name": "Color", "values": ["Red", "Blue"]},
                    {"name": "Size", "values": ["S", "M", "L"]}
                ]
            },
            {
                "options": [
                    {"name": "Material", "values": ["Cotton", "Polyester"]}
                ]
            }
        ]
    }
    
    policy = KeyPathNormalizePolicy(sep="__", enable_list_index=True)
    accessor = KeyPathAccessor(data)
    accessor._normalizer = KeyPathNormalizer(policy)
    
    # 첫 번째 제품의 모든 옵션 이름 추출 (수동)
    print("\n첫 번째 제품의 옵션들:")
    options = accessor.get("products__[0]__options__[*]")
    print(f"  options = {options}")
    
    for i, opt in enumerate(options):
        name = accessor.get(f"products__[0]__options__[{i}]__name")
        print(f"  [{i}] name = {name}")
    
    print("\n💡 참고: [*]는 현재 단계에서만 동작하며,")
    print("   중간 경로 [*] 처리는 ItemPostProcessor에서 구현 예정")


if __name__ == "__main__":
    test_normalizer_array_index()
    test_accessor_array_get()
    test_accessor_array_set()
    test_wildcard_in_middle()
    
    print("\n" + "="*60)
    print("✅ KeyPath 배열 인덱스 테스트 완료!")
    print("="*60)
