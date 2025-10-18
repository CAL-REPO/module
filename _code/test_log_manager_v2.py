# -*- coding: utf-8 -*-
"""LogManager + cfg_utils_v2 통합 테스트"""

import sys
from pathlib import Path

# PYTHONPATH 설정
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from logs_utils import LogManager, LogPolicy, SinkPolicy


def test_log_manager_with_policy():
    """LogPolicy 직접 전달 테스트"""
    print("=" * 60)
    print("1. LogPolicy 직접 전달 테스트")
    print("=" * 60)
    
    # LogPolicy 생성
    policy = LogPolicy(
        enabled=True,
        name="test_direct",
        level="DEBUG",
        sinks=[
            SinkPolicy(sink_type="console", level="INFO")
        ]
    )
    
    # LogManager 생성
    manager = LogManager(policy)
    
    print(f"✅ LogManager 생성 성공")
    print(f"   - config.name: {manager.config.name}")
    print(f"   - config.level: {manager.config.level}")
    print(f"   - config.enabled: {manager.config.enabled}")
    print(f"   - handlers: {len(manager._handler_ids)}")
    
    # 로그 출력
    manager.logger.info("테스트 로그 - INFO")
    manager.logger.debug("테스트 로그 - DEBUG (필터링됨)")
    
    print()


def test_log_manager_with_yaml():
    """YAML 파일로 로드 테스트"""
    print("=" * 60)
    print("2. YAML 파일 로드 테스트")
    print("=" * 60)
    
    yaml_path = Path("modules/logs_utils/configs/logging.yaml")
    
    if not yaml_path.exists():
        print(f"⚠️  {yaml_path} 파일이 없습니다. 스킵")
        print()
        return
    
    # YAML에서 로드
    manager = LogManager(str(yaml_path))
    
    print(f"✅ YAML 로드 성공")
    print(f"   - config.name: {manager.config.name}")
    print(f"   - config.level: {manager.config.level}")
    print(f"   - handlers: {len(manager._handler_ids)}")
    
    # 로그 출력
    manager.logger.info("YAML 설정으로 로그 출력")
    
    print()


def test_log_manager_with_dict():
    """dict로 생성 테스트"""
    print("=" * 60)
    print("3. dict로 생성 테스트")
    print("=" * 60)
    
    config_dict = {
        "enabled": True,
        "name": "test_dict",
        "level": "INFO",
        "sinks": [
            {
                "sink_type": "console",
                "level": "INFO",
                "colorize": True
            }
        ]
    }
    
    # dict에서 로드
    manager = LogManager(config_dict)
    
    print(f"✅ dict 로드 성공")
    print(f"   - config.name: {manager.config.name}")
    print(f"   - config.level: {manager.config.level}")
    
    # 로그 출력
    manager.logger.info("dict 설정으로 로그 출력")
    
    print()


def test_log_manager_with_overrides():
    """Override 테스트"""
    print("=" * 60)
    print("4. Override 테스트")
    print("=" * 60)
    
    # 기본 LogPolicy + Override
    manager = LogManager(
        None,  # 기본 설정
        name="test_override",
        level="WARNING"
    )
    
    print(f"✅ Override 적용 성공")
    print(f"   - config.name: {manager.config.name}")
    print(f"   - config.level: {manager.config.level}")
    
    # 로그 출력
    manager.logger.info("INFO 로그 (필터링됨)")
    manager.logger.warning("WARNING 로그 (출력됨)")
    
    print()


def test_log_manager_with_context():
    """Context 추가 테스트"""
    print("=" * 60)
    print("5. Context 추가 테스트")
    print("=" * 60)
    
    policy = LogPolicy(
        enabled=True,
        name="test_context",
        level="INFO",
        sinks=[SinkPolicy(sink_type="console", level="INFO")]
    )
    
    # Context 추가
    manager = LogManager(
        policy,
        context={
            "loader_id": 12345,
            "config_path": "/path/to/config.yaml"
        }
    )
    
    print(f"✅ Context 추가 성공")
    print(f"   - extra_context: {manager._extra_context}")
    
    # 로그 출력 (context 포함)
    manager.logger.info("Context가 포함된 로그")
    
    print()


def test_log_manager_disabled():
    """로깅 비활성화 테스트"""
    print("=" * 60)
    print("6. 로깅 비활성화 테스트")
    print("=" * 60)
    
    policy = LogPolicy(
        enabled=False,
        name="test_disabled",
        level="INFO"
    )
    
    manager = LogManager(policy)
    
    print(f"✅ LogManager 생성 성공 (로깅 비활성화)")
    print(f"   - config.enabled: {manager.config.enabled}")
    print(f"   - handlers: {len(manager._handler_ids)} (0이어야 함)")
    
    # 로그 출력 (출력 안됨)
    manager.logger.info("이 로그는 출력되지 않습니다")
    
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LogManager + cfg_utils_v2 통합 테스트")
    print("=" * 60 + "\n")
    
    try:
        test_log_manager_with_policy()
        test_log_manager_with_yaml()
        test_log_manager_with_dict()
        test_log_manager_with_overrides()
        test_log_manager_with_context()
        test_log_manager_disabled()
        
        print("=" * 60)
        print("✅ 모든 테스트 성공!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
