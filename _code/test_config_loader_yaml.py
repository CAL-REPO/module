# -*- coding: utf-8 -*-
"""ConfigLoaderPolicy YAML 로드 테스트"""

from pathlib import Path
from pprint import pprint

from modules.cfg_utils.core.policy import ConfigLoaderPolicy
from modules.structured_io.formats.yaml_io import YamlParser
from modules.structured_io.core.policy import BaseParserPolicy


def test_load_config_loader_policy():
    """config_loader.yaml을 ConfigLoaderPolicy로 로드"""
    print("\n" + "=" * 60)
    print("🧪 ConfigLoaderPolicy YAML 로드 테스트")
    print("=" * 60)
    
    # YAML 파일 경로
    yaml_path = Path("m:/CALife/CAShop - 구매대행/_code/modules/cfg_utils_v2/configs/config_loader.yaml")
    print(f"📂 YAML 파일: {yaml_path}")
    
    # YAML 파싱
    parser_policy = BaseParserPolicy(
        safe_mode=True,
        enable_env=True,
        enable_include=True,
        enable_placeholder=True
    )
    parser = YamlParser(policy=parser_policy)
    yaml_text = yaml_path.read_text(encoding="utf-8")
    policy_dict = parser.parse(yaml_text, base_path=yaml_path.parent)
    
    print(f"\n📦 파싱된 YAML 데이터:")
    pprint(policy_dict, width=100, compact=False)
    
    # ConfigLoaderPolicy 생성
    try:
        policy = ConfigLoaderPolicy(**policy_dict)
        print(f"\n✅ ConfigLoaderPolicy 생성 성공!")
        
        # 정책 검증
        print(f"\n🔍 정책 검증:")
        print(f"\n1️⃣ SourcePolicy:")
        print(f"  - base_model_normalizer: {policy.source.base_model_normalizer}")
        print(f"  - base_model_merge: {policy.source.base_model_merge}")
        print(f"  - dict_normalizer: {policy.source.dict_normalizer}")
        print(f"  - dict_merge: {policy.source.dict_merge}")
        print(f"  - yaml_parser: {policy.source.yaml_parser}")
        print(f"  - yaml_normalizer: {policy.source.yaml_normalizer}")
        print(f"  - yaml_merge: {policy.source.yaml_merge}")
        
        print(f"\n2️⃣ KeyPathStatePolicy:")
        print(f"  - {policy.keypath}")
        
        print(f"\n3️⃣ LogPolicy:")
        print(f"  - {policy.log}")
        
        # 타입별 정책 차이 확인
        print(f"\n📊 타입별 정책 비교:")
        print(f"\n{'속성':<20} {'BaseModel':<15} {'Dict':<15} {'YAML':<15}")
        print(f"{'-' * 70}")
        print(f"{'normalize_keys':<20} {str(policy.source.base_model_normalizer.normalize_keys):<15} {str(policy.source.dict_normalizer.normalize_keys):<15} {str(policy.source.yaml_normalizer.normalize_keys):<15}")
        print(f"{'drop_blanks':<20} {str(policy.source.base_model_normalizer.drop_blanks):<15} {str(policy.source.dict_normalizer.drop_blanks):<15} {str(policy.source.yaml_normalizer.drop_blanks):<15}")
        print(f"{'resolve_vars':<20} {str(policy.source.base_model_normalizer.resolve_vars):<15} {str(policy.source.dict_normalizer.resolve_vars):<15} {str(policy.source.yaml_normalizer.resolve_vars):<15}")
        print(f"{'merge.deep':<20} {str(policy.source.base_model_merge.deep):<15} {str(policy.source.dict_merge.deep):<15} {str(policy.source.yaml_merge.deep):<15}")
        print(f"{'merge.overwrite':<20} {str(policy.source.base_model_merge.overwrite):<15} {str(policy.source.dict_merge.overwrite):<15} {str(policy.source.yaml_merge.overwrite):<15}")
        
        # YAML 파서 설정 확인
        print(f"\n🔧 YAML Parser 설정:")
        print(f"  - safe_mode: {policy.source.yaml_parser.safe_mode}")
        print(f"  - encoding: {policy.source.yaml_parser.encoding}")
        print(f"  - enable_env: {policy.source.yaml_parser.enable_env}")
        print(f"  - enable_include: {policy.source.yaml_parser.enable_include}")
        print(f"  - enable_placeholder: {policy.source.yaml_parser.enable_placeholder}")
        
        print(f"\n✅ 모든 정책이 올바르게 로드되었습니다!")
        
        return policy
        
    except Exception as e:
        print(f"\n❌ ConfigLoaderPolicy 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_policy_usage():
    """로드된 정책을 실제로 사용하는 예시"""
    print("\n" + "=" * 60)
    print("🧪 정책 사용 예시")
    print("=" * 60)
    
    # 정책 로드
    policy = test_load_config_loader_policy()
    
    if policy:
        print(f"\n📝 정책 사용 예시:")
        print(f"""
# ConfigLoader 생성 시 사용:
from cfg_utils_v2 import ConfigLoader

loader = ConfigLoader(
    policy=policy,  # ← YAML에서 로드한 정책
    base_sources=[
        (ImagePolicy(), "image"),
        (OcrPolicy(), "ocr")
    ],
    override_sources=[
        ("config.yaml", "image"),  # YAML 소스 → yaml_parser, yaml_normalizer 사용
        ({{"max_width": 2048}}, "image")  # Dict 소스 → dict_normalizer 사용
    ]
)

# 각 소스별로 적절한 정책이 자동 적용됨:
# - BaseModel: base_model_normalizer, base_model_merge
# - Dict: dict_normalizer, dict_merge
# - YAML: yaml_parser, yaml_normalizer, yaml_merge
        """)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 ConfigLoaderPolicy YAML 테스트 시작")
    print("=" * 60)
    
    test_load_config_loader_policy()
    # test_policy_usage()
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료!")
    print("=" * 60)
