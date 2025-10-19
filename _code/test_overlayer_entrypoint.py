# -*- coding: utf-8 -*-
"""ImageOverlayer entry_point 테스트."""

import sys
from pathlib import Path

# PYTHONPATH 설정
modules_path = Path(__file__).parent / "modules"
if str(modules_path) not in sys.path:
    sys.path.insert(0, str(modules_path))

def test_overlayer():
    """ImageOverlayer entry_point 테스트."""
    print("\n" + "="*80)
    print("🧪 Testing ImageOverlayer EntryPoint")
    print("="*80)
    
    try:
        from image_utils.entry_point.overlayer import ImageOverlayer
        from image_utils.core.policy import ImageOverlayerPolicy, ImageOverlayPolicy, OverlayItemPolicy
        
        print("✅ Imports successful")
        
        # 테스트 이미지 경로
        test_image = Path(r"M:\CALife\CAShop - 구매대행\_code\scripts\test_img\01.jpg")
        output_dir = test_image.parent
        
        print(f"📁 Test image: {test_image}")
        print(f"📁 Output dir: {output_dir}")
        
        if not test_image.exists():
            print(f"❌ Test image not found: {test_image}")
            return False
        
        # 1. Policy 생성 (source + overlay)
        policy = ImageOverlayerPolicy(
            source={"path": str(test_image)},
            overlay=ImageOverlayPolicy(
                items=[
                    OverlayItemPolicy(
                        text="ENTRY POINT TEST",
                        polygon=[(100, 100), (600, 100), (600, 180), (100, 180)],
                        font={"size": 56, "color": (255, 165, 0, 255)},  # Orange
                    ),
                    OverlayItemPolicy(
                        text="ImageOverlayer",
                        polygon=[(100, 200), (550, 200), (550, 260), (100, 260)],
                        font={"size": 40, "color": (128, 0, 128, 255)},  # Purple
                    ),
                ]
            )
        )
        print(f"✅ ImageOverlayerPolicy created: {policy.name}")
        print(f"   Items: {len(policy.overlay.items)}")
        
        # 2. EntryPoint 생성
        overlayer = ImageOverlayer(cfg_like=policy)
        print("✅ ImageOverlayer entry_point created")
        
        # 3. run() 실행
        print("\n📝 Running overlay...")
        result = overlayer.run()
        
        if result["success"]:
            print("\n✅ ImageOverlayer.run() successful!")
            print(f"   Source: {result['source_path']}")
            print(f"   Image size: {result['image_size']}")
            print(f"   Overlaid items: {result['overlaid_items']}")
            
            # 결과 이미지 저장
            if result["image"]:
                output_path = output_dir / "01_overlayer_result.jpg"
                result["image"].save(output_path)
                print(f"   💾 Saved to: {output_path}")
        else:
            print(f"❌ ImageOverlayer.run() failed: {result.get('error')}")
            return False
        
        # 4. run() with source_override and custom items
        print("\n📝 Testing source_override and custom items...")
        custom_items = [
            OverlayItemPolicy(
                text="CUSTOM ENTRY POINT",
                polygon=[(150, 300), (750, 300), (750, 400), (150, 400)],
                font={"size": 72, "color": (255, 0, 255, 255)},  # Magenta
            ),
        ]
        
        result2 = overlayer.run(source_override=test_image, items=custom_items)
        
        if result2["success"]:
            print(f"✅ ImageOverlayer.run(custom) successful!")
            print(f"   Overlaid items: {result2['overlaid_items']}")
            
            # 결과 이미지 저장
            if result2["image"]:
                output_path = output_dir / "01_overlayer_custom.jpg"
                result2["image"].save(output_path)
                print(f"   💾 Saved to: {output_path}")
        else:
            print(f"❌ ImageOverlayer.run(custom) failed: {result2.get('error')}")
            return False
        
        print("\n✅ ImageOverlayer entry_point test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ ImageOverlayer entry_point test FAILED")
        print(f"   Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_overlayer()
    sys.exit(0 if success else 1)
