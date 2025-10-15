# -*- coding: utf-8 -*-
"""Test FSO integration in image_utils policies."""

import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from image_utils.core.policy import ImageSavePolicy, ImageMetaPolicy
from fso_utils import FSONamePolicy, FSOOpsPolicy


def test_fso_integration():
    """Test that ImageSavePolicy and ImageMetaPolicy use FSO."""
    
    print("=" * 70)
    print("Testing FSO Integration in image_utils Policies")
    print("=" * 70)
    
    # Test 1: ImageSavePolicy default values
    print("\n1. ImageSavePolicy default values:")
    save_policy = ImageSavePolicy()
    print(f"   save_copy: {save_policy.save_copy}")
    print(f"   directory: {save_policy.directory}")
    print(f"   name type: {type(save_policy.name)}")
    print(f"   name.suffix: {save_policy.name.suffix}")
    print(f"   name.tail_mode: {save_policy.name.tail_mode}")
    print(f"   name.ensure_unique: {save_policy.name.ensure_unique}")
    print(f"   ops type: {type(save_policy.ops)}")
    print(f"   format: {save_policy.format}")
    print(f"   quality: {save_policy.quality}")
    
    assert isinstance(save_policy.name, FSONamePolicy), "name should be FSONamePolicy"
    assert isinstance(save_policy.ops, FSOOpsPolicy), "ops should be FSOOpsPolicy"
    assert save_policy.name.suffix == "_processed", "default suffix should be _processed"
    assert save_policy.name.ensure_unique == True, "ensure_unique should be True"
    print("   ✅ All checks passed!")
    
    # Test 2: ImageMetaPolicy default values
    print("\n2. ImageMetaPolicy default values:")
    meta_policy = ImageMetaPolicy()
    print(f"   save_meta: {meta_policy.save_meta}")
    print(f"   directory: {meta_policy.directory}")
    print(f"   name type: {type(meta_policy.name)}")
    print(f"   name.suffix: {meta_policy.name.suffix}")
    print(f"   name.extension: {meta_policy.name.extension}")
    print(f"   name.ensure_unique: {meta_policy.name.ensure_unique}")
    print(f"   ops type: {type(meta_policy.ops)}")
    
    assert isinstance(meta_policy.name, FSONamePolicy), "name should be FSONamePolicy"
    assert isinstance(meta_policy.ops, FSOOpsPolicy), "ops should be FSOOpsPolicy"
    assert meta_policy.name.suffix == "_meta", "default suffix should be _meta"
    assert meta_policy.name.extension == ".json", "default extension should be .json"
    print("   ✅ All checks passed!")
    
    # Test 3: Custom FSO name policy
    print("\n3. Custom FSO name policy:")
    custom_name = FSONamePolicy(
        as_type="file",
        prefix="img",
        suffix="_custom",
        tail_mode="datetime",
        ensure_unique=False,
    )
    custom_save_policy = ImageSavePolicy(name=custom_name)
    print(f"   name.prefix: {custom_save_policy.name.prefix}")
    print(f"   name.suffix: {custom_save_policy.name.suffix}")
    print(f"   name.tail_mode: {custom_save_policy.name.tail_mode}")
    print(f"   name.ensure_unique: {custom_save_policy.name.ensure_unique}")
    
    assert custom_save_policy.name.prefix == "img", "prefix should be 'img'"
    assert custom_save_policy.name.suffix == "_custom", "suffix should be '_custom'"
    assert custom_save_policy.name.tail_mode == "datetime", "tail_mode should be 'datetime'"
    print("   ✅ All checks passed!")
    
    # Test 4: Dict construction (YAML compatibility)
    print("\n4. Dict construction (YAML compatibility):")
    config_dict = {
        "save_copy": True,
        "directory": None,
        "name": {
            "as_type": "file",
            "suffix": "_yaml_test",
            "tail_mode": "counter",
            "ensure_unique": True,
        },
        "ops": {
            "as_type": "file",
            "exist": {"create_if_missing": True},
        },
        "format": "jpg",
        "quality": 90,
    }
    
    yaml_policy = ImageSavePolicy(**config_dict)
    print(f"   name.suffix: {yaml_policy.name.suffix}")
    print(f"   name.tail_mode: {yaml_policy.name.tail_mode}")
    print(f"   format: {yaml_policy.format}")
    print(f"   quality: {yaml_policy.quality}")
    
    assert yaml_policy.name.suffix == "_yaml_test", "suffix from dict should work"
    assert yaml_policy.format == "jpg", "format from dict should work"
    print("   ✅ All checks passed!")
    
    print("\n" + "=" * 70)
    print("✅ All FSO integration tests passed!")
    print("=" * 70)


if __name__ == "__main__":
    test_fso_integration()
