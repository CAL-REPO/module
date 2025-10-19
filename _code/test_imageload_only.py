# -*- coding: utf-8 -*-
"""ImageLoad adapter 단독 테스트."""

import sys
from pathlib import Path

# PYTHONPATH 설정
modules_path = Path(__file__).parent / "modules"
if str(modules_path) not in sys.path:
    sys.path.insert(0, str(modules_path))

def test_imageload():
    """ImageLoad adapter 테스트."""
    print("\n" + "="*80)
    print("🧪 Testing ImageLoad Adapter")
    print("="*80)
    
    try:
        from image_utils.adapter.load import ImageLoad
        
        print("✅ Imports successful")
        
        # 1. 간단한 dict 정책으로 테스트
        policy_dict = {
            "source": {
                "path": r"M:\CALife\CAShop - 구매대행\_public\01.IMAGE\CAPEA-001\01.jpg",
                "pattern": "*.jpg",
                "recursive": False,
                "convert_mode": "RGB"
            },
            "save": {
                "save_copy": False
            },
            "meta": {
                "save_meta": False
            }
        }
        
        print("✅ Policy created")
        
        # 2. Adapter 생성
        adapter = ImageLoad(cfg_like=policy_dict)
        
        print("✅ Adapter created")
        print(f"   Policy source: {adapter.policy.source.path}")
        
        # 3. load() 실행
        result = adapter.load()
        
        if result["success"]:
            print("✅ ImageLoad.load() successful!")
            print(f"   Loaded: {len(result['images'])} image(s)")
            if result['images']:
                img = result['images'][0]
                print(f"   Image size: {img.size}")
                print(f"   Image mode: {img.mode}")
            print(f"   Source: {result['source_path']}")
        else:
            print(f"❌ ImageLoad.load() failed: {result.get('error')}")
            return False
        
        print("\n✅ ImageLoad adapter test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ ImageLoad adapter test FAILED")
        print(f"   Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_imageload()
    sys.exit(0 if success else 1)
