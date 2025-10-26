# -*- coding: utf-8 -*-
"""
Test Policy Hierarchy v5.1
"""

from crawl_utils.core.policy import (
    CrawlPolicy,
    ExecutionPolicy,
    RetryPolicy,
    PostProcessorPolicy,
    NormalizationRule,
    ExecutionMode
)


def test_execution_policy():
    """ExecutionPolicy 테스트"""
    print("=" * 80)
    print("ExecutionPolicy 테스트")
    print("=" * 80)
    
    # 기본값 테스트
    policy = ExecutionPolicy()
    print(f"✅ 기본값:")
    print(f"   - mode: {policy.mode}")
    print(f"   - concurrency: {policy.concurrency}")
    
    # 사용자 지정값 테스트
    policy = ExecutionPolicy(mode=ExecutionMode.SYNC, concurrency=1)
    print(f"\n✅ 사용자 지정:")
    print(f"   - mode: {policy.mode}")
    print(f"   - concurrency: {policy.concurrency}")


def test_retry_policy():
    """RetryPolicy 테스트"""
    print("\n" + "=" * 80)
    print("RetryPolicy 테스트")
    print("=" * 80)
    
    # 기본값 테스트
    policy = RetryPolicy()
    print(f"✅ 기본값:")
    print(f"   - retries: {policy.retries}")
    print(f"   - backoff_sec: {policy.backoff_sec}")
    
    # 사용자 지정값 테스트
    policy = RetryPolicy(retries=5, backoff_sec=3.0)
    print(f"\n✅ 사용자 지정:")
    print(f"   - retries: {policy.retries}")
    print(f"   - backoff_sec: {policy.backoff_sec}")


def test_post_processor_policy():
    """PostProcessorPolicy 테스트"""
    print("\n" + "=" * 80)
    print("PostProcessorPolicy 테스트")
    print("=" * 80)
    
    # 기본값 테스트
    policy = PostProcessorPolicy()
    print(f"✅ 기본값:")
    print(f"   - runtime_context: {policy.runtime_context}")
    print(f"   - env_context: {policy.env_context}")
    
    # 사용자 지정값 테스트
    policy = PostProcessorPolicy(
        runtime_context={"cas_no": "TEST-001", "date": "2025-10-26"},
        env_context={"output_dir": "output"}
    )
    print(f"\n✅ 사용자 지정:")
    print(f"   - runtime_context: {policy.runtime_context}")
    print(f"   - env_context: {policy.env_context}")


def test_crawl_policy_hierarchy():
    """CrawlPolicy 계층 구조 테스트"""
    print("\n" + "=" * 80)
    print("CrawlPolicy 계층 구조 테스트")
    print("=" * 80)
    
    # 최소 설정 (모든 기본값 사용)
    policy = CrawlPolicy()
    print(f"✅ 최소 설정 (기본값):")
    print(f"   - execution.mode: {policy.execution.mode}")
    print(f"   - execution.concurrency: {policy.execution.concurrency}")
    print(f"   - retry.retries: {policy.retry.retries}")
    print(f"   - retry.backoff_sec: {policy.retry.backoff_sec}")
    print(f"   - post_processor.runtime_context: {policy.post_processor.runtime_context}")
    print(f"   - rules: {len(policy.rules)}개")
    
    # 완전한 설정
    policy = CrawlPolicy(
        rules=[
            NormalizationRule(
                kind="image",
                source="product.images",
                directory="{{env.output_dir}}/images",
                name="{{runtime.cas_no}}_{{item.index}}",
                explode=True,
                allow_empty=False,
                auto_infer=False
            ),
            NormalizationRule(
                kind="text",
                source=None,
                auto_infer=True,
                directory="{{env.output_dir}}/texts",
                name="auto_{{item.index}}",
                explode=False,
                allow_empty=False
            )
        ],
        execution=ExecutionPolicy(mode=ExecutionMode.SYNC, concurrency=1),
        retry=RetryPolicy(retries=3, backoff_sec=2.0),
        post_processor=PostProcessorPolicy(
            runtime_context={"cas_no": "CAPEA-001", "date": "2025-10-26"},
            env_context={"output_dir": "output"}
        )
    )
    
    print(f"\n✅ 완전한 설정:")
    print(f"   - rules: {len(policy.rules)}개")
    print(f"     1. {policy.rules[0].kind} (source={policy.rules[0].source})")
    print(f"     2. {policy.rules[1].kind} (auto_infer={policy.rules[1].auto_infer})")
    print(f"   - execution.mode: {policy.execution.mode}")
    print(f"   - execution.concurrency: {policy.execution.concurrency}")
    print(f"   - retry.retries: {policy.retry.retries}")
    print(f"   - retry.backoff_sec: {policy.retry.backoff_sec}")
    print(f"   - post_processor.runtime_context: {policy.post_processor.runtime_context}")
    print(f"   - post_processor.env_context: {policy.post_processor.env_context}")


def test_dict_conversion():
    """Dict 변환 테스트 (ConfigLoader 호환성)"""
    print("\n" + "=" * 80)
    print("Dict 변환 테스트 (ConfigLoader 호환성)")
    print("=" * 80)
    
    policy = CrawlPolicy(
        execution=ExecutionPolicy(mode=ExecutionMode.SYNC),
        retry=RetryPolicy(retries=5),
        post_processor=PostProcessorPolicy(
            runtime_context={"cas_no": "TEST-001"}
        )
    )
    
    # model_dump() 테스트
    policy_dict = policy.model_dump()
    print(f"✅ policy.model_dump() 성공")
    print(f"   - execution: {policy_dict['execution']}")
    print(f"   - retry: {policy_dict['retry']}")
    print(f"   - post_processor: {policy_dict['post_processor']}")
    
    # 재생성 테스트
    policy_restored = CrawlPolicy(**policy_dict)
    print(f"\n✅ CrawlPolicy(**dict) 재생성 성공")
    print(f"   - execution.mode: {policy_restored.execution.mode}")
    print(f"   - retry.retries: {policy_restored.retry.retries}")


if __name__ == "__main__":
    try:
        test_execution_policy()
        test_retry_policy()
        test_post_processor_policy()
        test_crawl_policy_hierarchy()
        test_dict_conversion()
        
        print("\n" + "=" * 80)
        print("✅ 모든 테스트 통과!")
        print("=" * 80)
        print("\n📋 v5.1 정책 계층화 완료:")
        print("1. ExecutionPolicy (mode, concurrency)")
        print("2. RetryPolicy (retries, backoff_sec)")
        print("3. PostProcessorPolicy (runtime/env context)")
        print("4. CrawlPolicy (계층화된 통합 정책)")
        print("\n🎯 특징:")
        print("- Sync/Async 구분 없는 공통 정책")
        print("- 모든 정책에 기본값 제공")
        print("- ConfigLoader 완전 호환")
        print("- Pydantic BaseModel 기반 타입 안정성")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
