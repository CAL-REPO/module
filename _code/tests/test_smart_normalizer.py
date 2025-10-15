# -*- coding: utf-8 -*-
# test_smart_normalizer.py
# SmartNormalizer 통합 테스트

"""
SmartNormalizer 기능 검증 스크립트
"""

import sys
from pathlib import Path

# PYTHONPATH 설정
modules_path = Path(__file__).parent.parent
sys.path.insert(0, str(modules_path))

from crawl_utils.services.smart_normalizer import SmartNormalizer


def test_basic_normalize():
    """기본 정규화 테스트"""
    print("\n=== Test 1: 기본 정규화 ===")
    
    normalizer = SmartNormalizer()
    
    # 실제 크롤링 결과 예시
    extracted = {
        "images": [
            "https://img.example.com/product1.jpg",
            "https://img.example.com/product2.png"
        ],
        "title": "나이키 에어맥스 신발",
        "price": "89,000원",
        "description": "편안한 착용감의 운동화",
        "options": ["블랙", "화이트", "레드"],
    }
    
    items = normalizer.normalize(extracted, section="product_123", name_prefix="nike")
    
    print(f"총 {len(items)}개 아이템 생성")
    print()
    
    for idx, item in enumerate(items, 1):
        print(f"{idx}. Kind: {item.kind:7s} | Name: {item.name_hint:25s} | Value: {str(item.value)[:50]}")
    
    # 검증
    assert len(items) == 8  # images(2) + title(1) + price(1) + description(1) + options(3)
    
    # 이미지 검증
    image_items = [item for item in items if item.kind == "image"]
    assert len(image_items) == 2
    assert all(item.extension == "jpg" or item.extension == "png" for item in image_items)
    
    # 텍스트 검증
    text_items = [item for item in items if item.kind == "text"]
    assert len(text_items) == 6
    
    print("\n✅ Test 1 통과!")


def test_url_type_inference():
    """URL 타입 추론 테스트"""
    print("\n=== Test 2: URL 타입 추론 ===")
    
    normalizer = SmartNormalizer()
    
    data = {
        "product_image": "https://cdn.com/product.jpg",
        "video_url": "https://cdn.com/demo.mp4",
        "manual_pdf": "https://cdn.com/manual.pdf",
        "archive": "https://cdn.com/files.zip",
    }
    
    items = normalizer.normalize(data, section="test")
    
    print(f"총 {len(items)}개 아이템 생성")
    for item in items:
        print(f"- {item.metadata['source_key']:15s}: {item.kind:7s} (inferred: {item.metadata['inferred_type']})")
    
    # 검증
    assert items[0].kind == "image"
    assert items[1].kind == "file"  # video → file
    assert items[2].kind == "file"  # document → file
    assert items[3].kind == "file"  # archive → file
    
    print("\n✅ Test 2 통과!")


def test_text_detection():
    """텍스트 타입 감지 테스트"""
    print("\n=== Test 3: 텍스트 타입 감지 ===")
    
    normalizer = SmartNormalizer()
    
    data = {
        "product_name": "상품명",
        "category": "운동화",
        "price_text": "10,000원",
        "tags": ["태그1", "태그2"],
    }
    
    items = normalizer.normalize(data)
    
    print(f"총 {len(items)}개 아이템 생성")
    for item in items:
        print(f"- {item.name_hint}: {item.kind} = {item.value}")
    
    # 모두 text여야 함
    assert all(item.kind == "text" for item in items)
    assert len(items) == 5  # 3개 단일값 + 2개 태그
    
    print("\n✅ Test 3 통과!")


def test_normalize_many():
    """여러 레코드 일괄 처리 테스트"""
    print("\n=== Test 4: 여러 레코드 일괄 처리 ===")
    
    normalizer = SmartNormalizer()
    
    # 검색 결과 예시
    records = [
        {
            "title": "상품1",
            "image": "https://img.com/1.jpg",
            "price": "10,000원"
        },
        {
            "title": "상품2",
            "image": "https://img.com/2.jpg",
            "price": "20,000원"
        },
        {
            "title": "상품3",
            "image": "https://img.com/3.jpg",
            "price": "30,000원"
        },
    ]
    
    items = normalizer.normalize_many(
        records,
        section_template="product_{index}",
        name_prefix="search"
    )
    
    print(f"총 {len(items)}개 아이템 생성 (레코드 {len(records)}개)")
    
    # 섹션별 그룹화
    sections = {}
    for item in items:
        if item.section not in sections:
            sections[item.section] = []
        sections[item.section].append(item)
    
    for section, section_items in sections.items():
        print(f"\n[{section}] {len(section_items)}개 아이템:")
        for item in section_items:
            print(f"  - {item.name_hint}: {item.kind} = {str(item.value)[:40]}")
    
    # 검증
    assert len(items) == 9  # 3개 레코드 * 3개 필드
    assert len(sections) == 3  # 3개 섹션
    
    print("\n✅ Test 4 통과!")


def test_edge_cases():
    """엣지 케이스 테스트"""
    print("\n=== Test 5: 엣지 케이스 ===")
    
    normalizer = SmartNormalizer()
    
    data = {
        "empty_string": "",
        "none_value": None,
        "empty_list": [],
        "list_with_none": [None, "value", None],
        "whitespace": "   ",
    }
    
    items = normalizer.normalize(data)
    
    print(f"총 {len(items)}개 아이템 생성 (빈 값 제외)")
    for item in items:
        print(f"- {item.name_hint}: {item.value}")
    
    # 빈 값은 제외되어야 함
    assert len(items) == 1  # "value"만
    assert items[0].value == "value"
    
    print("\n✅ Test 5 통과!")


def test_extension_inference():
    """확장자 추론 테스트"""
    print("\n=== Test 6: 확장자 추론 ===")
    
    normalizer = SmartNormalizer()
    
    data = {
        "jpg_image": "https://cdn.com/photo.jpg",
        "png_image": "https://cdn.com/icon.png",
        "gif_image": "https://cdn.com/banner.gif",
        "webp_image": "https://cdn.com/modern.webp",
    }
    
    items = normalizer.normalize(data)
    
    print(f"총 {len(items)}개 아이템 생성")
    for item in items:
        print(f"- {item.name_hint}: ext={item.extension} | url={item.value}")
    
    # 확장자 검증
    assert items[0].extension == "jpg"
    assert items[1].extension == "png"
    assert items[2].extension == "gif"
    assert items[3].extension == "webp"
    
    print("\n✅ Test 6 통과!")


def main():
    """전체 테스트 실행"""
    print("=" * 60)
    print("SmartNormalizer 통합 테스트")
    print("=" * 60)
    
    try:
        test_basic_normalize()
        test_url_type_inference()
        test_text_detection()
        test_normalize_many()
        test_edge_cases()
        test_extension_inference()
        
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 통과!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
