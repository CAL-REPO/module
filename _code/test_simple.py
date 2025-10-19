# -*- coding: utf-8 -*-
"""간단한 ConfigLoader 테스트"""

from cfg_utils import ConfigLoader
from logs_utils.core.policy import LogPolicy
from logs_utils.services.manager import LogManager

# LogPolicy의 기본 section 이름 사용
SECTION_NAME = LogPolicy().name  # "default"

print("=" * 60)
print(f"테스트 1: src=(LogPolicy(), '{SECTION_NAME}')")
print("=" * 60)
try:
    CfgLoader = ConfigLoader(src=(LogPolicy(), SECTION_NAME))
    state = CfgLoader.get_state()
    print("전체 state:", state.to_dict())
    
    log_policy_dict = CfgLoader.get_state(name=SECTION_NAME)
    print(f"\n{SECTION_NAME} section:", log_policy_dict)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
print()

print("=" * 60)
print("테스트 2: config_loader_cfg_path (YAML에서 src 추출)")
print("=" * 60)
try:
    CfgLoader = ConfigLoader(
        config_loader_cfg_path="M:/CALife/CAShop - 구매대행/_code/modules/logs_utils/configs/config_loader_log.yaml"
    )
    state = CfgLoader.get_state()
    print("전체 state:", state.to_dict())
    
    if state.to_dict():
        log_policy_dict = CfgLoader.get_state(name=SECTION_NAME)
        print(f"\n{SECTION_NAME} section:", log_policy_dict)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()


