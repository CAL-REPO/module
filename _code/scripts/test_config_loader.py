# -*- coding: utf-8 -*-
"""Test ConfigLoader section and root loading capabilities."""

from pathlib import Path
from modules.cfg_utils import ConfigLoader
from pillow_utils.policy import ImageLoaderPolicy, ImageOverlayPolicy

print("=" * 80)
print("ConfigLoader Section vs Root Test")
print("=" * 80)

# Test 1: Load from section-based YAML
print("\n[Test 1] Load from section-based YAML (pillow.yaml)")
try:
    config = ConfigLoader("configs/pillow.yaml")
    
    # Check if section exists
    has_pillow = config.has_section("pillow")
    print(f"  Has 'pillow' section: {has_pillow}")
    
    # Load as model (auto-detect section)
    policy = config.as_model(ImageLoaderPolicy)
    print(f"  ✅ Loaded ImageLoaderPolicy")
    print(f"  Source path: {policy.source.path}")
    print(f"  Suffix: {policy.image.suffix}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 2: Load from non-section YAML (root)
print("\n[Test 2] Load from non-section YAML (pillow_nosection.yaml)")
try:
    config = ConfigLoader("configs/pillow_nosection.yaml")
    
    # Check if section exists
    has_pillow = config.has_section("pillow")
    print(f"  Has 'pillow' section: {has_pillow}")
    
    # Load as model (should use root)
    policy = config.as_model(ImageLoaderPolicy)
    print(f"  ✅ Loaded ImageLoaderPolicy from root")
    print(f"  Source path: {policy.source.path}")
    print(f"  Suffix: {policy.image.suffix}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 3: Load overlay from section-based YAML
print("\n[Test 3] Load from section-based YAML (overlay.yaml)")
try:
    config = ConfigLoader("configs/overlay.yaml")
    
    # Check if section exists
    has_overlay = config.has_section("overlay")
    print(f"  Has 'overlay' section: {has_overlay}")
    
    # Load as model (auto-detect section)
    policy = config.as_model(ImageOverlayPolicy)
    print(f"  ✅ Loaded ImageOverlayPolicy")
    print(f"  Source path: {policy.source.path}")
    print(f"  Suffix: {policy.output.suffix}")
    print(f"  Texts count: {len(policy.texts)}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 4: Load overlay from non-section YAML (root)
print("\n[Test 4] Load from non-section YAML (overlay_nosection.yaml)")
try:
    config = ConfigLoader("configs/overlay_nosection.yaml")
    
    # Check if section exists
    has_overlay = config.has_section("overlay")
    print(f"  Has 'overlay' section: {has_overlay}")
    
    # Load as model (should use root)
    policy = config.as_model(ImageOverlayPolicy)
    print(f"  ✅ Loaded ImageOverlayPolicy from root")
    print(f"  Source path: {policy.source.path}")
    print(f"  Suffix: {policy.output.suffix}")
    print(f"  Texts count: {len(policy.texts)}")
    print(f"  First text: {policy.texts[0].text}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 5: Load from unified.yaml (multiple sections)
print("\n[Test 5] Load from unified.yaml (multiple sections)")
try:
    config = ConfigLoader("configs/unified.yaml")
    
    # Check sections
    has_pillow = config.has_section("pillow")
    has_overlay = config.has_section("overlay")
    has_ocr = config.has_section("ocr")
    print(f"  Has 'pillow' section: {has_pillow}")
    print(f"  Has 'overlay' section: {has_overlay}")
    print(f"  Has 'ocr' section: {has_ocr}")
    
    # Load pillow
    pillow_policy = config.as_model(ImageLoaderPolicy)
    print(f"  ✅ Loaded ImageLoaderPolicy from unified")
    print(f"  Suffix: {pillow_policy.image.suffix}")
    
    # Load overlay
    overlay_policy = config.as_model(ImageOverlayPolicy)
    print(f"  ✅ Loaded ImageOverlayPolicy from unified")
    print(f"  Suffix: {overlay_policy.output.suffix}")
    print(f"  Texts count: {len(overlay_policy.texts)}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Test 6: Explicit section loading
print("\n[Test 6] Explicit section loading")
try:
    config = ConfigLoader("configs/unified.yaml")
    
    # Get sections explicitly
    pillow_dict = config.get_section("pillow")
    overlay_dict = config.get_section("overlay")
    print(f"  ✅ Got 'pillow' section: {list(pillow_dict.keys())[:3]}...")
    print(f"  ✅ Got 'overlay' section: {list(overlay_dict.keys())[:3]}...")
    
    # Get root
    root_dict = config.get_root()
    print(f"  ✅ Got root sections: {list(root_dict.keys())}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "=" * 80)
print("All tests completed!")
print("=" * 80)
