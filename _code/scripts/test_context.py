"""ConfigLoader source_paths context 전달 테스트"""
from pathlib import Path
import os
from modules.cfg_utils.services.config_loader import ConfigLoader

# 1. paths.local.yaml 로드
paths_yaml = Path(os.getenv("CASHOP_PATHS"))
paths_dict = ConfigLoader.load(paths_yaml)

print("paths_dict configs_dir:", paths_dict.get("configs_dir"))

# 2. config_loader_image.yaml 경로
config_loader_path = Path("M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_image.yaml")

print("\n" + "="*80)
print("ConfigLoader with context")
print("="*80)

# 3. ConfigLoader 생성 - context 전달하기
from modules.structured_io.core.base_policy import BaseParserPolicy
from modules.cfg_utils.core.policy import ConfigPolicy

# policy_overrides에 yaml.context를 추가할 수 있을까?
loader = ConfigLoader(
    cfg_like={},
    policy_overrides={
        "config_loader_path": str(config_loader_path),
        # "yaml.context": paths_dict,  # 이게 가능한지 테스트
    }
)

print(f"\nPolicy yaml.source_paths: {loader.policy.yaml.source_paths}")
print(f"Internal data keys: {list(loader._data.data.keys())}")
if loader._data.data:
    print(f"source field: {loader._data.data.get('source')}")
