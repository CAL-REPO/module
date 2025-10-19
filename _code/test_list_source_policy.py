# -*- coding: utf-8 -*-
"""List[SourcePolicy] 처리 테스트."""

import sys
from pathlib import Path

# PYTHONPATH 설정
code_dir = Path(__file__).parent
modules_dir = code_dir / "modules"
sys.path.insert(0, str(modules_dir))

from cfg_utils import ConfigLoader


def test_list_source_policy():
    """config_loader_oto.yaml의 List[SourcePolicy] 처리 테스트."""
    
    print("=" * 80)
    print("List[SourcePolicy] 처리 테스트")
    print("=" * 80)
    
    # ConfigLoader 생성 (config_loader_cfg_path 사용)
    loader = ConfigLoader(
        config_loader_cfg_path=code_dir / "configs" / "loader" / "config_loader_oto.yaml",
        env_os=["CASHOP_PATHS"]  # CASHOP_PATHS만 로드 (paths.local.yaml)
    )
    
    # 정책 확인
    print("\n[1] PolicyLoader 결과 확인:")
    print(f"source_policy 타입: {type(loader._source_policy)}")
    
    if isinstance(loader._source_policy, list):
        print(f"SourcePolicy 개수: {len(loader._source_policy)}")
        for idx, sp in enumerate(loader._source_policy):
            print(f"\n  [{idx}] src: {sp.src}")
            print(f"      yaml_parser.enable_reference: {sp.yaml_parser.enable_reference if sp.yaml_parser else None}")
            print(f"      yaml_normalizer.resolve_vars: {sp.yaml_normalizer.resolve_vars if sp.yaml_normalizer else None}")
    else:
        print(f"단일 SourcePolicy: {loader._source_policy.src if hasattr(loader._source_policy, 'src') else 'N/A'}")
    
    # State 확인
    print("\n[2] Config.state 확인:")
    try:
        state = loader.get_state()
        
        print(f"✅ Load 성공!")
        print(f"State keys: {list(state.to_dict().keys())}")
        
        # 각 section 확인
        for section in ["image", "overlay", "text_recognizer", "translate"]:
            section_data = state.to_dict().get(section)
            if section_data:
                print(f"\n  [{section}] 섹션 로드 성공")
                if isinstance(section_data, dict):
                    keys = list(section_data.keys())
                    print(f"    Keys ({len(keys)}개): {keys[:5]}...")  # 처음 5개만
            else:
                print(f"\n  [{section}] 섹션 없음 ❌")
        
    except Exception as e:
        print(f"❌ Load 실패: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    test_list_source_policy()
