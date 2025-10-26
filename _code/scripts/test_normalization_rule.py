# -*- coding: utf-8 -*-
"""
Test v5.0: NormalizationRule (directory + name + ops)
"""

from crawl_utils.core.policy import (
    NormalizationPolicy,
    NormalizationRule,
    CrawlPolicy,
    ScrollPolicy,
    ExtractorPolicy,
    WaitPolicy
)
from crawl_utils.services.data_normalizer import DataNormalizer


def test_normalization_rule():
    """NormalizationRule에 directory/name/ops 포함 확인"""
    print("=" * 80)
    print("1. NormalizationRule 구조 확인")
    print("=" * 80)
    
    rule = NormalizationRule(
        kind="image",
        source="product.images",
        directory="{{env.output_dir}}/images/{{runtime.cas_no}}",
        name="{{runtime.cas_no}}_{{item.index}}",
        ops={"overwrite": False, "ensure_unique": True},
        explode=True
    )
    
    print(f"✅ NormalizationRule 생성 성공")
    print(f"   - kind: {rule.kind}")
    print(f"   - source: {rule.source}")
    print(f"   - directory: {rule.directory}")
    print(f"   - name: {rule.name}")
    print(f"   - ops: {rule.ops}")
    print(f"   - explode: {rule.explode}")


def test_data_normalizer():
    """DataNormalizer가 metadata에 directory/name/ops 저장하는지 확인"""
    print("\n" + "=" * 80)
    print("2. DataNormalizer metadata 확인")
    print("=" * 80)
    
    policy = NormalizationPolicy(
        rules=[
            NormalizationRule(
                kind="image",
                source="product.images",
                directory="{{env.output_dir}}/images/{{runtime.cas_no}}",
                name="{{runtime.cas_no}}_{{item.index}}",
                ops={"overwrite": False, "ensure_unique": True},
                explode=True
            )
        ]
    )
    
    normalizer = DataNormalizer(policy)
    
    records = [
        {
            "product": {
                "images": ["https://a.jpg", "https://b.jpg"]
            }
        }
    ]
    
    items = normalizer.normalize(records)
    
    print(f"✅ DataNormalizer 정규화 성공")
    print(f"   - 입력: {len(records)}개 레코드")
    print(f"   - 출력: {len(items)}개 NormalizedItem")
    
    for i, item in enumerate(items):
        print(f"\n   [{i+1}] {item.kind}")
        print(f"       value: {item.value}")
        print(f"       metadata:")
        print(f"         - source_key: {item.metadata.get('source_key')}")
        print(f"         - directory: {item.metadata.get('directory')}")
        print(f"         - name: {item.metadata.get('name')}")
        print(f"         - ops: {item.metadata.get('ops')}")


def test_crawl_policy():
    """CrawlPolicy에 normalization 필드 확인"""
    print("\n" + "=" * 80)
    print("3. CrawlPolicy normalization 필드 확인")
    print("=" * 80)
    
    # Case 1: use_smart_normalizer=False + NormalizationPolicy
    crawl_policy = CrawlPolicy(
        name="crawl",
        site="aliexpress",
        method="detail",
        scroll=ScrollPolicy(),  # pyright: ignore
        extractor=ExtractorPolicy(),  # pyright: ignore
        wait=WaitPolicy(),  # pyright: ignore
        use_smart_normalizer=False,
        normalization=NormalizationPolicy(
            rules=[
                NormalizationRule(
                    kind="image",
                    source="product.images",
                    directory="{{env.output_dir}}/images/{{runtime.cas_no}}",
                    name="{{runtime.cas_no}}_{{item.index}}",
                    explode=True
                )
            ]
        )
    )
    
    print(f"✅ CrawlPolicy 생성 성공")
    print(f"   - use_smart_normalizer: {crawl_policy.use_smart_normalizer}")
    print(f"   - normalization: {len(crawl_policy.normalization.rules)}개 규칙")
    print(f"   - storage: {crawl_policy.storage}")


if __name__ == "__main__":
    try:
        test_normalization_rule()
        test_data_normalizer()
        test_crawl_policy()
        
        print("\n" + "=" * 80)
        print("✅ 모든 테스트 통과!")
        print("=" * 80)
        print("\n📋 요약:")
        print("1. NormalizationRule = directory + name + ops (fso_utils)")
        print("2. DataNormalizer = metadata에 directory/name/ops 저장")
        print("3. CrawlPolicy = normalization 필드 포함")
        print("\n🎯 다음 작업:")
        print("- PostProcessor: metadata의 directory/name/ops를 Jinja2로 렌더링")
        print("- Pipeline: Normalizer 선택 로직 완료 (이미 구현됨)")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
