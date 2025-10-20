# -*- coding: utf-8 -*-
"""crawl_utils ConfigLoader 테스트

환경변수 자동 설정하여 ConfigLoader 검증
"""

import os
import json
from pathlib import Path
from cfg_utils import ConfigLoader
from pprint import pprint

# ✅ 테스트용 환경변수 자동 설정
TEST_ENV = {
    "CASHOP_PATHS": r"M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml"
}

# OS 환경변수에 설정
for key, value in TEST_ENV.items():
    os.environ[key] = value


def test_crawl_config_loader():
    """crawl_config_loader_test.yaml 로드 테스트 - KeyPathState 출력"""
    print("\n" + "="*80)
    print("TEST: crawl_config_loader_test.yaml - KeyPathState OUTPUT")
    print("="*80)
    
    # ConfigLoader 생성 (env_os로 환경변수 주입)
    config_loader_path = Path(__file__).parent / "modules/crawl_utils/configs/crawl_config_loader_test.yaml"
    
    loader = ConfigLoader(
        config_loader_cfg_path=str(config_loader_path),
        env_os=list(TEST_ENV.keys())  # ["CASHOP_PATHS"] - OS 환경변수에서 읽기
    )
    
    # 🔥 KeyPathState 직접 접근
    print("\n" + "🔥 KeyPathState ".ljust(80, "="))
    state = loader.config.state  # ConfigLoader.config.state
    print(f"Type: {type(state)}")
    print(f"Name: {state.name}")
    
    # KeyPathState의 내부 dict 출력
    print("\n" + "📦 KeyPathState.store (Internal Dict) ".ljust(80, "="))
    pprint(state.store, width=120, sort_dicts=False)
    
    # to_dict() 결과와 비교
    print("\n" + "🔄 to_dict() Result ".ljust(80, "="))
    full_config = loader.to_dict()
    pprint(full_config, width=120, sort_dicts=False)
    
    # 섹션별 상세 출력
    print("\n" + "📋 SECTION: env ".ljust(80, "="))
    if "env" in full_config:
        pprint(full_config["env"], width=120, sort_dicts=False)
    
    print("\n" + "📋 SECTION: webdriver_firefox ".ljust(80, "="))
    if "webdriver_firefox" in full_config:
        pprint(full_config["webdriver_firefox"], width=120, sort_dicts=False)
    
    print("\n" + "📋 SECTION: crawl ".ljust(80, "="))
    if "crawl" in full_config:
        pprint(full_config["crawl"], width=120, sort_dicts=False)
    
    print("\n" + "📋 SECTION: log ".ljust(80, "="))
    if "log" in full_config:
        pprint(full_config["log"], width=120, sort_dicts=False)
    
    print("\n✅ crawl_config_loader_test.yaml 로드 성공!\n")


def test_crawl_config_loader_prod():
    """crawl_config_loader.yaml (운영) 로드 테스트 - 전체 데이터 출력"""
    print("\n" + "="*80)
    print("TEST: crawl_config_loader.yaml (Production) - FULL DATA OUTPUT")
    print("="*80)
    
    config_loader_path = Path(__file__).parent / "modules/crawl_utils/configs/crawl_config_loader.yaml"
    
    loader = ConfigLoader(
        config_loader_cfg_path=str(config_loader_path),
        env_os=list(TEST_ENV.keys())
    )
    
    # 🔥 전체 설정 딕셔너리 출력
    print("\n" + "🔥 FULL CONFIG DICT (PRODUCTION) ".ljust(80, "="))
    full_config = loader.to_dict()
    pprint(full_config, width=120, sort_dicts=False)
    
    # JSON 포맷으로도 출력
    print("\n" + "💾 JSON FORMAT (PRODUCTION) ".ljust(80, "="))
    print(json.dumps(full_config, indent=2, ensure_ascii=False))
    
    print("\n✅ crawl_config_loader.yaml (Production) 로드 성공!\n")


def test_paths_resolution():
    """paths.local.yaml의 configs_crawl_dir 해석 확인"""
    print("\n" + "="*80)
    print("TEST: paths.local.yaml - configs_crawl_dir Resolution")
    print("="*80)
    
    # paths.local.yaml 직접 로드
    paths_yaml = Path(__file__).parent / "configs/paths.local.yaml"
    
    loader = ConfigLoader(
        src=str(paths_yaml),  # 파일 경로만 전달
        env_os=list(TEST_ENV.keys())
    )
    
    paths_dict = loader.to_dict()
    
    print(f"\n[1] modules_dir: {paths_dict.get('modules_dir')}")
    print(f"[2] configs_crawl_dir: {paths_dict.get('configs_crawl_dir')}")
    
    # configs_crawl_dir이 제대로 해석되었는지 확인
    expected_path = "M:/CALife/CAShop - 구매대행/_code/modules/crawl_utils/configs/crawl.yaml"
    actual_path = paths_dict.get('configs_crawl_dir')
    
    if actual_path == expected_path:
        print(f"\n✅ configs_crawl_dir 해석 성공!")
        print(f"   Expected: {expected_path}")
        print(f"   Actual:   {actual_path}")
    else:
        print(f"\n❌ configs_crawl_dir 해석 실패!")
        print(f"   Expected: {expected_path}")
        print(f"   Actual:   {actual_path}")
    
    print()


if __name__ == "__main__":
    # 환경변수 출력
    print("\n🔥 Test Environment Variables:")
    for key, value in TEST_ENV.items():
        print(f"  {key} = {value}")
    
    # 테스트 실행
    test_paths_resolution()
    test_crawl_config_loader()
    # test_crawl_config_loader_prod()  # Production 테스트는 주석 처리
    
    print("\n" + "="*80)
    print("✅ All Tests Completed!")
    print("="*80 + "\n")
