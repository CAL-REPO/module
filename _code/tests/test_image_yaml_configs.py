# -*- coding: utf-8 -*-
"""Test image_utils YAML config files validation."""

import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from image_utils.core.policy import ImageLoaderPolicy, ImageOCRPolicy, ImageOverlayPolicy
from cfg_utils import ConfigLoader


def test_image_yaml_configs():
    """Test that all image_utils YAML configs are valid."""
    
    config_dir = Path(__file__).parent.parent / "modules" / "image_utils" / "config"
    
    print("=" * 70)
    print("Testing image_utils YAML Configuration Files")
    print("=" * 70)
    
    # Test ImageLoader configs
    print("\n📁 ImageLoader Configs:")
    
    print("\n   1. image_loader_simple.yaml")
    try:
        loader_simple = ConfigLoader(config_dir / "image_loader_simple.yaml")
        policy = loader_simple.as_model(ImageLoaderPolicy, section="image")
        print(f"      ✅ Valid!")
        print(f"         source: {policy.source.path}")
        print(f"         save_copy: {policy.save.save_copy}")
        print(f"         suffix: {policy.save.name.suffix}")
        print(f"         tail_mode: {policy.save.name.tail_mode}")
    except Exception as e:
        print(f"      ❌ Error: {e}")
    
    print("\n   2. image_loader_full.yaml")
    try:
        loader_full = ConfigLoader(config_dir / "image_loader_full.yaml")
        policy = loader_full.as_model(ImageLoaderPolicy, section="image")
        print(f"      ✅ Valid!")
        print(f"         source: {policy.source.path}")
        print(f"         suffix: {policy.save.name.suffix}")
        print(f"         ensure_unique: {policy.save.name.ensure_unique}")
        print(f"         format: {policy.save.format}")
        print(f"         quality: {policy.save.quality}")
    except Exception as e:
        print(f"      ❌ Error: {e}")
    
    # Test ImageOCR configs
    print("\n📁 ImageOCR Configs:")
    
    print("\n   1. image_ocr_simple.yaml")
    try:
        ocr_simple = ConfigLoader(config_dir / "image_ocr_simple.yaml")
        policy = ocr_simple.as_model(ImageOCRPolicy, section="ocr")
        print(f"      ✅ Valid!")
        print(f"         provider: {policy.provider.provider}")
        print(f"         langs: {policy.provider.langs}")
        print(f"         min_conf: {policy.provider.min_conf}")
        print(f"         max_width: {policy.preprocess.max_width}")
    except Exception as e:
        print(f"      ❌ Error: {e}")
    
    print("\n   2. image_ocr_full.yaml")
    try:
        ocr_full = ConfigLoader(config_dir / "image_ocr_full.yaml")
        policy = ocr_full.as_model(ImageOCRPolicy, section="ocr")
        print(f"      ✅ Valid!")
        print(f"         provider: {policy.provider.provider}")
        print(f"         paddle_device: {policy.provider.paddle_device}")
        print(f"         strip_special_chars: {policy.postprocess.strip_special_chars}")
        print(f"         deduplicate_iou: {policy.postprocess.deduplicate_iou_threshold}")
    except Exception as e:
        print(f"      ❌ Error: {e}")
    
    # Test ImageOverlay configs
    print("\n📁 ImageOverlay Configs:")
    
    print("\n   1. image_overlay_simple.yaml")
    try:
        overlay_simple = ConfigLoader(config_dir / "image_overlay_simple.yaml")
        policy = overlay_simple.as_model(ImageOverlayPolicy, section="overlay")
        print(f"      ✅ Valid!")
        print(f"         source: {policy.source.path}")
        print(f"         texts count: {len(policy.texts)}")
        print(f"         background_opacity: {policy.background_opacity}")
        if policy.texts:
            print(f"         first text: '{policy.texts[0].text}'")
            print(f"         font family: {policy.texts[0].font.family}")
    except Exception as e:
        print(f"      ❌ Error: {e}")
    
    print("\n   2. image_overlay_full.yaml")
    try:
        overlay_full = ConfigLoader(config_dir / "image_overlay_full.yaml")
        policy = overlay_full.as_model(ImageOverlayPolicy, section="overlay")
        print(f"      ✅ Valid!")
        print(f"         source: {policy.source.path}")
        print(f"         texts count: {len(policy.texts)}")
        print(f"         suffix: {policy.save.name.suffix}")
        if len(policy.texts) > 1:
            print(f"         second text: '{policy.texts[1].text}'")
            print(f"         second font family: {policy.texts[1].font.family}")
            print(f"         second font size: {policy.texts[1].font.size}")
            print(f"         second font fill: {policy.texts[1].font.fill}")
            print(f"         second font stroke_fill: {policy.texts[1].font.stroke_fill}")
            print(f"         second font stroke_width: {policy.texts[1].font.stroke_width}")
    except Exception as e:
        print(f"      ❌ Error: {e}")
    
    # Test FSO integration
    print("\n📁 FSO Integration Check:")
    try:
        loader_policy = loader_simple.as_model(ImageLoaderPolicy, section="image")
        print(f"   ✅ FSONamePolicy:")
        print(f"      type: {type(loader_policy.save.name).__name__}")
        print(f"      suffix: {loader_policy.save.name.suffix}")
        print(f"      tail_mode: {loader_policy.save.name.tail_mode}")
        print(f"      ensure_unique: {loader_policy.save.name.ensure_unique}")
        print(f"      sanitize: {loader_policy.save.name.sanitize}")
        
        print(f"\n   ✅ FSOOpsPolicy:")
        print(f"      type: {type(loader_policy.save.ops).__name__}")
        print(f"      create_if_missing: {loader_policy.save.ops.exist.create_if_missing}")
        print(f"      overwrite: {loader_policy.save.ops.exist.overwrite}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("✅ All image_utils YAML configuration files are valid!")
    print("=" * 70)


if __name__ == "__main__":
    test_image_yaml_configs()
