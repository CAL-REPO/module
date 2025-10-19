# -*- coding: utf-8 -*-
"""ImageTextRecognizer entry_point 테스트."""

import sys
from pathlib import Path

# PYTHONPATH 설정
modules_path = Path(__file__).parent / "modules"
if str(modules_path) not in sys.path:
    sys.path.insert(0, str(modules_path))

def test_text_recognizer():
    """ImageTextRecognizer entry_point 테스트."""
    print("\n" + "="*80)
    print("🧪 Testing ImageTextRecognizer EntryPoint")
    print("="*80)
    
    try:
        from image_utils.entry_point.text_recognizer import ImageTextRecognizer
        from image_utils.core.policy import ImageTextRecognizerPolicy, ImageTextRecognizePolicy
        
        print("✅ Imports successful")
        
        # 테스트 이미지 경로
        test_image = Path(r"M:\CALife\CAShop - 구매대행\_code\scripts\test_img\01.jpg")
        output_dir = test_image.parent
        
        print(f"📁 Test image: {test_image}")
        print(f"📁 Output dir: {output_dir}")
        
        if not test_image.exists():
            print(f"❌ Test image not found: {test_image}")
            return False
        
        # 1. Policy 생성 (source + text_recognize)
        policy = ImageTextRecognizerPolicy(
            source={"path": str(test_image)},
            text_recognize=ImageTextRecognizePolicy()
        )
        print(f"✅ ImageTextRecognizerPolicy created: {policy.name}")
        
        # 2. EntryPoint 생성
        recognizer = ImageTextRecognizer(cfg_like=policy)
        print("✅ ImageTextRecognizer entry_point created")
        
        # 3. run() 실행
        print("\n📝 Running OCR...")
        result = recognizer.run()
        
        if result["success"]:
            print("\n✅ ImageTextRecognizer.run() successful!")
            print(f"   Source: {result['source_path']}")
            print(f"   Original size: {result['original_size']}")
            print(f"   Detected: {len(result['ocr_items'])} text items")
            
            # 결과 출력 (상위 5개)
            if result['ocr_items']:
                print("\n📋 Top 5 OCR results:")
                for i, item in enumerate(result['ocr_items'][:5], 1):
                    print(f"   {i}. '{item.text}' (conf: {item.conf:.2f}, lang: {item.lang})")
            
            # 결과를 텍스트 파일로 저장
            output_path = output_dir / "01_recognizer_result.txt"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"OCR Results: {len(result['ocr_items'])} items\n")
                f.write("="*80 + "\n\n")
                for i, item in enumerate(result['ocr_items'], 1):
                    f.write(f"{i}. {item.text} (conf: {item.conf:.2f}, lang: {item.lang})\n")
            print(f"\n💾 Results saved to: {output_path}")
        else:
            print(f"❌ ImageTextRecognizer.run() failed: {result.get('error')}")
            return False
        
        # 4. run() with source_override
        print("\n📝 Testing source_override...")
        result2 = recognizer.run(source_override=test_image)
        
        if result2["success"]:
            print(f"✅ ImageTextRecognizer.run(source_override) successful!")
            print(f"   Detected: {len(result2['ocr_items'])} items")
        else:
            print(f"❌ ImageTextRecognizer.run(source_override) failed: {result2.get('error')}")
            return False
        
        print("\n✅ ImageTextRecognizer entry_point test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ ImageTextRecognizer entry_point test FAILED")
        print(f"   Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_text_recognizer()
    sys.exit(0 if success else 1)
