# -*- coding: utf-8 -*-
"""ConfigLoader Section Wrapping 메커니즘 상세 분석

질문:
1. section명을 change해서 저장하는게 아니고 중첩이 발생하는가?
2. 최상위 키의 존재 여부를 확인할 수 있는 방법이 있는가?
"""

import os
from pathlib import Path
from cfg_utils import ConfigLoader

print("=" * 80)
print("ConfigLoader Section Wrapping 메커니즘 분석")
print("=" * 80)

# 테스트 YAML 파일들
test_cases = [
    {
        "name": "Case 1: Section 일치 (webdriver_china.yaml)",
        "yaml_path": "m:/CALife/CAShop - 구매대행/_code/modules/crawl_utils/configs/webdriver_china.yaml",
        "yaml_top_key": "webdriver",
        "src_section": "webdriver",
        "description": "YAML 최상위 키 = src section → 어떻게 처리되는가?"
    },
    {
        "name": "Case 2: Section 불일치 (xlcrawl_excel.yaml)",
        "yaml_path": "m:/CALife/CAShop - 구매대행/_code/configs/xlcrawl/xlcrawl_excel.yaml",
        "yaml_top_key": "xlcrawl_excel",
        "src_section": "excel",
        "description": "YAML 최상위 키 ≠ src section → 중첩 발생하는가?"
    },
    {
        "name": "Case 3: Section 일치 (xlcrawl_excel.yaml)",
        "yaml_path": "m:/CALife/CAShop - 구매대행/_code/configs/xlcrawl/xlcrawl_excel.yaml",
        "yaml_top_key": "xlcrawl_excel",
        "src_section": "xlcrawl_excel",
        "description": "YAML 최상위 키 = src section → 정상 처리되는가?"
    }
]

for idx, test in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"[{idx}] {test['name']}")
    print(f"{'='*80}")
    print(f"📝 {test['description']}")
    print(f"\n설정:")
    print(f"  - YAML 파일: {Path(test['yaml_path']).name}")
    print(f"  - YAML 최상위 키: '{test['yaml_top_key']}'")
    print(f"  - src section 지정: '{test['src_section']}'")
    
    try:
        # ConfigLoader로 로드
        loader = ConfigLoader(src=(test['yaml_path'], test['src_section']))
        
        # 전체 State 확인
        full_dict = loader.to_dict()
        print(f"\n📦 전체 State 구조:")
        print(f"  최상위 키: {list(full_dict.keys())}")
        
        # 지정한 section 추출
        section_dict = loader.to_dict(section=test['src_section'])
        section_keys = list(section_dict.keys())
        print(f"\n🔍 to_dict(section='{test['src_section']}') 결과:")
        print(f"  내부 키 (샘플): {section_keys[:5]}")
        
        # 중첩 여부 확인
        if test['yaml_top_key'] in section_dict:
            print(f"\n⚠️  중첩 발생!")
            print(f"  → section_dict['{test['yaml_top_key']}']가 존재합니다!")
            print(f"  → 실제 데이터는 {test['src_section']}.{test['yaml_top_key']}에 위치")
            
            # 중첩된 구조 확인
            nested_keys = list(section_dict[test['yaml_top_key']].keys())[:5]
            print(f"  → section_dict['{test['yaml_top_key']}'] 내부 키: {nested_keys}")
        else:
            print(f"\n✅ 중첩 없음 (정상)")
            print(f"  → section_dict에서 바로 데이터 접근 가능")
        
        # KeyPathState로 직접 확인
        state = loader.to_keypath_state()
        print(f"\n🔑 KeyPathState 확인:")
        print(f"  state.to_dict() 최상위 키: {list(state.to_dict().keys())}")
        
        # 특정 경로로 데이터 접근 테스트
        if test['yaml_top_key'] == test['src_section']:
            # 일치하는 경우
            test_path1 = f"{test['src_section']}__provider" if 'webdriver' in test['yaml_top_key'] else f"{test['src_section']}__target"
            print(f"  state.get('{test_path1}'): {state.get(test_path1, 'N/A')}")
        else:
            # 불일치하는 경우
            test_path2 = f"{test['src_section']}__{test['yaml_top_key']}__target"
            print(f"  state.get('{test_path2}'): {state.get(test_path2, 'N/A')}")
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("핵심 질문 답변")
print("=" * 80)

print("""
1️⃣ section명을 change해서 저장하는게 아니고 중첩이 발생하는가?
   → ✅ 맞습니다! section명을 변경하는 것이 아니라 "wrap"합니다.
   
   동작 방식:
   a) YAML 파일 파싱 → {'xlcrawl_excel': {...}} 
   b) src section='excel' 확인
   c) YAML에 'excel' 키가 있는가? → 없음
   d) 전체를 'excel'로 wrap → {'excel': {'xlcrawl_excel': {...}}}
   
   즉, 이름을 바꾸는 것이 아니라 한 단계 더 감싸는 것!

2️⃣ 이름이 다르더라도 최상위 키의 존재 여부를 확인할 수 있는 방법이 있는가?
   → ✅ 있습니다! 다음 테스트를 통해 확인 가능합니다:
   
   방법 1: to_dict() 결과에서 확인
   ```python
   section_dict = loader.to_dict(section="excel")
   if "xlcrawl_excel" in section_dict:
       print("중첩 발생! 실제 키는 xlcrawl_excel입니다.")
   ```
   
   방법 2: KeyPathState로 확인
   ```python
   state = loader.to_keypath_state()
   # excel__xlcrawl_excel__target 경로로 접근 가능하면 중첩됨
   if state.get("excel__xlcrawl_excel") is not None:
       print("중첩 발생!")
   ```
   
   방법 3: YAML 파일 직접 파싱
   ```python
   import yaml
   with open(yaml_path) as f:
       data = yaml.safe_load(f)
   top_keys = list(data.keys())
   print(f"YAML 최상위 키: {top_keys}")
   ```
""")

print("\n💡 해결 방안:")
print("""
Option 1: YAML 최상위 키와 section을 항상 일치시키기 (권장)
  - xlcrawl_excel.yaml의 'xlcrawl_excel' → 'excel'로 변경
  - 또는 src: [..., 'xlcrawl_excel']로 section 지정

Option 2: 중첩을 허용하고 접근 경로 조정
  - section_dict['xlcrawl_excel']로 접근
  - KeyPath: excel__xlcrawl_excel__target

Option 3: UnifiedSource에서 자동 unwrap 로직 추가
  - src section과 YAML 최상위 키가 다르면
  - YAML 최상위 키가 1개일 때 자동으로 해당 키를 section으로 사용
""")
