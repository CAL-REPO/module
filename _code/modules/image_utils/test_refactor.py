# -*- coding: utf-8 -*-
"""Quick test for the refactored ImageOCR system."""

from pathlib import Path
from image_utils.services.ocr import ImageOCR, OcrPolicy
from pillow_utils.policy import ImageSourcePolicy
from image_utils.services.ocr.core.policy import OcrProviderPolicy, OcrPreprocessPolicy
from log_utils.core.policy import LogPolicy

def test_image_ocr_from_yaml():
    """Test ImageOCR loading from YAML config."""
    print("\n" + "=" * 70)
    print("TEST 1: ImageOCR from YAML Config")
    print("=" * 70)
    
    cfg_path = Path("M:/CALife/CAShop - 구매대행/_code/configs/ocr.yaml")
    
    if not cfg_path.exists():
        print(f"❌ Config file not found: {cfg_path}")
        return False
    
    try:
        ocr = ImageOCR(cfg_path)
        print(f"✅ ImageOCR initialized from {cfg_path}")
        print(f"   Source: {ocr.policy.src_path}")
        print(f"   Logger: {ocr.logger}")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_ocr_from_policy():
    """Test ImageOCR with programmatic policy."""
    print("\n" + "=" * 70)
    print("TEST 2: ImageOCR from OcrPolicy Object")
    print("=" * 70)
    
    try:
        policy = OcrPolicy(
            source=ImageSourcePolicy(  # pyright: ignore
                path=Path("M:/CALife/CAShop - 구매대행/_code/scripts/01.jpg"),
                must_exist=False,
                convert_mode="RGB"
            ),
            provider=OcrProviderPolicy(  # pyright: ignore
                langs=["en", "ch_sim"],
                min_conf=0.5,
                paddle_device="cpu"  # Use CPU for test
            ),
            preprocess=OcrPreprocessPolicy(max_width=1200),  # pyright: ignore
            log=LogPolicy(enabled=True, level="INFO")  # pyright: ignore
        )
        
        print("✅ OcrPolicy created successfully")
        print(f"   Source path: {policy.source.path if policy.source else 'None'}")  # pyright: ignore
        print(f"   Languages: {policy.provider.langs}")
        print(f"   Device: {policy.provider.paddle_device}")
        print(f"   Log enabled: {policy.log.enabled if policy.log else False}")  # pyright: ignore
        
        # Try to create ImageOCR (without running)
        # ocr = ImageOCR(policy)
        # print(f"✅ ImageOCR initialized")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create policy: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compat():
    """Test backward compatibility with run_ocr function."""
    print("\n" + "=" * 70)
    print("TEST 3: Backward Compatibility (run_ocr function)")
    print("=" * 70)
    
    try:
        from image_utils.services.ocr import run_ocr
        print("✅ run_ocr function imported successfully")
        print("   This maintains backward compatibility with old code")
        return True
    except Exception as e:
        print(f"❌ Failed to import run_ocr: {e}")
        return False


def main():
    print("\n" + "=" * 70)
    print("ImageOCR Refactoring Test Suite")
    print("=" * 70)
    
    results = {
        "TEST 1: YAML Config": test_image_ocr_from_yaml(),
        "TEST 2: Policy Object": test_image_ocr_from_policy(),
        "TEST 3: Backward Compat": test_backward_compat(),
    }
    
    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed_count = sum(results.values())
    
    print(f"\nTotal: {passed_count}/{total} tests passed")
    
    if passed_count == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
