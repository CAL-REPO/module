# -*- coding: utf-8 -*-
"""Test ConfigLoader section extraction."""

import os
from cfg_utils.service.loader import ConfigLoader
from logs_utils.core.policy import LogPolicy
from logs_utils.services.manager import LogManager

print("=" * 70)
print("Test ConfigLoader Section Extraction")
print("=" * 70)

# OS 환경변수 설정
os.environ["CASHOP_PATHS"] = "M:/CALife/CAShop - 구매대행/_code/configs/paths.local.yaml"

# ConfigLoader 생성
CfgLoader = ConfigLoader(
    config_loader_cfg_path="M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_oto.yaml",
    env_os=["CASHOP_PATHS"]
)

print("\n=== Full State ===")
full_state = CfgLoader.get_state()
print(f"State name: {full_state.name}")
print(f"Store keys: {list(full_state.store.keys())}")

print("\n=== Section: image ===")
try:
    policy_image = CfgLoader.get_state(name="image")
    print(policy_image)
except Exception as e:
    print(f"❌ Error: {e}")

print("\n=== Section: overlay ===")
try:
    policy_overlay = CfgLoader.get_state(name="overlay")
    print(policy_overlay)
except Exception as e:
    print(f"❌ Error: {e}")

print("\n=== Section: text_recognizer ===")
try:
    policy_text_recognize = CfgLoader.get_state(name="text_recognizer")
    print(policy_text_recognize)
except Exception as e:
    print(f"❌ Error: {e}")

print("\n=== Section: translate ===")
try:
    policy_translate = CfgLoader.get_state(name="translate")
    print(policy_translate)
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
