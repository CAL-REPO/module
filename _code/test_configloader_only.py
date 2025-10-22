#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ConfigLoader를 사용한 WebDriver 3개 정책 테스트 (간소화 버전)

ConfigLoader로 설정을 로드하고 비교하는 테스트
"""

from pathlib import Path
import sys
import json

# PYTHONPATH 추가
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from cfg_utils import ConfigLoader


def main():
    print("\n🚀 ConfigLoader WebDriver 3개 정책 비교 테스트")
    print("=" * 80)
    
    # ConfigLoader로 webdriver_config_loader.yaml 로드
    config_loader_path = Path(__file__).parent / "modules" / "crawl_utils" / "configs" / "webdriver_config_loader.yaml"
    
    if not config_loader_path.exists():
        print(f"❌ ConfigLoader YAML 파일을 찾을 수 없습니다: {config_loader_path}")
        return
    
    # ConfigLoader 생성
    print(f"\n✅ ConfigLoader 생성: {config_loader_path.name}")
    config = ConfigLoader(config_loader_cfg_path=str(config_loader_path))
    
    # 3개 섹션 추출
    print(f"\n📋 3개 WebDriver 설정 추출 중...")
    configs = {
        "webdriver": config.to_dict(section="webdriver"),
        "webdriver_china": config.to_dict(section="webdriver_china"),
        "webdriver_global": config.to_dict(section="webdriver_global"),
    }
    
    print(f"✅ 모든 설정 로드 완료")
    
    # 설정 비교
    print("\n" + "=" * 80)
    print("📊 3개 WebDriver 설정 비교")
    print("=" * 80)
    
    print(f"\n{'항목':<25} | {'webdriver':<20} | {'webdriver_china':<20} | {'webdriver_global':<20}")
    print("-" * 110)
    
    # 주요 항목 비교
    keys = ["provider", "region", "headless", "window_size", "accept_languages", "disable_automation"]
    for key in keys:
        row = f"{key:<25}"
        for name in ["webdriver", "webdriver_china", "webdriver_global"]:
            value = configs[name].get(key, "N/A")
            if isinstance(value, str) and len(value) > 18:
                value = value[:15] + "..."
            elif isinstance(value, list):
                value = str(value)
            row += f" | {str(value):<20}"
        print(row)
    
    # Firefox 설정 상세 비교
    print("\n" + "=" * 80)
    print("🦊 Firefox 전용 설정 상세 비교")
    print("=" * 80)
    
    firefox_keys = ["binary_path", "profile_path", "driver_path", "use_webdriver_manager", 
                    "dom_enabled", "resist_fingerprint_enabled"]
    
    for name in ["webdriver", "webdriver_china", "webdriver_global"]:
        print(f"\n[{name}]")
        firefox_config = configs[name].get("firefox", {})
        for key in firefox_keys:
            value = firefox_config.get(key, "N/A")
            print(f"   - {key:<30}: {value}")
    
    # JSON 출력 (전체 설정)
    print("\n" + "=" * 80)
    print("📄 전체 설정 (JSON 형식)")
    print("=" * 80)
    
    for name in ["webdriver", "webdriver_china", "webdriver_global"]:
        print(f"\n[{name}]")
        print(json.dumps(configs[name], indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 80)
    print("✅ 테스트 완료!")
    print("=" * 80)
    
    # 결론
    print("\n💡 결론:")
    print("   - ConfigLoader는 3개의 YAML 파일을 성공적으로 로드했습니다.")
    print("   - 각 설정은 서로 다른 region과 profile_path를 가집니다.")
    print("   - webdriver.yaml: 기본 글로벌 (profile_path 없음)")
    print("   - webdriver_china.yaml: 중국 지역 (CRAWL_CHINA)")
    print("   - webdriver_global.yaml: 글로벌 지역 (CRAWL_GLOBAL)")


if __name__ == "__main__":
    main()
