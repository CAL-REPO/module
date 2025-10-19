# -*- coding: utf-8 -*-
"""Policy 단독 테스트."""

import sys
from pathlib import Path

# PYTHONPATH 설정
modules_path = Path(__file__).parent / "modules"
if str(modules_path) not in sys.path:
    sys.path.insert(0, str(modules_path))

def test_policies():
    """Policy import 테스트."""
    print("\n" + "="*80)
    print("🧪 Testing image_utils Policies")
    print("="*80)
    
    try:
        from image_utils.core.policy import (
            # Adapter policies
            ImageLoadPolicy,
            ImageTextRecognizePolicy,
            ImageOverlayPolicy,
            
            # EntryPoint policies
            ImageLoaderPolicy,
            ImageTextRecognizerPolicy,
            ImageOverlayerPolicy,
        )
        
        print("✅ All policies imported successfully")
        
        # ImageLoadPolicy 생성 테스트
        policy = ImageLoadPolicy()
        print(f"✅ ImageLoadPolicy created: {policy.name}")
        
        # ImageLoaderPolicy 생성 테스트
        from image_utils.core.policy import ImageSourcePolicy
        loader_policy = ImageLoaderPolicy(
            source=ImageSourcePolicy(
                path=Path("test.jpg"),
                must_exist=False
            )
        )
        print(f"✅ ImageLoaderPolicy created: {loader_policy.name}")
        print(f"   source: {loader_policy.source.path}")
        print(f"   image_load.name: {loader_policy.image_load.name}")
        
        print("\n✅ Policy test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Policy test FAILED")
        print(f"   Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_policies()
    sys.exit(0 if success else 1)
