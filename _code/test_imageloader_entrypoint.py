# -*- coding: utf-8 -*-
"""ImageLoader entry_point 테스트."""

import sys
from pathlib import Path

# PYTHONPATH 설정
modules_path = Path(__file__).parent / "modules"
if str(modules_path) not in sys.path:
    sys.path.insert(0, str(modules_path))

def test_imageloader():
    """ImageLoader entry_point 테스트."""
    print("\n" + "="*80)
    print("🧪 Testing ImageLoader EntryPoint")
    print("="*80)
    
    try:
        from image_utils.entry_point.loader import ImageLoader
        from image_utils.core.policy import ImageLoaderPolicy, ImageLoadPolicy
        
        print("✅ Imports successful")
        
        # 테스트 이미지 경로
        test_image = Path(r"M:\CALife\CAShop - 구매대행\_code\scripts\test_img\01.jpg")
        output_dir = test_image.parent
        
        print(f"📁 Test image: {test_image}")
        print(f"📁 Output dir: {output_dir}")
        
        if not test_image.exists():
            print(f"❌ Test image not found: {test_image}")
            return False
        
        # 1. Policy 생성 (source + image_load)
        policy = ImageLoaderPolicy(
            source={"path": str(test_image)},
            image_load=ImageLoadPolicy()
        )
        print(f"✅ ImageLoaderPolicy created: {policy.name}")
        
        # 2. EntryPoint 생성
        loader = ImageLoader(cfg_like=policy)
        print("✅ ImageLoader entry_point created")
        
        # 3. run() 실행
        result = loader.run()
        
        if result["success"]:
            print("✅ ImageLoader.run() successful!")
            print(f"   Source: {result['source_path']}")
            print(f"   Original size: {result['original_size']}")
            print(f"   Processed size: {result['processed_size']}")
            print(f"   Processing: {result['processing']}")
            
            # 결과 이미지 저장
            if result["image"]:
                output_path = output_dir / "01_loader_output.jpg"
                result["image"].save(output_path)
                print(f"   💾 Saved to: {output_path}")
        else:
            print(f"❌ ImageLoader.run() failed: {result.get('error')}")
            return False
        
        # 4. run() with source_override
        print("\n📝 Testing source_override...")
        result2 = loader.run(source_override=test_image)
        
        if result2["success"]:
            print("✅ ImageLoader.run(source_override) successful!")
            
            # 결과 이미지 저장
            if result2["image"]:
                output_path = output_dir / "01_loader_override.jpg"
                result2["image"].save(output_path)
                print(f"   💾 Saved to: {output_path}")
        else:
            print(f"❌ ImageLoader.run(source_override) failed: {result2.get('error')}")
            return False
        
        print("\n✅ ImageLoader entry_point test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ ImageLoader entry_point test FAILED")
        print(f"   Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_imageloader()
    sys.exit(0 if success else 1)
