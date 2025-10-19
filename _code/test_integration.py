# -*- coding: utf-8 -*-
"""image_utils 전체 통합 테스트."""

import sys
from pathlib import Path

# PYTHONPATH 설정
modules_path = Path(__file__).parent / "modules"
if str(modules_path) not in sys.path:
    sys.path.insert(0, str(modules_path))

def test_integration():
    """image_utils 전체 통합 테스트."""
    print("\n" + "="*80)
    print("🧪 Testing image_utils Integration")
    print("="*80)
    
    try:
        # 테스트 이미지 경로
        test_image = Path(r"M:\CALife\CAShop - 구매대행\_code\scripts\test_img\01.jpg")
        output_dir = test_image.parent
        
        print(f"\n📁 Test image: {test_image}")
        print(f"📁 Output dir: {output_dir}")
        
        if not test_image.exists():
            print(f"❌ Test image not found: {test_image}")
            return False
        
        # ======================================================================
        # 1. ImageLoader 테스트
        # ======================================================================
        print("\n" + "="*80)
        print("1️⃣ Testing ImageLoader (Load + Process)")
        print("="*80)
        
        from image_utils.entry_point.loader import ImageLoader
        from image_utils.core.policy import ImageLoaderPolicy, ImageLoadPolicy
        
        loader_policy = ImageLoaderPolicy(
            source={"path": str(test_image)},
            image_load=ImageLoadPolicy()
        )
        loader = ImageLoader(cfg_like=loader_policy)
        loader_result = loader.run()
        
        if loader_result["success"]:
            print(f"✅ ImageLoader: {loader_result['original_size']} → {loader_result['processed_size']}")
            output_path = output_dir / "integration_01_loaded.jpg"
            loader_result["image"].save(output_path)
            print(f"   💾 Saved: {output_path.name}")
        else:
            print(f"❌ ImageLoader failed: {loader_result.get('error')}")
            return False
        
        # ======================================================================
        # 2. ImageTextRecognizer 테스트 (OCR)
        # ======================================================================
        print("\n" + "="*80)
        print("2️⃣ Testing ImageTextRecognizer (OCR)")
        print("="*80)
        
        from image_utils.entry_point.text_recognizer import ImageTextRecognizer
        from image_utils.core.policy import ImageTextRecognizerPolicy, ImageTextRecognizePolicy
        
        recognizer_policy = ImageTextRecognizerPolicy(
            source={"path": str(test_image)},
            text_recognize=ImageTextRecognizePolicy()
        )
        recognizer = ImageTextRecognizer(cfg_like=recognizer_policy)
        ocr_result = recognizer.run()
        
        if ocr_result["success"]:
            print(f"✅ ImageTextRecognizer: {len(ocr_result['ocr_items'])} items detected")
            if ocr_result['ocr_items']:
                print(f"   📋 Top 3:")
                for i, item in enumerate(ocr_result['ocr_items'][:3], 1):
                    print(f"      {i}. '{item.text}' (conf: {item.conf:.2f})")
            
            # OCR 결과를 텍스트 파일로 저장
            output_path = output_dir / "integration_02_ocr.txt"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"OCR Results: {len(ocr_result['ocr_items'])} items\n")
                f.write("="*80 + "\n\n")
                for i, item in enumerate(ocr_result['ocr_items'], 1):
                    f.write(f"{i}. {item.text} (conf: {item.conf:.2f})\n")
            print(f"   💾 Saved: {output_path.name}")
        else:
            print(f"❌ ImageTextRecognizer failed: {ocr_result.get('error')}")
            return False
        
        # ======================================================================
        # 3. ImageOverlayer 테스트 (OCR 결과로 오버레이)
        # ======================================================================
        print("\n" + "="*80)
        print("3️⃣ Testing ImageOverlayer (Overlay OCR results)")
        print("="*80)
        
        from image_utils.entry_point.overlayer import ImageOverlayer
        from image_utils.core.policy import ImageOverlayerPolicy, ImageOverlayPolicy, OverlayItemPolicy
        
        # OCR 결과를 오버레이 항목으로 변환 (상위 5개만)
        overlay_items = []
        for item in ocr_result['ocr_items'][:5]:
            overlay_items.append(
                OverlayItemPolicy(
                    text=item.text,
                    polygon=item.quad,
                    font={"size": 24, "color": (255, 0, 0, 255)},  # Red
                )
            )
        
        overlayer_policy = ImageOverlayerPolicy(
            source={"path": str(test_image)},
            overlay=ImageOverlayPolicy(
                items=[],  # runtime에서 items 전달
                background_opacity=0.0
            )
        )
        overlayer = ImageOverlayer(cfg_like=overlayer_policy)
        overlay_result = overlayer.run(items=overlay_items)
        
        if overlay_result["success"]:
            print(f"✅ ImageOverlayer: {overlay_result['overlaid_items']} items rendered")
            output_path = output_dir / "integration_03_overlay.jpg"
            overlay_result["image"].save(output_path)
            print(f"   💾 Saved: {output_path.name}")
        else:
            print(f"❌ ImageOverlayer failed: {overlay_result.get('error')}")
            return False
        
        # ======================================================================
        # 4. 전체 파이프라인 테스트 (Load → OCR → Overlay)
        # ======================================================================
        print("\n" + "="*80)
        print("4️⃣ Testing Full Pipeline (Load → OCR → Overlay)")
        print("="*80)
        
        # 4.1. Load
        loader2 = ImageLoader(cfg_like=loader_policy)
        loaded = loader2.run()
        
        if not loaded["success"]:
            print(f"❌ Pipeline Load failed: {loaded.get('error')}")
            return False
        
        print(f"✅ Step 1: Loaded {loaded['original_size']}")
        
        # 4.2. OCR (Adapter 직접 사용 - Image 객체 전달)
        from image_utils.adapter.text_recognize import ImageTextRecognize
        
        ocr_adapter = ImageTextRecognize(cfg_like=ImageTextRecognizePolicy())
        ocr_items = ocr_adapter.run(loaded["image"])
        
        print(f"✅ Step 2: OCR detected {len(ocr_items)} items")
        
        # 4.3. Overlay (Adapter 직접 사용 - Image 객체 + items 전달)
        from image_utils.adapter.overlay import ImageOverlay
        
        # OCR 결과를 오버레이 항목으로 변환 (상위 3개만)
        pipeline_items = []
        for item in ocr_items[:3]:
            pipeline_items.append(
                OverlayItemPolicy(
                    text=item.text,
                    polygon=item.quad,
                    font={"size": 32, "color": (0, 255, 0, 255)},  # Green
                )
            )
        
        overlay_adapter = ImageOverlay(cfg_like=ImageOverlayPolicy(items=[], background_opacity=0.0))
        overlay_result2 = overlay_adapter.run(loaded["image"], items=pipeline_items)
        
        if overlay_result2["success"]:
            print(f"✅ Step 3: Overlay rendered {overlay_result2['overlaid_items']} items")
            output_path = output_dir / "integration_04_pipeline.jpg"
            overlay_result2["image"].save(output_path)
            print(f"   💾 Saved: {output_path.name}")
        else:
            print(f"❌ Pipeline Overlay failed: {overlay_result2.get('error')}")
            return False
        
        # ======================================================================
        # 결과 요약
        # ======================================================================
        print("\n" + "="*80)
        print("📊 Integration Test Results")
        print("="*80)
        print(f"✅ ImageLoader: Success")
        print(f"✅ ImageTextRecognizer: {len(ocr_result['ocr_items'])} OCR items")
        print(f"✅ ImageOverlayer: {overlay_result['overlaid_items']} items rendered")
        print(f"✅ Full Pipeline: Load → OCR ({len(ocr_items)} items) → Overlay ({overlay_result2['overlaid_items']} items)")
        print("\n📁 Output files:")
        print(f"   - integration_01_loaded.jpg")
        print(f"   - integration_02_ocr.txt")
        print(f"   - integration_03_overlay.jpg")
        print(f"   - integration_04_pipeline.jpg")
        
        print("\n✅ Integration test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test FAILED")
        print(f"   Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)
