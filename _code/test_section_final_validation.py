# -*- coding: utf-8 -*-
"""ConfigLoader 섹션명 최종 검증 테스트

YAML 파일 최상위 키 vs config_loader의 section 지정 비교
"""

import os
from pathlib import Path
from cfg_utils import ConfigLoader

print("=" * 80)
print("ConfigLoader 섹션명 최종 검증")
print("=" * 80)

print("\n📚 이론:")
print("   1. YAML 파일 직접 로드: src=(path, section)")
print("      → section은 YAML 내부에서 추출할 키 OR wrap할 키")
print("   2. YAML 최상위 키 = 'webdriver' → section='webdriver'로 추출")
print("   3. config_loader의 src: [path, 'custom'] → section='custom'으로 강제 wrap")

print("\n" + "=" * 80)
print("실제 검증")
print("=" * 80)

# 테스트 1: webdriver_china.yaml 직접 로드
print("\n[테스트 1] webdriver_china.yaml 직접 로드")
print("-" * 80)
print("YAML 최상위 키: webdriver")
print("src=(path, 'webdriver')")

webdriver_path = "m:/CALife/CAShop - 구매대행/_code/modules/crawl_utils/configs/webdriver_china.yaml"
loader1 = ConfigLoader(src=(webdriver_path, "webdriver"))
full1 = loader1.to_dict()
print(f"✅ 전체 State 최상위 키: {list(full1.keys())}")
section1 = loader1.to_dict(section="webdriver")
print(f"✅ section='webdriver' 내부 키 (샘플): {list(section1.keys())[:5]}")

# 테스트 2: xlcrawl_excel.yaml 직접 로드
print("\n[테스트 2] xlcrawl_excel.yaml 직접 로드")
print("-" * 80)
print("YAML 최상위 키: xlcrawl_excel")
print("src=(path, 'xlcrawl_excel')")

xlcrawl_excel_path = "m:/CALife/CAShop - 구매대행/_code/configs/xlcrawl/xlcrawl_excel.yaml"
loader2 = ConfigLoader(src=(xlcrawl_excel_path, "xlcrawl_excel"))
full2 = loader2.to_dict()
print(f"✅ 전체 State 최상위 키: {list(full2.keys())}")
section2 = loader2.to_dict(section="xlcrawl_excel")
print(f"✅ section='xlcrawl_excel' 내부 키 (샘플): {list(section2.keys())[:5]}")

# 테스트 3: xlcrawl_excel.yaml을 'excel' 섹션으로 wrap
print("\n[테스트 3] xlcrawl_excel.yaml을 'excel' 섹션으로 강제 wrap")
print("-" * 80)
print("YAML 최상위 키: xlcrawl_excel")
print("src=(path, 'excel')  ← 'excel'로 강제 wrap 시도")

loader3 = ConfigLoader(src=(xlcrawl_excel_path, "excel"))
full3 = loader3.to_dict()
print(f"✅ 전체 State 최상위 키: {list(full3.keys())}")

try:
    section3 = loader3.to_dict(section="excel")
    print(f"✅ section='excel' 내부 키 (샘플): {list(section3.keys())[:5]}")
    
    # xlcrawl_excel이 하위에 있는지 확인
    if "xlcrawl_excel" in section3:
        print(f"   ⚠️  내부에 'xlcrawl_excel' 키가 존재!")
        print(f"   → section3['xlcrawl_excel'] 키: {list(section3['xlcrawl_excel'].keys())[:5]}")
except Exception as e:
    print(f"❌ section='excel' 추출 실패: {e}")

print("\n" + "=" * 80)
print("핵심 결론")
print("=" * 80)

print("""
1. ✅ YAML 파일의 최상위 섹션명이 기본 섹션명입니다
   - webdriver_china.yaml의 'webdriver' → section='webdriver'
   - xlcrawl_excel.yaml의 'xlcrawl_excel' → section='xlcrawl_excel'

2. ✅ src=(path, section)의 section은 다음과 같이 동작합니다:
   
   a) YAML에 해당 section이 존재하는 경우:
      - YAML에서 해당 section만 추출 후 최상위로 올림
      - 예: xlcrawl_excel.yaml에 'xlcrawl_excel' 키가 있으면
           src=(path, 'xlcrawl_excel') → {'xlcrawl_excel': {...}}
   
   b) YAML에 해당 section이 없는 경우:
      - YAML 전체를 해당 section으로 wrap
      - 예: xlcrawl_excel.yaml에 'excel' 키가 없으면
           src=(path, 'excel') → {'excel': {'xlcrawl_excel': {...}}}

3. ⚠️ config_loader_xlcrawl.yaml의 문제:
   - src: [xlcrawl_excel.yaml, 'excel']로 지정
   - xlcrawl_excel.yaml의 최상위 키는 'xlcrawl_excel'
   - 'excel' 키가 없으므로 wrap됨: {'excel': {'xlcrawl_excel': {...}}}
   - 실제 데이터는 excel.xlcrawl_excel에 위치!

4. ✅ 올바른 사용법:
   - Option 1: YAML 최상위 키를 변경
     xlcrawl_excel.yaml의 'xlcrawl_excel' → 'excel'로 변경
   
   - Option 2: config_loader에서 section 수정
     src: [xlcrawl_excel.yaml, 'xlcrawl_excel']로 변경
   
   - Option 3: section 없이 로드 후 rename
     src: [xlcrawl_excel.yaml]만 지정 (section 생략)
""")
