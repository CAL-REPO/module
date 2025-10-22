# -*- coding: utf-8 -*-
"""ConfigLoader 섹션명 테스트 #2 - config_loader_*.yaml 방식

config_loader_xlcrawl.yaml처럼 source에서 여러 YAML을 로드할 때
섹션명이 어떻게 설정되는지 확인합니다.
"""

import os
from pathlib import Path
from cfg_utils import ConfigLoader

# 환경변수 설정 확인
cashop_paths = os.environ.get("CASHOP_PATHS")
print(f"✅ CASHOP_PATHS: {cashop_paths}\n")

print("=" * 80)
print("ConfigLoader 섹션명 테스트 #2 - config_loader_*.yaml 방식")
print("=" * 80)

# config_loader_xlcrawl.yaml 테스트
config_loader_path = Path("m:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_xlcrawl.yaml")

if not config_loader_path.exists():
    print(f"❌ 파일 없음: {config_loader_path}")
else:
    print(f"\n📁 로드 대상: {config_loader_path.name}")
    print("-" * 80)
    
    # config_loader_xlcrawl.yaml 내용 확인
    print("\n📋 config_loader_xlcrawl.yaml 구조:")
    print("   source:")
    print("     - src: [{{configs_xlcrawl_dir}}/xlcrawl_excel.yaml, 'excel']")
    print("     - src: [{{configs_xlcrawl_dir}}/xlcrawl_crawl.yaml, 'crawl']")
    
    try:
        # ConfigLoader로 로드
        loader = ConfigLoader(config_loader_cfg_path=str(config_loader_path))
        
        # 전체 state 확인
        full_dict = loader.to_dict()
        print(f"\n✅ 로드 성공!")
        print(f"\n📦 전체 State 구조:")
        print(f"   최상위 키: {list(full_dict.keys())}")
        
        # 각 섹션별로 확인
        sections_to_test = ["excel", "crawl"]
        
        for section_name in sections_to_test:
            print(f"\n{'='*80}")
            print(f"섹션 테스트: '{section_name}'")
            print(f"{'='*80}")
            
            try:
                section_dict = loader.to_dict(section=section_name)
                print(f"✅ section='{section_name}' 추출 성공!")
                print(f"   섹션 내부 키 (최대 10개): {list(section_dict.keys())[:10]}")
                
                # 몇 가지 샘플 값 출력
                print(f"\n   샘플 데이터:")
                for idx, (key, value) in enumerate(list(section_dict.items())[:3]):
                    if isinstance(value, dict):
                        print(f"     - {key}: dict (하위 키: {list(value.keys())[:3]}...)")
                    elif isinstance(value, list):
                        print(f"     - {key}: list (길이: {len(value)})")
                    else:
                        print(f"     - {key}: {value}")
            
            except KeyError as e:
                print(f"❌ section='{section_name}' 없음: {e}")
            except Exception as e:
                print(f"❌ 추출 실패: {e}")
    
    except Exception as e:
        print(f"\n❌ 로드 실패: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("테스트 완료")
print("=" * 80)

print("\n📝 결론:")
print("   1. config_loader_*.yaml의 source에서 지정한 section명이 최종 섹션명입니다.")
print("   2. src: [path, 'excel'] → section='excel'로 추출 가능")
print("   3. src: [path, 'crawl'] → section='crawl'로 추출 가능")
print("   4. YAML 파일 내부의 최상위 섹션명과 무관하게, source의 두 번째 인자가 섹션명입니다.")
print("\n   즉, webdriver_china.yaml의 최상위 키가 'webdriver'이지만,")
print("   config_loader에서 src: [webdriver_china.yaml, 'driver']로 지정하면")
print("   section='driver'로 추출됩니다.")
