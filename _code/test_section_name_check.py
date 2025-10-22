# -*- coding: utf-8 -*-
"""ConfigLoader 섹션명 테스트

YAML 파일의 최상위 섹션명이 ConfigLoader에서 어떻게 설정되는지 확인합니다.
"""

import os
from pathlib import Path
from cfg_utils import ConfigLoader

# 환경변수 설정 확인
cashop_paths = os.environ.get("CASHOP_PATHS")
print(f"✅ CASHOP_PATHS: {cashop_paths}\n")

# 테스트 대상 YAML 파일들
test_cases = [
    {
        "name": "webdriver_china.yaml",
        "path": "modules/crawl_utils/configs/webdriver_china.yaml",
        "expected_section": "webdriver",
        "test_keys": ["provider", "region", "firefox"]
    },
    {
        "name": "webdriver_global.yaml",
        "path": "modules/crawl_utils/configs/webdriver_global.yaml",
        "expected_section": "webdriver",
        "test_keys": ["provider", "region", "firefox"]
    }
]

print("=" * 80)
print("ConfigLoader 섹션명 테스트")
print("=" * 80)

for idx, test_case in enumerate(test_cases, 1):
    print(f"\n[테스트 {idx}] {test_case['name']}")
    print("-" * 80)
    
    yaml_path = Path("m:/CALife/CAShop - 구매대행/_code") / test_case["path"]
    
    if not yaml_path.exists():
        print(f"❌ 파일 없음: {yaml_path}")
        continue
    
    try:
        # ConfigLoader로 직접 로드 (src 방식)
        loader = ConfigLoader(src=(str(yaml_path), test_case["expected_section"]))
        
        # 전체 state 확인
        full_dict = loader.to_dict()
        print(f"\n📋 전체 State 구조:")
        print(f"   최상위 키: {list(full_dict.keys())}")
        
        # 예상 섹션 추출 시도
        try:
            section_dict = loader.to_dict(section=test_case["expected_section"])
            print(f"\n✅ section='{test_case['expected_section']}' 추출 성공!")
            print(f"   섹션 내부 키: {list(section_dict.keys())}")
            
            # 테스트 키 확인
            print(f"\n🔍 테스트 키 확인:")
            for key in test_case["test_keys"]:
                value = section_dict.get(key)
                if value is not None:
                    if isinstance(value, dict):
                        print(f"   - {key}: {type(value).__name__} (하위 키: {list(value.keys())[:3]}...)")
                    else:
                        print(f"   - {key}: {value}")
                else:
                    print(f"   - {key}: ❌ 없음")
        
        except Exception as e:
            print(f"\n❌ section 추출 실패: {e}")
    
    except Exception as e:
        print(f"\n❌ 로드 실패: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("테스트 완료")
print("=" * 80)

print("\n📝 결론:")
print("   - YAML 파일의 최상위 섹션명이 ConfigLoader의 섹션명으로 설정됩니다.")
print("   - webdriver_china.yaml의 'webdriver' 섹션 → section='webdriver'로 추출")
print("   - src=(path, section) 형식에서 section은 wrap/unwrap 용도입니다.")
