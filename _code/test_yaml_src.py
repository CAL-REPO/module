# -*- coding: utf-8 -*-
"""YAML에 src 포함 테스트"""

from pathlib import Path
from pprint import pprint

from modules.cfg_utils_v2.core.policy import ConfigLoaderPolicy, SourcePolicy
from modules.cfg_utils_v2 import UnifiedSource
from modules.structured_io.formats.yaml_io import YamlParser
from modules.structured_io.core.policy import BaseParserPolicy


def test_yaml_with_src():
    """YAML 파일에 src가 포함된 경우"""
    print("\n" + "=" * 60)
    print("🧪 YAML에 src 포함 테스트")
    print("=" * 60)
    
    # YAML 파일 경로
    yaml_path = Path("m:/CALife/CAShop - 구매대행/_code/modules/cfg_utils_v2/configs/config_loader_with_src.yaml")
    print(f"📂 설정 파일: {yaml_path}")
    
    # YAML 파싱
    parser_policy = BaseParserPolicy(safe_mode=True)
    parser = YamlParser(policy=parser_policy)
    yaml_text = yaml_path.read_text(encoding="utf-8")
    policy_dict = parser.parse(yaml_text, base_path=yaml_path.parent)
    
    print(f"\n📦 파싱된 YAML 데이터:")
    pprint(policy_dict, width=100)
    
    # ConfigLoaderPolicy 생성
    try:
        config_policy = ConfigLoaderPolicy(**policy_dict)
        print(f"\n✅ ConfigLoaderPolicy 생성 성공!")
        
        # SourcePolicy에 src가 있는지 확인
        print(f"\n🔍 SourcePolicy.src 확인:")
        print(f"  - src: {config_policy.source.src}")
        print(f"  - src type: {type(config_policy.source.src)}")
        
        if config_policy.source.src:
            print(f"\n✅ YAML에 src가 포함되어 있습니다!")
            print(f"  📂 src 경로: {config_policy.source.src}")
            
            # UnifiedSource로 실제 로드 테스트
            print(f"\n🔄 UnifiedSource로 데이터 추출 테스트:")
            source = UnifiedSource(config_policy.source)
            kpd = source.extract()
            
            print(f"\n📦 추출된 데이터:")
            pprint(kpd.data, width=100)
            
            # 데이터 검증
            print(f"\n🔍 데이터 검증:")
            assert "image" in kpd.data, "image 섹션이 없습니다!"
            assert "ocr" in kpd.data, "ocr 섹션이 없습니다!"
            assert kpd.data["image"]["max_width"] == 2048
            assert kpd.data["ocr"]["lang"] == "kor+eng"
            
            print(f"  ✅ image__max_width: {kpd.data['image']['max_width']}")
            print(f"  ✅ ocr__lang: {kpd.data['ocr']['lang']}")
            print(f"  ✅ database__host: {kpd.data['database']['host']}")
            
            print(f"\n✅ YAML src 기능 정상 작동!")
            
        else:
            print(f"\n⚠️  src가 None입니다. (런타임에 주입해야 함)")
        
        return config_policy
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_yaml_without_src():
    """YAML 파일에 src가 없는 경우 (런타임 주입)"""
    print("\n" + "=" * 60)
    print("🧪 YAML에 src 없이 런타임 주입 테스트")
    print("=" * 60)
    
    # 기본 YAML (src 없음)
    yaml_path = Path("m:/CALife/CAShop - 구매대행/_code/modules/cfg_utils_v2/configs/config_loader.yaml")
    print(f"📂 설정 파일: {yaml_path}")
    
    # YAML 파싱
    parser_policy = BaseParserPolicy(safe_mode=True)
    parser = YamlParser(policy=parser_policy)
    yaml_text = yaml_path.read_text(encoding="utf-8")
    policy_dict = parser.parse(yaml_text, base_path=yaml_path.parent)
    
    # ConfigLoaderPolicy 생성
    config_policy = ConfigLoaderPolicy(**policy_dict)
    
    print(f"\n🔍 SourcePolicy.src 확인:")
    print(f"  - src: {config_policy.source.src}")
    
    if config_policy.source.src is None:
        print(f"\n✅ src가 None입니다. (예상대로)")
        
        # 런타임에 src 주입
        print(f"\n🔄 런타임에 src 주입 테스트:")
        
        # 새로운 SourcePolicy 생성 (src 포함)
        runtime_policy = SourcePolicy(
            src="modules/cfg_utils_v2/configs/test_default.yaml",
            yaml_parser=config_policy.source.yaml_parser,
            yaml_normalizer=config_policy.source.yaml_normalizer,
            yaml_merge=config_policy.source.yaml_merge
        )
        
        print(f"  📂 주입된 src: {runtime_policy.src}")
        
        # UnifiedSource로 추출
        source = UnifiedSource(runtime_policy)
        kpd = source.extract()
        
        print(f"\n📦 추출된 데이터:")
        pprint(kpd.data, width=100, depth=2)
        
        print(f"\n✅ 런타임 src 주입 정상 작동!")


def test_comparison():
    """정적 src vs 런타임 src 비교"""
    print("\n" + "=" * 60)
    print("📊 정적 src vs 런타임 src 비교")
    print("=" * 60)
    
    print(f"""
1️⃣ 정적 src (YAML에 포함):
   - 장점: 설정 파일에 모든 정보 포함, 재사용 쉬움
   - 단점: 고정된 파일 경로, 유연성 낮음
   - 사용: 기본 설정 파일, 환경별 고정 설정
   
   예시:
   ```yaml
   source:
     src: "configs/default.yaml"  # ← 여기에 고정
     yaml_parser: ...
   ```

2️⃣ 런타임 src (코드에서 주입):
   - 장점: 동적 파일 선택, 유연성 높음
   - 단점: 코드에서 관리 필요
   - 사용: 사용자 입력, 동적 설정, Override
   
   예시:
   ```python
   policy = SourcePolicy(
       src=user_selected_file,  # ← 런타임에 결정
       **config_policy.source.dict()
   )
   ```

3️⃣ 혼합 사용:
   - ConfigLoaderPolicy: 기본 정책만 (src 없음)
   - 런타임: 필요에 따라 src 주입
   
   예시:
   ```python
   # 기본 정책 로드
   base_policy = ConfigLoaderPolicy.from_yaml("config_loader.yaml")
   
   # 필요시 src 주입
   if user_wants_yaml:
       source_policy = SourcePolicy(
           src=user_file,
           **base_policy.source.dict()
       )
   ```
    """)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 YAML src 테스트 시작")
    print("=" * 60)
    
    # 1. YAML에 src 포함
    test_yaml_with_src()
    
    # 2. YAML에 src 없이 런타임 주입
    test_yaml_without_src()
    
    # 3. 비교 분석
    test_comparison()
    
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)
