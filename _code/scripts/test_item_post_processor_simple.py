# -*- coding: utf-8 -*-
"""ItemPostProcessor 배열 KeyPath 처리 테스트 (간소화 버전)"""

import sys
from pathlib import Path

# PYTHONPATH 설정
modules_path = Path(__file__).parent.parent / "modules"
sys.path.insert(0, str(modules_path))

# 직접 import하여 crawl_utils __init__ 우회
import importlib.util

# ItemPostProcessor 직접 로드
spec = importlib.util.spec_from_file_location(
    "Item_Post_Processor",
    modules_path / "crawl_utils" / "services" / "Item_Post_Processor.py"
)
item_post_processor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(item_post_processor_module)
ItemPostProcessor = item_post_processor_module.ItemPostProcessor

# Policy 직접 로드
spec_policy = importlib.util.spec_from_file_location(
    "policy",
    modules_path / "crawl_utils" / "core" / "policy.py"
)
policy_module = importlib.util.module_from_spec(spec_policy)
spec_policy.loader.exec_module(policy_module)
ItemPostProcessPolicy = policy_module.ItemPostProcessPolicy


def test_simple_array_explode():
    """Case 1: 단순 배열 explode (source가 배열을 직접 가리킴)"""
    print("\n" + "="*60)
    print("TEST 1: 단순 배열 explode")
    print("="*60)
    
    # 추출된 데이터
    extracted_data = [
        {
            "product": {
                "title": "Test Product",
                "images": [
                    "https://example.com/img1.jpg",
                    "https://example.com/img2.jpg",
                    "https://example.com/img3.jpg"
                ]
            }
        }
    ]
    
    # 규칙 정의 (최소 파라미터)
    rules = [
        ItemPostProcessPolicy(
            kind="image",
            source="product__images",  # 배열 경로
            directory=Path("output/images")
        )
    ]
    
    # ItemPostProcessor 실행
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(extracted_data)
    
    # 검증
    print(f"\n✅ 생성된 ItemList 개수: {len(items)}")
    assert len(items) == 3, f"Expected 3 items, got {len(items)}"
    
    for i, item in enumerate(items, start=1):
        print(f"\nItemList #{i}:")
        print(f"  kind: {item.kind}")
        print(f"  value: {item.value}")
        print(f"  record_index: {item.record_index}")
        print(f"  item_index: {item.item_index}")
        
        assert item.kind == "image"
        assert item.value == extracted_data[0]["product"]["images"][i-1]
        assert item.record_index == 1
        assert item.item_index == i
    
    print("\n✅ TEST 1 PASSED!")


def test_wildcard_keypath():
    """Case 2: 중간 경로에 [*] 있는 경우"""
    print("\n" + "="*60)
    print("TEST 2: Wildcard KeyPath (중간 경로 [*])")
    print("="*60)
    
    # 추출된 데이터
    extracted_data = [
        {
            "sku": {
                "options": [
                    {"name": "Red", "value": "color-red"},
                    {"name": "Blue", "value": "color-blue"},
                    {"name": "Green", "value": "color-green"}
                ]
            }
        }
    ]
    
    # 규칙 정의
    rules = [
        ItemPostProcessPolicy(
            kind="text",
            source="sku__options[*]__name",  # 중간 경로에 [*]
            directory=Path("output/sku")
        )
    ]
    
    # ItemPostProcessor 실행
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(extracted_data)
    
    # 검증
    print(f"\n✅ 생성된 ItemList 개수: {len(items)}")
    assert len(items) == 3, f"Expected 3 items, got {len(items)}"
    
    expected_names = ["Red", "Blue", "Green"]
    for i, item in enumerate(items, start=1):
        print(f"\nItemList #{i}:")
        print(f"  kind: {item.kind}")
        print(f"  value: {item.value}")
        print(f"  record_index: {item.record_index}")
        print(f"  item_index: {item.item_index}")
        
        assert item.kind == "text"
        assert item.value == expected_names[i-1]
        assert item.record_index == 1
        assert item.item_index == i
    
    print("\n✅ TEST 2 PASSED!")


def test_nested_wildcard():
    """Case 3: 중첩된 [*] 패턴"""
    print("\n" + "="*60)
    print("TEST 3: 중첩 Wildcard KeyPath")
    print("="*60)
    
    # 추출된 데이터
    extracted_data = [
        {
            "variants": [
                {
                    "color": "Red",
                    "images": ["red1.jpg", "red2.jpg"]
                },
                {
                    "color": "Blue",
                    "images": ["blue1.jpg", "blue2.jpg", "blue3.jpg"]
                }
            ]
        }
    ]
    
    # 규칙 정의
    rules = [
        ItemPostProcessPolicy(
            kind="image",
            source="variants[*]__images[*]",  # 중첩 [*]
            directory=Path("output/variants")
        )
    ]
    
    # ItemPostProcessor 실행
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(extracted_data)
    
    # 검증
    print(f"\n✅ 생성된 ItemList 개수: {len(items)}")
    assert len(items) == 5, f"Expected 5 items (2+3), got {len(items)}"
    
    expected_values = ["red1.jpg", "red2.jpg", "blue1.jpg", "blue2.jpg", "blue3.jpg"]
    for i, item in enumerate(items, start=1):
        print(f"\nItemList #{i}:")
        print(f"  kind: {item.kind}")
        print(f"  value: {item.value}")
        
        assert item.kind == "image"
        assert item.value == expected_values[i-1]
    
    print("\n✅ TEST 3 PASSED!")


def test_specific_index():
    """Case 4: 특정 인덱스 접근 [0], [1]"""
    print("\n" + "="*60)
    print("TEST 4: 특정 인덱스 접근")
    print("="*60)
    
    # 추출된 데이터
    extracted_data = [
        {
            "items": [
                {"title": "First Item", "price": 100},
                {"title": "Second Item", "price": 200}
            ]
        }
    ]
    
    # 규칙 정의
    rules = [
        ItemPostProcessPolicy(
            kind="text",
            source="items[0]__title",  # 첫 번째 아이템만
            directory=Path("output/items")
        )
    ]
    
    # ItemPostProcessor 실행
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(extracted_data)
    
    # 검증
    print(f"\n✅ 생성된 ItemList 개수: {len(items)}")
    assert len(items) == 1, f"Expected 1 item, got {len(items)}"
    
    print(f"\nItemList #1:")
    print(f"  kind: {items[0].kind}")
    print(f"  value: {items[0].value}")
    
    assert items[0].kind == "text"
    assert items[0].value == "First Item"
    
    print("\n✅ TEST 4 PASSED!")


def test_multiple_records():
    """Case 5: 여러 record 처리"""
    print("\n" + "="*60)
    print("TEST 5: 여러 record 처리")
    print("="*60)
    
    # 추출된 데이터 (2개 record)
    extracted_data = [
        {
            "product": {
                "images": ["url1.jpg", "url2.jpg"]
            }
        },
        {
            "product": {
                "images": ["url3.jpg"]
            }
        }
    ]
    
    # 규칙 정의
    rules = [
        ItemPostProcessPolicy(
            kind="image",
            source="product__images",
            directory=Path("output/images")
        )
    ]
    
    # ItemPostProcessor 실행
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(extracted_data)
    
    # 검증
    print(f"\n✅ 생성된 ItemList 개수: {len(items)}")
    assert len(items) == 3, f"Expected 3 items, got {len(items)}"
    
    print(f"\nRecord 1의 items:")
    print(f"  [{items[0].record_index}:{items[0].item_index}] {items[0].value}")
    print(f"  [{items[1].record_index}:{items[1].item_index}] {items[1].value}")
    
    print(f"\nRecord 2의 items:")
    print(f"  [{items[2].record_index}:{items[2].item_index}] {items[2].value}")
    
    # Record 1의 items
    assert items[0].record_index == 1
    assert items[0].item_index == 1
    assert items[0].value == "url1.jpg"
    
    assert items[1].record_index == 1
    assert items[1].item_index == 2
    assert items[1].value == "url2.jpg"
    
    # Record 2의 item
    assert items[2].record_index == 2
    assert items[2].item_index == 1
    assert items[2].value == "url3.jpg"
    
    print("\n✅ TEST 5 PASSED!")


if __name__ == "__main__":
    try:
        test_simple_array_explode()
        test_wildcard_keypath()
        test_nested_wildcard()
        test_specific_index()
        test_multiple_records()
        
        print("\n" + "="*60)
        print("🎉 모든 테스트 통과!")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        raise
