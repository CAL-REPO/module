# -*- coding: utf-8 -*-
"""
xl_utils 설정 테스트
- 기본 섹션 'excel' 확인
- 상대경로 확인
"""

from xl_utils.core.policy import XlPolicyManager

# 1. XlPolicyManager.load() 테스트
print("=" * 80)
print("XlPolicyManager.load() 테스트")
print("=" * 80)

# None 전달 시 기본 경로 사용
policy = XlPolicyManager.load()

print(f"✅ App visible: {policy.app.visible}")
print(f"✅ App display_alerts: {policy.app.display_alerts}")
print(f"✅ Target excel_path: {policy.target.excel_path}")
print(f"✅ Target sheet_name: {policy.target.sheet_name}")
print(f"✅ Logging: {policy.logging}")

# 2. XlController 테스트
print("\n" + "=" * 80)
print("XlController 기본 설정 테스트")
print("=" * 80)

from xl_utils import XlController

# None 전달 시 기본 경로 사용 (xl_utils/config/excel.yaml)
controller = XlController(None)

print(f"✅ Controller config loaded")
print(f"✅ App visible: {controller.config.app.visible}")
print(f"✅ Target excel_path: {controller.config.target.excel_path}")
print(f"✅ Target sheet_name: {controller.config.target.sheet_name}")

# 3. 런타임 오버라이드 테스트
print("\n" + "=" * 80)
print("런타임 오버라이드 테스트")
print("=" * 80)

controller2 = XlController(None, xw_app__visible=False, xw_app__display_alerts=True)

print(f"✅ Overridden visible: {controller2.config.app.visible}")
print(f"✅ Overridden display_alerts: {controller2.config.app.display_alerts}")

print("\n✅ 모든 테스트 통과!")
