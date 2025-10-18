# -*- coding: utf-8 -*-
"""cfg_utils_v2 LogPolicy 통합 테스트"""

import sys
from pathlib import Path

# PYTHONPATH 설정
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from cfg_utils_v2.core.policy import ConfigLoaderPolicy
from logs_utils import LogPolicy, SinkPolicy


def test_log_policy_type_hint():
    """LogPolicy 타입 힌트 테스트"""
    print("=" * 60)
    print("1. LogPolicy 타입 힌트 테스트")
    print("=" * 60)
    
    # LogPolicy 인스턴스 생성
    log_policy = LogPolicy(
        enabled=True,
        name="test_logger",
        level="DEBUG",
        sinks=[
            SinkPolicy(sink_type="console", level="INFO")
        ]
    )
    
    # ConfigLoaderPolicy에 LogPolicy 할당
    config_policy = ConfigLoaderPolicy(
        log=log_policy
    )
    
    print(f"✅ LogPolicy 타입: {type(config_policy.log)}")
    print(f"✅ LogPolicy.name: {config_policy.log.name}")
    print(f"✅ LogPolicy.level: {config_policy.log.level}")
    print(f"✅ LogPolicy.enabled: {config_policy.log.enabled}")
    print()


def test_config_loader_yaml_with_log():
    """config_loader.yaml에서 LogPolicy 로드 테스트"""
    print("=" * 60)
    print("2. config_loader.yaml LogPolicy 로드 테스트")
    print("=" * 60)
    
    from structured_io import YamlParser
    
    yaml_path = Path("modules/cfg_utils_v2/configs/config_loader.yaml")
    parser = YamlParser()
    data = parser.parse_file(yaml_path)
    
    print(f"✅ YAML 로드 성공")
    print(f"✅ log 섹션 존재: {'log' in data}")
    
    if 'log' in data:
        log_data = data['log']
        print(f"✅ log.enabled: {log_data.get('enabled')}")
        print(f"✅ log.name: {log_data.get('name')}")
        print(f"✅ log.level: {log_data.get('level')}")
        print(f"✅ log.sinks: {len(log_data.get('sinks', []))} items")
        
        # LogPolicy 인스턴스 생성
        log_policy = LogPolicy(**log_data)
        print(f"✅ LogPolicy 인스턴스 생성 성공")
        print(f"   - name: {log_policy.name}")
        print(f"   - level: {log_policy.level}")
        print(f"   - sinks: {len(log_policy.sinks)}")
    print()


def test_config_loader_with_log():
    """ConfigLoader에 LogPolicy 적용 테스트"""
    print("=" * 60)
    print("3. ConfigLoader LogPolicy 적용 테스트")
    print("=" * 60)
    
    from cfg_utils_v2 import ConfigLoader
    from pydantic import BaseModel, Field
    
    # 테스트용 Policy
    class TestPolicy(BaseModel):
        max_value: int = Field(100, description="최대값")
        enabled: bool = Field(True, description="활성화")
    
    # LogPolicy 생성
    log_policy = LogPolicy(
        enabled=True,
        name="test_config_loader",
        level="DEBUG",
        sinks=[
            SinkPolicy(
                sink_type="console",
                level="DEBUG",
                colorize=True
            )
        ]
    )
    
    print(f"✅ LogPolicy 생성: {log_policy.name}")
    
    # ConfigLoader 생성 (log 적용)
    try:
        loader = ConfigLoader(
            base_sources=[(TestPolicy(), "test")],
            log=log_policy
        )
        print(f"✅ ConfigLoader 생성 성공 (로깅 활성화)")
        print(f"   - Logger initialized: {loader._logger_initialized}")
        
        # State 추출 (로그 출력됨)
        state = loader.get_state()
        print(f"✅ State 추출 성공")
        print(f"   - test__max_value: {state.get('test__max_value')}")
        
    except Exception as e:
        print(f"❌ ConfigLoader 생성 실패: {e}")
    
    print()


def test_config_loader_without_log():
    """ConfigLoader 로깅 비활성화 테스트"""
    print("=" * 60)
    print("4. ConfigLoader 로깅 비활성화 테스트")
    print("=" * 60)
    
    from cfg_utils_v2 import ConfigLoader
    from pydantic import BaseModel, Field
    
    class TestPolicy(BaseModel):
        value: int = 42
    
    # log=None (로깅 비활성화)
    loader = ConfigLoader(
        base_sources=[(TestPolicy(), "test")],
        log=None
    )
    
    print(f"✅ ConfigLoader 생성 성공 (로깅 비활성화)")
    print(f"   - Logger initialized: {loader._logger_initialized}")
    print(f"   - Logger: {loader._logger}")
    
    state = loader.get_state()
    print(f"✅ State 추출 성공 (로그 없음)")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("cfg_utils_v2 + logs_utils 통합 테스트")
    print("=" * 60 + "\n")
    
    try:
        test_log_policy_type_hint()
        test_config_loader_yaml_with_log()
        test_config_loader_with_log()
        test_config_loader_without_log()
        
        print("=" * 60)
        print("✅ 모든 테스트 성공!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
