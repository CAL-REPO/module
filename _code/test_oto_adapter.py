# -*- coding: utf-8 -*-
"""Test OTO Adapter (Adapter Pattern)."""

import sys
from pathlib import Path

# PYTHONPATH 설정
code_dir = Path(__file__).parent
modules_dir = code_dir / "modules"
scripts_dir = code_dir / "scripts"
sys.path.insert(0, str(modules_dir))
sys.path.insert(0, str(scripts_dir))

from PIL import Image
from oto.adapter.oto import Oto

def test_oto_adapter():
    """Test OTO Adapter with Translate pattern."""
    
    print("\n" + "=" * 80)
    print("🧪 Testing OTO Adapter (Adapter Pattern)")
    print("=" * 80)
    
    # Test image
    test_img = code_dir / "scripts" / "test_img" / "01.jpg"
    output_dir = test_img.parent
    
    if not test_img.exists():
        print(f"❌ Test image not found: {test_img}")
        return False
    
    print(f"\n📁 Test image: {test_img}")
    print(f"📁 Output dir: {output_dir}")
    
    # ========================================================================
    # Test 1: Adapter Pattern - run(image)
    # ========================================================================
    print("\n" + "=" * 80)
    print("Test 1: OTO Adapter - run(image)")
    print("=" * 80)
    
    try:
        # Load image
        image = Image.open(test_img)
        print(f"Loaded image: {image.size} {image.mode}")
        
        # Create OTO adapter with minimal config
        oto = Oto(
            cfg_like={
                "text_recognize": {
                    "provider": {"langs": ["ch", "en"]},
                    "preprocess": {"max_width": None},
                    "postprocess": {
                        "strip_special_chars": True,
                        "filter_alphanumeric": False,
                    },
                },
                "translate": {
                    "provider": {
                        "provider": "mock",  # mock provider 사용 (google은 미지원)
                        "source_lang": "auto",
                        "target_lang": "ko",
                    },
                },
                "overlay": {
                    "items": [],  # OCR 결과로 자동 생성
                    "background_opacity": 0.7,
                },
                "log": {
                    "enabled": True,
                    "level": "INFO",
                },
            }
        )
        
        print("\n✅ OTO adapter created")
        
        # Run pipeline
        result = oto.run(image=image, source_path=test_img)
        
        if not result["success"]:
            print(f"❌ Pipeline failed: {result.get('error')}")
            return False
        
        # Check results
        ocr_items = result.get("ocr_items", [])
        translated_dict = result.get("translated_dict", {})
        overlay_items = result.get("overlay_items", [])
        final_image = result.get("image")
        
        print(f"\n📊 Pipeline Results:")
        print(f"  OCR items: {len(ocr_items)}")
        print(f"  Translations: {len(translated_dict)}")
        print(f"  Overlay items: {len(overlay_items)}")
        print(f"  Final image: {final_image.size if final_image else None}")
        
        if ocr_items:
            print(f"\n  Top 3 OCR results:")
            for i, item in enumerate(ocr_items[:3], 1):
                original = item.text
                translated = translated_dict.get(original, original)
                print(f"    {i}. '{original}' → '{translated}' (conf: {item.conf:.2f})")
        
        # Save result
        if final_image:
            output_path = output_dir / "oto_adapter_result.jpg"
            final_image.save(output_path)
            print(f"\n💾 Saved: {output_path.name}")
        
        print("\n✅ Test 1 PASSED")
        
    except Exception as e:
        print(f"\n❌ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 80)
    print("📊 Test Summary")
    print("=" * 80)
    print("✅ OTO Adapter: PASSED")
    print(f"   - OCR: {len(ocr_items)} items")
    print(f"   - Translation: {len(translated_dict)} pairs")
    print(f"   - Overlay: {len(overlay_items)} items")
    print(f"   - Output: {output_path.name}")
    print("\n✅ All tests PASSED")
    
    return True


if __name__ == "__main__":
    success = test_oto_adapter()
    sys.exit(0 if success else 1)
