# -*- coding: utf-8 -*-
"""ImageLoad adapter 테스트."""

import sys
from pathlib import Path
from PIL import Image

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
        from image_utils.core.policy import ImageLoadPolicy
        
        print("✅ Imports successful")
        
        # 1. Policy 생성
        policy = ImageLoadPolicy()
        print(f"✅ ImageLoadPolicy created: {policy.name}")
        
        # 2. Adapter 생성
        adapter = ImageLoad(cfg_like=policy)
        print("✅ ImageLoad adapter created")
        
        # 3. run() with file path
        test_image = Path(r"M:\CALife\CAShop - 구매대행\_code\scripts\test_img\01.jpg")
        output_dir = test_image.parent
        
        print(f"📁 Test image: {test_image}")
        print(f"📁 Output dir: {output_dir}")
        
        if test_image.exists():
            result = adapter.run(test_image)
            
            if result["success"]:
                print("✅ ImageLoad.run(file_path) successful!")
                print(f"   Original size: {result['original_size']}")
                print(f"   Processed size: {result['processed_size']}")
                print(f"   Processing: {result['processing']}")
                
                # 결과 이미지 저장 (테스트용)
                if result["image"]:
                    output_path = output_dir / "01_processed.jpg"
                    result["image"].save(output_path)
                    print(f"   💾 Saved to: {output_path}")
            else:
                print(f"❌ ImageLoad.run() failed: {result.get('error')}")
                return False
            
            # 4. run() with Image object
            img = Image.open(test_image)
            result2 = adapter.run(img)
            
            if result2["success"]:
                print("✅ ImageLoad.run(Image) successful!")
                print(f"   Original size: {result2['original_size']}")
                
                # Image 객체로 처리한 결과도 저장 (테스트용)
                if result2["image"]:
                    output_path = output_dir / "01_processed_from_image.jpg"
                    result2["image"].save(output_path)
                    print(f"   💾 Saved to: {output_path}")
            else:
                print(f"❌ ImageLoad.run(Image) failed: {result2.get('error')}")
                return False
        else:
            print(f"⚠️ Test image not found: {test_image}")
            print("   Skipping run() tests")
        
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
