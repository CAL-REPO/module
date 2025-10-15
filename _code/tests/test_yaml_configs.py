#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YAML 설정 파일 테스트 스크립트
"""

import sys
from pathlib import Path

# PYTHONPATH 설정
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from logs_utils import create_logger, LogContextManager


def test_yaml_configs():
    """모든 YAML 설정 파일 테스트"""
    
    config_dir = Path(__file__).parent.parent / "modules" / "logs_utils" / "config"
    
    yaml_files = {
        "log.yaml": "전체 기능 포함",
        "log.simple.yaml": "간단한 설정",
        "log.console.yaml": "콘솔 전용",
        "log.production.yaml": "프로덕션",
        "log.structured.yaml": "JSON 구조화",
        "log.debug.yaml": "디버깅",
        "log.time_rotation.yaml": "시간 기준 회전",
    }
    
    print("=" * 70)
    print("YAML 설정 파일 테스트")
    print("=" * 70)
    
    for yaml_file, description in yaml_files.items():
        yaml_path = config_dir / yaml_file
        
        if not yaml_path.exists():
            print(f"\n❌ {yaml_file}: 파일 없음")
            continue
        
        print(f"\n📄 {yaml_file}: {description}")
        print("-" * 70)
        
        try:
            # Context Manager로 테스트
            with LogContextManager(yaml_path) as log:
                log.info(f"[{yaml_file}] INFO 레벨 테스트")
                log.debug(f"[{yaml_file}] DEBUG 레벨 테스트")
                log.warning(f"[{yaml_file}] WARNING 레벨 테스트")
                log.success(f"[{yaml_file}] SUCCESS 테스트")
            
            print(f"✅ {yaml_file}: 정상 동작")
            
        except Exception as e:
            print(f"❌ {yaml_file}: 오류 발생 - {e}")
    
    print("\n" + "=" * 70)
    print("테스트 완료!")
    print("=" * 70)


def test_runtime_override():
    """Runtime Override 테스트"""
    
    print("\n" + "=" * 70)
    print("Runtime Override 테스트")
    print("=" * 70)
    
    config_path = Path(__file__).parent.parent / "modules" / "logs_utils" / "config" / "log.simple.yaml"
    
    # YAML 로드 + Runtime Override
    with LogContextManager(config_path, name="overridden_logger") as log:
        log.info("Runtime으로 name을 override했습니다")
        log.success("정상 동작 확인")
    
    print("✅ Runtime Override 성공")


def test_dict_config():
    """Dictionary 설정 테스트"""
    
    print("\n" + "=" * 70)
    print("Dictionary 설정 테스트")
    print("=" * 70)
    
    config = {
        "name": "dict_logger",
        "sinks": [
            {
                "sink_type": "console",
                "level": "INFO",
                "format": "<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
                "colorize": True
            },
            {
                "sink_type": "file",
                "filepath": "output/logs/dict_test.log",
                "level": "DEBUG",
                "rotation": "1 MB",
                "retention": "3 days",
                "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
            }
        ]
    }
    
    with LogContextManager(config) as log:
        log.info("Dictionary 설정으로 로거 생성")
        log.debug("파일에만 기록됩니다")
        log.success("정상 동작!")
    
    print("✅ Dictionary 설정 성공")


if __name__ == "__main__":
    # 1. YAML 파일 테스트
    test_yaml_configs()
    
    # 2. Runtime Override 테스트
    test_runtime_override()
    
    # 3. Dictionary 테스트
    test_dict_config()
    
    print("\n" + "🎉 모든 테스트 완료!")
