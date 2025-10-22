# -*- coding: utf-8 -*-
"""ConfigLoader 요구사항 vs 현재 구현 검증

요구사항:
1. 동일 구조 YAML(webdriver.yaml) + 다른 내용 → Section명으로 구분
2. YAML 최상위 Section 설정/미설정 모두 동작
3. YAML 최상위 Section == ConfigLoader Section → 동일 Section 추출
4. YAML 최상위 Section != ConfigLoader Section → Raise
5. 모듈별 Section 기본값 → ConfigLoader에서 Section 미지정 시 사용
"""

import os
from pathlib import Path
from cfg_utils import ConfigLoader

print("=" * 80)
print("ConfigLoader 요구사항 검증")
print("=" * 80)

# =============================================================================
# 요구사항 1: 동일 구조 YAML + 다른 내용 → Section명으로 구분
# =============================================================================
print("\n[요구사항 1] 동일 구조 YAML + 다른 내용 → Section명으로 구분")
print("-" * 80)

test1_files = [
    ("webdriver_china.yaml", "modules/crawl_utils/configs/webdriver_china.yaml", "china"),
    ("webdriver_global.yaml", "modules/crawl_utils/configs/webdriver_global.yaml", "global"),
]

for name, rel_path, region in test1_files:
    yaml_path = Path("m:/CALife/CAShop - 구매대행/_code") / rel_path
    if yaml_path.exists():
        loader = ConfigLoader(src=(str(yaml_path), "webdriver"))
        config = loader.to_dict(section="webdriver")
        print(f"  {name}: region='{config.get('region')}' (예상: {region})")
        if config.get('region') == region:
            print(f"    ✅ 올바르게 구분됨")
        else:
            print(f"    ❌ 구분 실패!")

# =============================================================================
# 요구사항 2: YAML 최상위 Section 설정/미설정 모두 동작
# =============================================================================
print("\n[요구사항 2] YAML 최상위 Section 설정/미설정 모두 동작")
print("-" * 80)
print("현재 동작:")

# 2-1: 최상위 Section 있음
print("\n  2-1: YAML 최상위 Section 있음 (webdriver_china.yaml)")
yaml_path = "m:/CALife/CAShop - 구매대행/_code/modules/crawl_utils/configs/webdriver_china.yaml"
try:
    loader = ConfigLoader(src=(yaml_path, "webdriver"))
    full = loader.to_dict()
    print(f"    ✅ 로드 성공: 최상위 키 = {list(full.keys())}")
except Exception as e:
    print(f"    ❌ 실패: {e}")

# 2-2: 최상위 Section 없음 (가정)
print("\n  2-2: YAML 최상위 Section 없음 (테스트용 생성 필요)")
print("    ⚠️  현재 테스트 불가 - 최상위 Section 없는 YAML 필요")

# =============================================================================
# 요구사항 3: YAML 최상위 == ConfigLoader Section → 동일 Section 추출
# =============================================================================
print("\n[요구사항 3] YAML 최상위 == ConfigLoader Section → 동일 Section 추출")
print("-" * 80)

yaml_path = "m:/CALife/CAShop - 구매대행/_code/modules/crawl_utils/configs/webdriver_china.yaml"
try:
    loader = ConfigLoader(src=(yaml_path, "webdriver"))
    full = loader.to_dict()
    section = loader.to_dict(section="webdriver")
    
    print(f"  YAML 최상위 키: webdriver")
    print(f"  ConfigLoader Section: webdriver")
    print(f"  전체 State: {list(full.keys())}")
    print(f"  Section 내부 키 (샘플): {list(section.keys())[:5]}")
    
    # 중첩 확인
    if "webdriver" in section:
        print(f"  ❌ 중첩 발생! section['webdriver']가 존재")
    else:
        print(f"  ✅ 중첩 없음 - 정상")
except Exception as e:
    print(f"  ❌ 실패: {e}")

# =============================================================================
# 요구사항 4: YAML 최상위 != ConfigLoader Section → Raise
# =============================================================================
print("\n[요구사항 4] YAML 최상위 != ConfigLoader Section → Raise")
print("-" * 80)

yaml_path = "m:/CALife/CAShop - 구매대행/_code/configs/xlcrawl/xlcrawl_excel.yaml"
try:
    # xlcrawl_excel.yaml의 최상위 키는 'xlcrawl_excel'
    # ConfigLoader Section은 'excel'로 지정 → 불일치
    loader = ConfigLoader(src=(yaml_path, "excel"))
    full = loader.to_dict()
    section = loader.to_dict(section="excel")
    
    print(f"  YAML 최상위 키: xlcrawl_excel")
    print(f"  ConfigLoader Section: excel")
    print(f"  전체 State: {list(full.keys())}")
    print(f"  Section 내부 키: {list(section.keys())[:5]}")
    
    # 중첩 확인
    if "xlcrawl_excel" in section:
        print(f"  ❌ 현재: 중첩 발생 (Wrap됨) - Raise 안 됨!")
        print(f"  ⚠️  요구사항: Raise해야 함!")
    else:
        print(f"  ✅ Raise됨 (또는 정상 처리)")
except Exception as e:
    print(f"  ✅ Raise됨: {e}")

# =============================================================================
# 요구사항 5: 모듈별 Section 기본값 → ConfigLoader에서 미지정 시 사용
# =============================================================================
print("\n[요구사항 5] 모듈별 Section 기본값 → ConfigLoader에서 미지정 시 사용")
print("-" * 80)

# ConfigLoader에서 section 미지정
yaml_path = "m:/CALife/CAShop - 구매대행/_code/modules/crawl_utils/configs/webdriver_china.yaml"
try:
    # Section 없이 로드
    loader = ConfigLoader(src=yaml_path)
    full = loader.to_dict()
    
    print(f"  YAML 파일: webdriver_china.yaml")
    print(f"  ConfigLoader src: (yaml_path)  ← Section 미지정")
    print(f"  전체 State: {list(full.keys())}")
    
    # 모듈 기본값으로 추출 시도
    print(f"\n  모듈 기본값 'webdriver'로 추출 시도:")
    try:
        section = loader.to_dict(section="webdriver")
        print(f"    ✅ 성공: {list(section.keys())[:5]}")
    except Exception as e:
        print(f"    ❌ 실패: {e}")
    
except Exception as e:
    print(f"  ❌ 로드 실패: {e}")

print("\n" + "=" * 80)
print("검증 결과 요약")
print("=" * 80)

print("""
┌─────────────────────────────────────────────────────────────────────────┐
│ 요구사항                     │ 현재 상태 │ 문제점                         │
├─────────────────────────────────────────────────────────────────────────┤
│ 1. 동일 구조 YAML 구분       │ ✅ 정상   │ region 필드로 구분 가능        │
│ 2. 최상위 Section 설정/미설정│ ⚠️  부분  │ 최상위 없는 YAML 테스트 필요   │
│ 3. 최상위 == Section → 추출  │ ✅ 정상   │ 중첩 없이 정상 추출됨          │
│ 4. 최상위 != Section → Raise │ ❌ 실패   │ Wrap만 하고 Raise 안 함!       │
│ 5. 모듈 Section 기본값 사용  │ ⚠️  부분  │ 기본값 개념이 구현 안 됨       │
└─────────────────────────────────────────────────────────────────────────┘

🔥 핵심 문제점:

1. 요구사항 4 위반:
   - 현재: YAML 최상위 != ConfigLoader Section → Wrap (중첩)
   - 요구사항: YAML 최상위 != ConfigLoader Section → Raise!
   
   예시:
   - YAML 최상위: 'xlcrawl_excel'
   - ConfigLoader: section='excel'
   - 현재 동작: {'excel': {'xlcrawl_excel': {...}}}  ← Wrap
   - 요구 동작: ValueError("Section mismatch!")      ← Raise

2. 요구사항 5 미구현:
   - 모듈별 Section 기본값 개념이 없음
   - ConfigLoader에서 section 미지정 시 YAML 최상위 키 사용
   - 모듈이 원하는 기본 section과 다를 수 있음
   
   예시:
   - 모듈 기본값: 'webdriver'
   - YAML 최상위: 'webdriver'
   - ConfigLoader: src=(path)  ← section 미지정
   - 현재 동작: {'webdriver': {...}}  ← YAML 최상위 키 사용
   - 요구 동작: 모듈 기본값으로 자동 매핑?

3. 요구사항 2 불명확:
   - "YAML 최상위 Section 미설정"의 의미?
   - Option A: YAML에 Section 키가 없음 (flat 구조)
   - Option B: ConfigLoader에서 section 지정 안 함
""")

print("\n💡 해결 방안:")
print("""
1. UnifiedSource._extract_yaml() 수정:
   - YAML 최상위 키 != section 지정 → ValueError Raise
   - section이 None이면 YAML 최상위 키를 자동 사용
   
2. 모듈별 기본 Section 정책 추가:
   - WebDriverPolicy.default_section = "webdriver"
   - ImagePolicy.default_section = "image"
   - ConfigLoader에서 section 미지정 시 Policy 기본값 사용
   
3. Section 검증 로직 강화:
   - YAML 파싱 후 최상위 키 확인
   - section 지정과 비교하여 불일치 시 Raise
   - section 미지정 시 모듈 기본값 또는 YAML 최상위 키 사용
""")
