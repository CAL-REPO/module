# -*- coding: utf-8 -*-
"""ItemPostProcessor 배열 KeyPath 처리 단위 테스트"""

# 이 파일은 crawl_utils/services/ 디렉토리에서 직접 실행됩니다
# python -m pytest test_item_post_processor_arrays.py

from pathlib import Path
from typing import List, Dict, Any

# 상대 import (같은 디렉토리)
from Item_Post_Processor import ItemPostProcessor

# 상위 디렉토리에서 import
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from crawl_utils.core.policy import ItemPostProcessPolicy


def test_simple_array_explode():
    """테스트 1: 단순 배열 explode"""
    print("\n" + "="*60)
    print("TEST 1: 단순 배열 explode (product__images)")
    print("="*60)
    
    extracted_data = [{
        "product": {
            "images": ["url1.jpg", "url2.jpg", "url3.jpg"]
        }
    }]
    
    rules = [
        ItemPostProcessPolicy(
            kind="image",
            source="product__images",
            directory=Path("output/test")
        )
    ]
    
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(extracted_data)
    
    print(f"\n생성된 ItemList: {len(items)}개")
    for i, item in enumerate(items, 1):
        print(f"  [{i}] kind={item.kind}, value={item.value}, index={item.item_index}")
    
    assert len(items) == 3
    assert all(item.kind == "image" for item in items)
    assert items[0].item_index == 1
    assert items[1].item_index == 2
    assert items[2].item_index == 3
    
    print("✅ TEST 1 PASSED!\n")


def test_wildcard_keypath():
    """테스트 2: 중간 경로 [*] 패턴"""
    print("\n" + "="*60)
    print("TEST 2: Wildcard KeyPath (sku__options[*]__name)")
    print("="*60)
    
    extracted_data = [{
        "sku": {
            "options": [
                {"name": "Red", "value": "color-red"},
                {"name": "Blue", "value": "color-blue"},
                {"name": "Green", "value": "color-green"}
            ]
        }
    }]
    
    rules = [
        ItemPostProcessPolicy(
            kind="text",
            source="sku__options[*]__name",
            directory=Path("output/test")
        )
    ]
    
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(extracted_data)
    
    print(f"\n생성된 ItemList: {len(items)}개")
    for i, item in enumerate(items, 1):
        print(f"  [{i}] kind={item.kind}, value={item.value}")
    
    assert len(items) == 3
    assert items[0].value == "Red"
    assert items[1].value == "Blue"
    assert items[2].value == "Green"
    
    print("✅ TEST 2 PASSED!\n")


def test_nested_wildcard():
    """테스트 3: 중첩 [*] 패턴"""
    print("\n" + "="*60)
    print("TEST 3: 중첩 Wildcard (variants[*]__images[*])")
    print("="*60)
    
    extracted_data = [{
        "variants": [
            {"color": "Red", "images": ["red1.jpg", "red2.jpg"]},
            {"color": "Blue", "images": ["blue1.jpg", "blue2.jpg", "blue3.jpg"]}
        ]
    }]
    
    rules = [
        ItemPostProcessPolicy(
            kind="image",
            source="variants[*]__images[*]",
            directory=Path("output/test")
        )
    ]
    
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(extracted_data)
    
    print(f"\n생성된 ItemList: {len(items)}개")
    for i, item in enumerate(items, 1):
        print(f"  [{i}] value={item.value}")
    
    assert len(items) == 5  # 2 + 3
    assert items[0].value == "red1.jpg"
    assert items[1].value == "red2.jpg"
    assert items[2].value == "blue1.jpg"
    
    print("✅ TEST 3 PASSED!\n")


def test_specific_index():
    """테스트 4: 특정 인덱스 [0]"""
    print("\n" + "="*60)
    print("TEST 4: 특정 인덱스 (items[0]__title)")
    print("="*60)
    
    extracted_data = [{
        "items": [
            {"title": "First", "price": 100},
            {"title": "Second", "price": 200}
        ]
    }]
    
    rules = [
        ItemPostProcessPolicy(
            kind="text",
            source="items[0]__title",
            directory=Path("output/test")
        )
    ]
    
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(extracted_data)
    
    print(f"\n생성된 ItemList: {len(items)}개")
    print(f"  value={items[0].value}")
    
    assert len(items) == 1
    assert items[0].value == "First"
    
    print("✅ TEST 4 PASSED!\n")


def test_multiple_records():
    """테스트 5: 다중 record"""
    print("\n" + "="*60)
    print("TEST 5: 다중 record 처리")
    print("="*60)
    
    extracted_data = [
        {"product": {"images": ["url1.jpg", "url2.jpg"]}},
        {"product": {"images": ["url3.jpg"]}}
    ]
    
    rules = [
        ItemPostProcessPolicy(
            kind="image",
            source="product__images",
            directory=Path("output/test")
        )
    ]
    
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(extracted_data)
    
    print(f"\n생성된 ItemList: {len(items)}개")
    for item in items:
        print(f"  record={item.record_index}, item={item.item_index}, value={item.value}")
    
    assert len(items) == 3
    assert items[0].record_index == 1
    assert items[1].record_index == 1
    assert items[2].record_index == 2
    
    print("✅ TEST 5 PASSED!\n")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("ItemPostProcessor 배열 KeyPath 처리 테스트")
    print("="*60)
    
    try:
        test_simple_array_explode()
        test_wildcard_keypath()
        test_nested_wildcard()
        test_specific_index()
        test_multiple_records()
        
        print("\n" + "="*60)
        print("🎉 모든 테스트 통과!")
        print("="*60)
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        raise
