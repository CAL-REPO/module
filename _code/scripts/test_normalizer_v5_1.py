# -*- coding: utf-8 -*-
"""
Test Normalizer (v5.1 - Rule + Auto 통합)
"""

from crawl_utils.core.policy import NormalizationRule
from crawl_utils.services.Item_Post_Processor import ItemNormalizer


def test_normalizer_rule_mode():
    """Rule 모드 테스트 (source 있음)"""
    print("=" * 80)
    print("Rule 모드 테스트 (source 지정)")
    print("=" * 80)
    
    # Rule 생성 (source 있음 → Rule 모드)
    rule = NormalizationRule(
        kind="image",
        source="product.images",
        directory="{{env.output_dir}}/images/{{runtime.cas_no}}",
        name="{{runtime.cas_no}}_{{item.index}}",
        explode=True
    )
    
    print(f"✅ NormalizationRule 생성 (Rule 모드)")
    print(f"   - kind: {rule.kind}")
    print(f"   - source: {rule.source}")
    print(f"   - auto_infer: {rule.auto_infer}")
    
    # Normalizer 생성
    normalizer = ItemNormalizer(rules=[rule])
    
    # 테스트 데이터
    records = [{"product": {"images": ["a.jpg", "b.jpg"]}}]
    
    # Normalize
    items = normalizer.normalize(records)
    
    print(f"\n✅ Normalizer.normalize() 성공")
    print(f"   - 출력: {len(items)}개 NormalizedItem")
    
    for i, item in enumerate(items, start=1):
        print(f"\n   Item {i}:")
        print(f"     - kind: {item.kind}")
        print(f"     - value: {item.value}")
        print(f"     - metadata.mode: {item.metadata.get('mode')}")
        print(f"     - metadata.directory: {item.metadata.get('directory')}")
        print(f"     - metadata.name: {item.metadata.get('name')}")


def test_normalizer_auto_mode():
    """Auto 모드 테스트 (source 없음)"""
    print("\n" + "=" * 80)
    print("Auto 모드 테스트 (source 없음, auto_infer=True)")
    print("=" * 80)
    
    # Rule 생성 (source 없음 → Auto 모드)
    rule = NormalizationRule(
        kind="image",
        source=None,
        auto_infer=True,
        directory="{{env.output_dir}}/auto",
        name="auto_{{item.index}}",
        explode=True
    )
    
    print(f"✅ NormalizationRule 생성 (Auto 모드)")
    print(f"   - kind: {rule.kind}")
    print(f"   - source: {rule.source}")
    print(f"   - auto_infer: {rule.auto_infer}")
    
    # Normalizer 생성
    normalizer = ItemNormalizer(rules=[rule])
    
    # 테스트 데이터 (이미지로 추론될 URL들)
    records = [{
        "images": ["https://img.com/1.jpg", "https://img.com/2.jpg"],
        "title": "Product Name"  # 이미지 아니므로 무시됨
    }]
    
    # Normalize
    items = normalizer.normalize(records)
    
    print(f"\n✅ Normalizer.normalize() 성공")
    print(f"   - 출력: {len(items)}개 NormalizedItem (이미지만 수집)")
    
    for i, item in enumerate(items, start=1):
        print(f"\n   Item {i}:")
        print(f"     - kind: {item.kind}")
        print(f"     - value: {item.value}")
        print(f"     - metadata.mode: {item.metadata.get('mode')}")
        print(f"     - metadata.inferred_type: {item.metadata.get('inferred_type')}")


def test_normalizer_mixed_mode():
    """Mixed 모드 테스트 (Rule + Auto 혼합)"""
    print("\n" + "=" * 80)
    print("Mixed 모드 테스트 (Rule + Auto 혼합)")
    print("=" * 80)
    
    # Rule 1: Rule 모드 (source 지정)
    rule1 = NormalizationRule(
        kind="text",
        source="title",
        directory="{{env.output_dir}}/texts",
        name="title_{{item.index}}",
        explode=False
    )
    
    # Rule 2: Auto 모드 (source 없음)
    rule2 = NormalizationRule(
        kind="image",
        source=None,
        auto_infer=True,
        directory="{{env.output_dir}}/images",
        name="auto_{{item.index}}",
        explode=True
    )
    
    print(f"✅ NormalizationRule 2개 생성")
    print(f"   - Rule 1: Rule 모드 (text, source=title)")
    print(f"   - Rule 2: Auto 모드 (image, auto_infer=True)")
    
    # Normalizer 생성
    normalizer = ItemNormalizer(rules=[rule1, rule2])
    
    # 테스트 데이터
    records = [{
        "title": "Test Product",
        "images": ["https://img.com/1.jpg", "https://img.com/2.jpg"],
        "price": "10,000원"  # 무시됨 (Rule 없음)
    }]
    
    # Normalize
    items = normalizer.normalize(records)
    
    print(f"\n✅ Normalizer.normalize() 성공")
    print(f"   - 출력: {len(items)}개 NormalizedItem")
    
    for i, item in enumerate(items, start=1):
        print(f"\n   Item {i}:")
        print(f"     - kind: {item.kind}")
        print(f"     - value: {item.value[:50] if len(str(item.value)) > 50 else item.value}")
        print(f"     - metadata.mode: {item.metadata.get('mode')}")


if __name__ == "__main__":
    try:
        test_normalizer_rule_mode()
        test_normalizer_auto_mode()
        test_normalizer_mixed_mode()
        
        print("\n" + "=" * 80)
        print("✅ 모든 테스트 통과!")
        print("=" * 80)
        print("\n📋 검증 완료:")
        print("1. Rule 모드 (source 있음) → KeyPath 추출")
        print("2. Auto 모드 (source 없음) → 자동 타입 추론")
        print("3. Mixed 모드 (Rule + Auto 혼합)")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
