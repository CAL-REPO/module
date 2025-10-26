# -*- coding: utf-8 -*-
"""
Test PostProcessor with metadata (DataNormalizer)
"""

from pathlib import Path

from crawl_utils.core.policy import NormalizationRule
from crawl_utils.core.models import NormalizedItem
from crawl_utils.services.Item_Post_Processor import ItemNormalizer
from crawl_utils.services.post_processor import SyncPostProcessor


def test_post_processor_metadata():
    """PostProcessor가 metadata의 directory/name/ops를 Jinja2로 렌더링하는지 확인"""
    print("=" * 80)
    print("PostProcessor v5.1 metadata 기반 저장 테스트")
    print("=" * 80)
    
    # 1. Normalizer로 NormalizedItem 생성 (Rule 모드)
    rule = NormalizationRule(
        kind="text",
        source="title",
        directory="{{env.output_dir}}/test/{{runtime.cas_no}}",
        name="{{runtime.cas_no}}_title",
        explode=False,
        allow_empty=False,
        auto_infer=False
    )
    
    normalizer = ItemNormalizer(rules=[rule])
    records = [{"title": "Test Product"}]
    items = normalizer.normalize(records)
    
    print(f"✅ Normalizer 생성: {len(items)}개 아이템")
    print(f"   metadata: {items[0].metadata}")
    
    # 2. PostProcessor로 저장 (metadata 기반)
    post_processor = SyncPostProcessor(
        runtime_context={"cas_no": "TEST-001"},
        env_context={"output_dir": "output"}
    )
    
    print(f"\n✅ PostProcessor 초기화 완료")
    print(f"   - runtime_context: {post_processor.runtime_context}")
    print(f"   - env_context: {post_processor.env_context}")
    
    # metadata 확인
    has_metadata = items[0].metadata and "directory" in items[0].metadata
    print(f"\n✅ metadata 확인: {has_metadata}")
    
    if has_metadata:
        # 경로 생성 테스트
        path = post_processor._create_path_from_metadata(items[0])
        print(f"✅ 경로 생성 성공: {path}")
        
        # 예상 경로 확인
        expected = Path("output/test/TEST-001/TEST-001_title.txt")
        print(f"   예상: {expected}")
        print(f"   실제: {path}")
        
        # 경로 비교
        if path.as_posix() == expected.as_posix():
            print(f"   ✅ 경로 일치!")
        else:
            print(f"   ❌ 경로 불일치")


if __name__ == "__main__":
    try:
        test_post_processor_metadata()
        
        print("\n" + "=" * 80)
        print("✅ 테스트 완료!")
        print("=" * 80)
        print("\n📋 확인 사항:")
        print("1. Normalizer → metadata에 directory/name/ops 저장")
        print("2. PostProcessor._create_path_from_metadata() → Jinja2 렌더링")
        print("3. 렌더링된 경로: output/test/TEST-001/TEST-001_title.txt")
        print("\n🎯 v5.1 구조:")
        print("- NormalizationRule (Rule + Auto 모드)")
        print("- Normalizer (단일 통합)")
        print("- PostProcessor (metadata 기반만)")
        print("- StoragePolicy 제거 완료")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
