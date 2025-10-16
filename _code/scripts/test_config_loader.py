"""ConfigLoader source_paths 디버그"""
from pathlib import Path
from modules.cfg_utils.services.config_loader import ConfigLoader

# config_loader_image.yaml 경로
config_loader_path = Path("M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_image.yaml")

print("="*80)
print("ConfigLoader 디버그")
print("="*80)

# ConfigLoader 생성
loader = ConfigLoader(
    cfg_like={},
    policy_overrides={"config_loader_path": str(config_loader_path)}
)

print(f"\nPolicy yaml.source_paths: {loader.policy.yaml.source_paths}")
print(f"Policy yaml.enable_placeholder: {loader.policy.yaml.enable_placeholder}")
print(f"Policy yaml.enable_reference: {loader.policy.yaml.enable_reference}")

# 내부 데이터 확인
print(f"\nInternal data: {loader._data.data}")
