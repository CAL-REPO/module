# -*- coding: utf-8 -*-
"""ImageOverlay adapter 테스트."""

import sys
from pathlib import Path
from PIL import Image

# PYTHONPATH 설정
modules_path = Path(__file__).parent / "modules"
if str(modules_path) not in sys.path:
    sys.path.insert(0, str(modules_path))

def test_overlay():
    """ImageOverlay adapter 테스트."""
    print("\n" + "="*80)
    print("🧪 Testing ImageOverlay Adapter")
    print("="*80)
    
    try:
        from image_utils.adapter.overlay import ImageOverlay
        from image_utils.core.policy import ImageOverlayPolicy, OverlayItemPolicy
        
        print("✅ Imports successful")
        
        # 테스트 이미지 경로
        test_image = Path(r"M:\CALife\CAShop - 구매대행\_code\scripts\test_img\01.jpg")
        output_dir = test_image.parent
        
        print(f"📁 Test image: {test_image}")
        print(f"📁 Output dir: {output_dir}")
        
        if not test_image.exists():
            print(f"❌ Test image not found: {test_image}")
            return False
        
        # 1. Policy 생성 (오버레이 항목 포함)
        policy = ImageOverlayPolicy(
            items=[
                OverlayItemPolicy(
                    text="TEST OVERLAY",
                    polygon=[(50, 50), (500, 50), (500, 100), (50, 100)],  # 사각형
                    font={"size": 48, "color": (255, 0, 0, 255)},  # Red
                ),
                OverlayItemPolicy(
                    text="Second Line",
                    polygon=[(50, 120), (500, 120), (500, 170), (50, 170)],  # 사각형
                    font={"size": 32, "color": (0, 0, 255, 255)},  # Blue
                ),
            ],
            background_opacity=0.0
        )
        print(f"✅ ImageOverlayPolicy created: {policy.name}")
        print(f"   Items: {len(policy.items)}")
        
        # 2. Adapter 생성
        adapter = ImageOverlay(cfg_like=policy)
        print("✅ ImageOverlay adapter created")
        
        # 3. 이미지 로드
        img = Image.open(test_image)
        print(f"✅ Image loaded: {img.size} {img.mode}")
        
        # 4. run() 실행
        print("\n📝 Running overlay...")
        result = adapter.run(img)
        
        if result["success"]:
            print("\n✅ ImageOverlay.run() successful!")
            print(f"   Image size: {result['image_size']}")
            print(f"   Overlaid items: {result['overlaid_items']}")
            
            # 결과 이미지 저장
            if result["image"]:
                output_path = output_dir / "01_overlay_result.jpg"
                result["image"].save(output_path)
                print(f"   💾 Saved to: {output_path}")
        else:
            print(f"❌ ImageOverlay.run() failed: {result.get('error')}")
            return False
        
        # 5. run() with custom items (런타임 오버라이드)
        print("\n📝 Testing custom items...")
        custom_items = [
            OverlayItemPolicy(
                text="CUSTOM OVERLAY",
                polygon=[(100, 200), (700, 200), (700, 280), (100, 280)],  # 사각형
                font={"size": 64, "color": (0, 255, 0, 255)},  # Green
            ),
        ]
        
        result2 = adapter.run(img, items=custom_items)
        
        if result2["success"]:
            print("✅ ImageOverlay.run(custom_items) successful!")
            print(f"   Overlaid items: {result2['overlaid_items']}")
            
            # 결과 이미지 저장
            if result2["image"]:
                output_path = output_dir / "01_overlay_custom.jpg"
                result2["image"].save(output_path)
                print(f"   💾 Saved to: {output_path}")
        else:
            print(f"❌ ImageOverlay.run(custom_items) failed: {result2.get('error')}")
            return False
        
        print("\n✅ ImageOverlay adapter test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ ImageOverlay adapter test FAILED")
        print(f"   Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_overlay()
    sys.exit(0 if success else 1)
