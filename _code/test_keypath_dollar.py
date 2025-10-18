# -*- coding: utf-8 -*-
"""Test ${keypath} resolution"""

from keypath_utils import KeyPathDict

# Test: ${keypath} 직접 사용
data = {
    "env": {
        "CASHOP_PATHS": {
            "configs_oto_dir": "M:/test/configs/oto"
        }
    },
    "test_path": "${env__CASHOP_PATHS__configs_oto_dir}/image.yaml"
}

print("=" * 70)
print("Test: ${keypath} Resolution")
print("=" * 70)

kpd = KeyPathDict(data=data)
print(f"Before: {data['test_path']}")

resolved = kpd.resolve_all()
print(f"After:  {resolved.data['test_path']}")

# Test 2: Multiple levels
data2 = {
    "base": "M:/CALife/CAShop",
    "code_dir": "${base}/_code",
    "configs_dir": "${code_dir}/configs",
    "image_path": "${configs_dir}/oto/image.yaml"
}

print("\n" + "=" * 70)
print("Test: Multi-level Resolution")
print("=" * 70)

kpd2 = KeyPathDict(data=data2)
print(f"Before: {data2['image_path']}")

resolved2 = kpd2.resolve_all()
print(f"After:  {resolved2.data['image_path']}")
