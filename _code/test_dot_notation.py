# -*- coding: utf-8 -*-
"""Test dot notation in ${} vs __"""

from keypath_utils import KeyPathDict

# Test: ${} 안에서 dot notation 사용 가능한지?
data = {
    "env": {
        "CASHOP_PATHS": {
            "configs_oto_dir": "M:/test/configs/oto"
        }
    },
    # Case 1: __ 사용 (현재 KeyPath 방식)
    "path1": "${env__CASHOP_PATHS__configs_oto_dir}/image.yaml",
    # Case 2: dot 사용 (사용자가 쓰고 싶은 방식?)
    "path2": "${env.CASHOP_PATHS.configs_oto_dir}/image.yaml"
}

print("=" * 70)
print("Test: Dot vs Underscore in ${keypath}")
print("=" * 70)

kpd = KeyPathDict(data=data)
print(f"Before path1: {data['path1']}")
print(f"Before path2: {data['path2']}")

resolved = kpd.resolve_all()
print(f"\nAfter path1 (__): {resolved.data['path1']}")
print(f"After path2 (.):  {resolved.data['path2']}")
