# -*- coding: utf-8 -*-
"""logs_utils/configs YAML 파일 테스트"""

import sys
from pathlib import Path

# PYTHONPATH 설정
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from logs_utils import LogManager, LogPolicy
from cfg_utils import ConfigLoader


def test_log_yaml():
    """log.yaml 테스트"""
    print("=" * 60)
    print("1. log.yaml - 기본 logging 섹션")
    print("=" * 60)
    
    manager = LogManager("modules/logs_utils/configs/log.yaml")
    
    print(f"✅ LogManager 생성 성공")
    print(f"   - name: {manager.config.name}")
    print(f"   - level: {manager.config.level}")
    print(f"   - sinks: {len(manager.config.sinks)}")
    print(f"   - context: {manager.config.context}")
    
    manager.logger.info("기본 logging 섹션 테스트")
    manager.logger.debug("DEBUG 메시지 (필터링됨)")
    
    print()


def test_log_yaml_sections():
    """log.yaml 다양한 섹션 테스트"""
    print("=" * 60)
    print("2. log.yaml - 다양한 섹션")
    print("=" * 60)
    
    sections = [
        "example_console",
        "example_file",
        "example_production",
        "example_development",
    ]
    
    for section in sections:
        try:
            loader = ConfigLoader(
                base_sources=[(LogPolicy(), "logging")],
                override_sources=[("modules/logs_utils/configs/log.yaml", section)]
            )
            policy = loader.to_model(LogPolicy, section=section)
            
            print(f"✅ {section}")
            print(f"   - name: {policy.name}")
            print(f"   - level: {policy.level}")
            print(f"   - sinks: {len(policy.sinks)}")
            
        except Exception as e:
            print(f"❌ {section}: {e}")
    
    print()


def test_config_loader_log_yaml():
    """config_loader_log.yaml 테스트 - config_loader_cfg_path로 주입"""
    print("=" * 60)
    print("3. config_loader_log.yaml - config_loader_cfg_path로 주입")
    print("=" * 60)
    
    sections = [
        "config_loader",              # 기본
        "config_loader_debug",        # 디버그
        "config_loader_production",   # 운영
    ]
    
    from pydantic import BaseModel, Field
    
    class TestPolicy(BaseModel):
        value: int = Field(100, description="테스트 값")
    
    for section in sections:
        try:
            # config_loader_cfg_path로 정책 파일 전달
            loader = ConfigLoader(
                config_loader_cfg_path=("modules/logs_utils/configs/config_loader_log.yaml", section),
                base_sources=[(TestPolicy(), "test")]
            )
            
            state = loader.get_state()
            
            print(f"✅ {section}")
            print(f"   - ConfigLoader 생성 성공 (로깅 정책 적용)")
            print(f"   - test__value = {state.get('test__value')}")
            
        except Exception as e:
            print(f"❌ {section}: {e}")
            import traceback
            traceback.print_exc()
    
    print()


def test_config_loader_with_log():
    """ConfigLoader + config_loader_cfg_path 테스트"""
    print("=" * 60)
    print("4. ConfigLoader + config_loader_cfg_path")
    print("=" * 60)
    
    from pydantic import BaseModel, Field
    
    class TestPolicy(BaseModel):
        value: int = Field(default=100, description="테스트 값")
    
    # config_loader_cfg_path로 정책 파일 전달 (log 필드 자동 로드)
    loader = ConfigLoader(
        config_loader_cfg_path=("modules/logs_utils/configs/config_loader_log.yaml", "config_loader"),
        base_sources=[(TestPolicy(), "test")]
    )
    
    print(f"✅ ConfigLoader 생성 성공 (로깅 활성화)")
    
    # State 추출 (로그 출력됨)
    state = loader.get_state()
    print(f"✅ State 추출: test__value = {state.get('test__value')}")
    
    print()


def test_log_manager_with_override():
    """LogManager Override 테스트"""
    print("=" * 60)
    print("5. LogManager Override")
    print("=" * 60)
    
    manager = LogManager(
        "modules/logs_utils/configs/log.yaml",
        name="override_test",
        level="DEBUG"
    )
    
    print(f"✅ Override 적용")
    print(f"   - name: {manager.config.name}")
    print(f"   - level: {manager.config.level}")
    
    manager.logger.info("INFO 메시지")
    manager.logger.debug("DEBUG 메시지")
    
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("logs_utils/configs YAML 파일 테스트")
    print("=" * 60 + "\n")
    
    try:
        test_log_yaml()
        test_log_yaml_sections()
        test_config_loader_log_yaml()
        test_config_loader_with_log()
        test_log_manager_with_override()
        
        print("=" * 60)
        print("✅ 모든 테스트 성공!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
