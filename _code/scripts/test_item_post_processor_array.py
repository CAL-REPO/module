# -*- coding: utf-8 -*-
"""ItemPostProcessor 배열 KeyPath 처리 테스트"""

import sys
from pathlib import Path

# 직접 import를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from crawl_utils.services.Item_Post_Processor import ItemPostProcessor
from crawl_utils.core.policy import ItemPostProcessPolicy
from fso_utils.core.policy import FSONamePolicy


def create_name_policy(name: str, extension: str) -> FSONamePolicy:
    """간단한 FSONamePolicy 생성 헬퍼"""
    return FSONamePolicy(
        as_type="file",
        name=name,
        extension=extension,
        delimiter="_",
        tail_mode=None,
        date_format="%Y-%m-%d",
        counter_width=3,
        auto_expand=True,
        sanitize=True,
        case="keep",
        ensure_unique=True
    )


def test_simple_array():
    """단순 배열 경로 테스트"""
    print("\n" + "="*60)
    print("1. 단순 배열 경로 테스트 (product__images)")
    print("="*60)
    
    # 규칙 정의
    rules = [
        ItemPostProcessPolicy(
            kind="image",
            source="product__images",
            directory=Path("output/test"),
            name=create_name_policy("image", ".jpg")
        )
    ]
    
    # 테스트 데이터
    extracted_data = [
        {
            "product": {
                "title": "상품1",
                "images": [
                    "https://example.com/img1.jpg",
                    "https://example.com/img2.jpg",
                    "https://example.com/img3.jpg"
                ]
            }
        }
    ]
    
    # 처리 실행
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(
        extracted_data=extracted_data,
        runtime_context={"cas_no": "CAPEA-001"},
        env_context={"output_dir": "output"}
    )
    
    print(f"\n추출된 ItemList 개수: {len(items)}")
    for i, item in enumerate(items, start=1):
        print(f"  [{i}] value={item.value}, index={item.item_index}")
    
    assert len(items) == 3, f"Expected 3 items, got {len(items)}"
    assert all(item.kind == "image" for item in items)
    print("\n✅ 단순 배열 경로 테스트 통과!")


def test_wildcard_path():
    """중간 경로 [*] 패턴 테스트"""
    print("\n" + "="*60)
    print("2. 중간 경로 [*] 패턴 테스트 (sku__options[*]__name)")
    print("="*60)
    
    # 규칙 정의
    rules = [
        ItemPostProcessPolicy(
            kind="text",
            source="sku__options[*]__name",
            directory=Path("output/test"),
            name=create_name_policy("option", ".txt")
        )
    ]
    
    # 테스트 데이터
    extracted_data = [
        {
            "sku": {
                "id": "SKU-001",
                "options": [
                    {"name": "Color", "value": "Red"},
                    {"name": "Size", "value": "M"},
                    {"name": "Material", "value": "Cotton"}
                ]
            }
        }
    ]
    
    # 처리 실행
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(
        extracted_data=extracted_data,
        runtime_context={"cas_no": "CAPEA-001"},
        env_context={"output_dir": "output"}
    )
    
    print(f"\n추출된 ItemList 개수: {len(items)}")
    for i, item in enumerate(items, start=1):
        print(f"  [{i}] value={item.value}, index={item.item_index}")
    
    assert len(items) == 3, f"Expected 3 items, got {len(items)}"
    assert items[0].value == "Color"
    assert items[1].value == "Size"
    assert items[2].value == "Material"
    print("\n✅ 중간 경로 [*] 패턴 테스트 통과!")


def test_nested_wildcard():
    """중첩 배열 [*] 패턴 테스트"""
    print("\n" + "="*60)
    print("3. 중첩 배열 [*] 패턴 테스트 (variants[*]__images[*])")
    print("="*60)
    
    # 규칙 정의
    rules = [
        ItemPostProcessPolicy(
            kind="image",
            source="variants[*]__images[*]",
            directory=Path("output/test"),
            name=create_name_policy("variant_image", ".jpg")
        )
    ]
    
    # 테스트 데이터
    extracted_data = [
        {
            "variants": [
                {
                    "color": "Red",
                    "images": [
                        "red_img1.jpg",
                        "red_img2.jpg"
                    ]
                },
                {
                    "color": "Blue",
                    "images": [
                        "blue_img1.jpg",
                        "blue_img2.jpg",
                        "blue_img3.jpg"
                    ]
                }
            ]
        }
    ]
    
    # 처리 실행
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(
        extracted_data=extracted_data,
        runtime_context={"cas_no": "CAPEA-001"},
        env_context={"output_dir": "output"}
    )
    
    print(f"\n추출된 ItemList 개수: {len(items)}")
    for i, item in enumerate(items, start=1):
        print(f"  [{i}] value={item.value}, index={item.item_index}")
    
    assert len(items) == 5, f"Expected 5 items (2+3), got {len(items)}"
    print("\n✅ 중첩 배열 [*] 패턴 테스트 통과!")


def test_specific_index():
    """특정 인덱스 접근 테스트"""
    print("\n" + "="*60)
    print("4. 특정 인덱스 접근 테스트 (items[0]__title)")
    print("="*60)
    
    # 규칙 정의
    rules = [
        ItemPostProcessPolicy(
            kind="text",
            source="items[0]__title",
            directory=Path("output/test"),
            name=create_name_policy("first_title", ".txt")
        )
    ]
    
    # 테스트 데이터
    extracted_data = [
        {
            "items": [
                {"title": "First Item", "price": 100},
                {"title": "Second Item", "price": 200}
            ]
        }
    ]
    
    # 처리 실행
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(
        extracted_data=extracted_data,
        runtime_context={"cas_no": "CAPEA-001"},
        env_context={"output_dir": "output"}
    )
    
    print(f"\n추출된 ItemList 개수: {len(items)}")
    for i, item in enumerate(items, start=1):
        print(f"  [{i}] value={item.value}, index={item.item_index}")
    
    assert len(items) == 1, f"Expected 1 item, got {len(items)}"
    assert items[0].value == "First Item"
    print("\n✅ 특정 인덱스 접근 테스트 통과!")


def test_multiple_records():
    """다중 레코드 처리 테스트"""
    print("\n" + "="*60)
    print("5. 다중 레코드 처리 테스트")
    print("="*60)
    
    # 규칙 정의
    rules = [
        ItemPostProcessPolicy(
            kind="image",
            source="product__images",
            directory=Path("output/test"),
            name=create_name_policy("image", ".jpg")
        )
    ]
    
    # 테스트 데이터 (2개 레코드)
    extracted_data = [
        {
            "product": {
                "title": "상품1",
                "images": ["img1.jpg", "img2.jpg"]
            }
        },
        {
            "product": {
                "title": "상품2",
                "images": ["img3.jpg"]
            }
        }
    ]
    
    # 처리 실행
    processor = ItemPostProcessor(rules=rules)
    items = processor.process(
        extracted_data=extracted_data,
        runtime_context={"cas_no": "CAPEA-001"},
        env_context={"output_dir": "output"}
    )
    
    print(f"\n추출된 ItemList 개수: {len(items)}")
    for i, item in enumerate(items, start=1):
        print(f"  [{i}] record={item.record_index}, item={item.item_index}, value={item.value}")
    
    assert len(items) == 3, f"Expected 3 items (2+1), got {len(items)}"
    assert items[0].record_index == 1
    assert items[1].record_index == 1
    assert items[2].record_index == 2
    print("\n✅ 다중 레코드 처리 테스트 통과!")


if __name__ == "__main__":
    test_simple_array()
    test_wildcard_path()
    test_nested_wildcard()
    test_specific_index()
    test_multiple_records()
    
    print("\n" + "="*60)
    print("✅ 모든 ItemPostProcessor 배열 KeyPath 테스트 통과!")
    print("="*60)
