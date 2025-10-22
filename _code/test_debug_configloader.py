#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ConfigLoader 데이터 구조 디버깅
"""

from pathlib import Path
import sys
import json

# PYTHONPATH 추가
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from cfg_utils import ConfigLoader


def debug_configloader():
    """ConfigLoader 데이터 구조 확인"""
    print("=" * 80)
    print("ConfigLoader 데이터 구조 디버깅")
    print("=" * 80)
    
    # ConfigLoader로 webdriver_config_loader.yaml 로드
    config_loader_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver_config_loader.yaml"
    
    if not config_loader_path.exists():
        print(f"❌ ConfigLoader YAML 파일을 찾을 수 없습니다: {config_loader_path}")
        return
    
    # ConfigLoader 생성
    config = ConfigLoader(config_loader_cfg_path=str(config_loader_path))
    
    # webdriver 섹션 추출
    webdriver_config = config.to_dict(section="webdriver")
    
    print(f"\n📋 webdriver 섹션 내용:")
    print(json.dumps(webdriver_config, indent=2, ensure_ascii=False))
    
    print(f"\n🔍 firefox 섹션 확인:")
    print(f"   - Type: {type(webdriver_config.get('firefox'))}")
    print(f"   - Value: {webdriver_config.get('firefox')}")
    print(f"   - Is None: {webdriver_config.get('firefox') is None}")
    print(f"   - Is Empty Dict: {webdriver_config.get('firefox') == {}}")
    
    # webdriver_china 섹션 추출
    print(f"\n" + "=" * 80)
    webdriver_china_config = config.to_dict(section="webdriver_china")
    
    print(f"\n📋 webdriver_china 섹션 내용:")
    print(json.dumps(webdriver_china_config, indent=2, ensure_ascii=False))
    
    print(f"\n🔍 firefox 섹션 확인:")
    print(f"   - Type: {type(webdriver_china_config.get('firefox'))}")
    print(f"   - Value: {webdriver_china_config.get('firefox')}")
    
    # webdriver_global 섹션 추출
    print(f"\n" + "=" * 80)
    webdriver_global_config = config.to_dict(section="webdriver_global")
    
    print(f"\n📋 webdriver_global 섹션 내용:")
    print(json.dumps(webdriver_global_config, indent=2, ensure_ascii=False))
    
    print(f"\n🔍 firefox 섹션 확인:")
    print(f"   - Type: {type(webdriver_global_config.get('firefox'))}")
    print(f"   - Value: {webdriver_global_config.get('firefox')}")


if __name__ == "__main__":
    debug_configloader()
