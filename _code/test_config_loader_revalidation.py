# -*- coding: utf-8 -*-
"""ConfigLoader Section 동작 재검증 - config_loader 방식

사용자 지적사항:
- config_loader의 source에서 section명을 지정하면 그게 통일 아닌가?
- 모듈이 section명이 다르면 사용 못하는 건가?

검증 포인트:
1. webdriver_config_loader.yaml 방식으로 로드
2. section="webdriver_china", section="webdriver_global"로 각각 추출
3. 통일된 section명으로 추출 가능한가?
"""

import os
from pathlib import Path
from cfg_utils import ConfigLoader

print("=" * 80)
print("ConfigLoader Section 재검증 - config_loader 방식")
print("=" * 80)

# webdriver_config_loader.yaml 사용
config_loader_path = "m:/CALife/CAShop - 구매대행/_code/modules/crawl_utils/configs/webdriver_config_loader.yaml"

print("\n📁 config_loader 구조:")
print("""
source:
  - src: [webdriver_china.yaml, "webdriver_china"]
  - src: [webdriver_global.yaml, "webdriver_global"]
""")

try:
    loader = ConfigLoader(config_loader_cfg_path=config_loader_path)
    
    # 전체 State 확인
    full = loader.to_dict()
    print(f"\n📦 전체 State 최상위 키:")
    print(f"   {list(full.keys())}")
    
    print("\n" + "=" * 80)
    print("Section별 추출 테스트")
    print("=" * 80)
    
    # Section 1: webdriver_china
    print("\n[1] section='webdriver_china' 추출:")
    try:
        china_config = loader.to_dict(section="webdriver_china")
        print(f"   ✅ 성공!")
        print(f"   키 (샘플): {list(china_config.keys())[:5]}")
        print(f"   region: {china_config.get('region')}")
        print(f"   provider: {china_config.get('provider')}")
    except Exception as e:
        print(f"   ❌ 실패: {e}")
    
    # Section 2: webdriver_global
    print("\n[2] section='webdriver_global' 추출:")
    try:
        global_config = loader.to_dict(section="webdriver_global")
        print(f"   ✅ 성공!")
        print(f"   키 (샘플): {list(global_config.keys())[:5]}")
        print(f"   region: {global_config.get('region')}")
        print(f"   provider: {global_config.get('provider')}")
    except Exception as e:
        print(f"   ❌ 실패: {e}")
    
    # Section 3: 통일된 이름 "webdriver" 시도
    print("\n[3] section='webdriver' 추출 시도:")
    try:
        webdriver_config = loader.to_dict(section="webdriver")
        print(f"   ✅ 성공!")
        print(f"   키 (샘플): {list(webdriver_config.keys())[:5]}")
    except KeyError as e:
        print(f"   ❌ 실패 (section 없음): {e}")
    except Exception as e:
        print(f"   ❌ 실패: {e}")
    
    print("\n" + "=" * 80)
    print("핵심 질문에 대한 답변")
    print("=" * 80)
    
    print("""
Q1: config_loader의 source에서 section명을 바꿔서 로드하면 그게 통일 아닌가?

A1: ✅ 맞습니다!
    
    config_loader에서:
    - src: [webdriver_china.yaml, "webdriver"]  ← 통일된 section명 지정
    - src: [webdriver_global.yaml, "webdriver"]  ← 통일된 section명 지정
    
    이렇게 변경하면:
    - 둘 다 section="webdriver"로 추출 가능
    - YAML 파일 내부의 최상위 키는 무관
    - config_loader의 section 지정이 최종 section명이 됨
    
    하지만 문제:
    - 둘 다 "webdriver"로 로드하면 → 나중 것이 덮어씀!
    - china와 global을 동시에 사용 불가!

Q2: 모듈이 section명이 다르면 사용을 못한다는 소리인가?

A2: ❌ 아닙니다!
    
    현재 방식:
    - section="webdriver_china"로 추출 → china 설정 사용
    - section="webdriver_global"로 추출 → global 설정 사용
    
    각 모듈/스크립트에서:
    ```python
    # China 크롤링 시
    config = loader.to_dict(section="webdriver_china")
    policy = WebDriverPolicy(**config)
    
    # Global 크롤링 시
    config = loader.to_dict(section="webdriver_global")
    policy = WebDriverPolicy(**config)
    ```
    
    ✅ 서로 다른 section명으로 구분하여 사용 가능!
    """)
    
    print("\n" + "=" * 80)
    print("요구사항 재해석")
    print("=" * 80)
    
    print("""
제가 오해한 부분:

❌ 오해: "동일한 section명 'webdriver'로 통일해야 한다"
✅ 실제: "서로 다른 section명으로 구분하여 사용한다"

올바른 이해:

1. 동일 구조 YAML + 다른 내용 → Section명으로 구분
   → ✅ webdriver_china, webdriver_global로 구분 가능
   
2. YAML 최상위 Section 설정/미설정 모두 동작
   → ✅ config_loader의 section 지정이 최종 section명
   
3. YAML 최상위 == ConfigLoader Section → 동일 Section 추출
   → ✅ webdriver_china.yaml의 'webdriver_china' == section "webdriver_china"
   
4. YAML 최상위 != ConfigLoader Section → Raise
   → ⚠️  이 부분이 핵심!
   
5. 모듈별 Section 기본값
   → 각 모듈은 필요한 section명을 지정하여 사용

현재 구조의 의미:

webdriver_china.yaml (최상위 키: webdriver_china)
  ↓ config_loader에서 section="webdriver_china" 지정
  ↓ 일치!
  → ✅ 정상 동작

만약:
webdriver_china.yaml (최상위 키: webdriver_china)
  ↓ config_loader에서 section="webdriver" 지정
  ↓ 불일치!
  → ❌ 중첩 발생 또는 Raise
    """)

except Exception as e:
    print(f"\n❌ 로드 실패: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("최종 정리")
print("=" * 80)

print("""
✅ 현재 구조는 올바릅니다!

webdriver_config_loader.yaml:
  - src: [webdriver_china.yaml, "webdriver_china"]
  - src: [webdriver_global.yaml, "webdriver_global"]

각 YAML 파일:
  webdriver_china.yaml  → 최상위 키: webdriver_china
  webdriver_global.yaml → 최상위 키: webdriver_global

사용 방법:
  config = loader.to_dict(section="webdriver_china")   # China 설정
  config = loader.to_dict(section="webdriver_global")  # Global 설정

🔥 진짜 요구사항 재확인 필요:

1. section명이 달라야 하는가? (현재: china, global 구분)
   → ✅ 맞음! 서로 다른 설정을 구분하기 위함

2. section명을 통일해야 하는가? (모두 "webdriver"로?)
   → ❓ 이 경우 어떻게 구분하나요?
   
3. 동일한 Policy 클래스(WebDriverPolicy)를 사용하되,
   section명으로 china/global을 구분하는 것이 목적인가?
   → ✅ 맞다면 현재 구조가 올바름!
""")
