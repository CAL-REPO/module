# -*- coding: utf-8 -*-
"""ImageTextRecognize adapter 테스트."""

import sys
from pathlib import Path
from PIL import Image

# PYTHONPATH 설정
modules_path = Path(__file__).parent / "modules"
if str(modules_path) not in sys.path:
    sys.path.insert(0, str(modules_path))

def test_text_recognize():
    """ImageTextRecognize adapter 테스트."""
    print("\n" + "="*80)
    print("🧪 Testing ImageTextRecognize Adapter")
    print("="*80)
    
    try:
        from image_utils.adapter.text_recognize import ImageTextRecognize
        from image_utils.core.policy import ImageTextRecognizePolicy
        
        print("✅ Imports successful")
        
        # 테스트 이미지 경로
        test_image = Path(r"M:\CALife\CAShop - 구매대행\_code\scripts\test_img\01.jpg")
        output_dir = test_image.parent
        
        print(f"📁 Test image: {test_image}")
        print(f"📁 Output dir: {output_dir}")
        
        if not test_image.exists():
            print(f"❌ Test image not found: {test_image}")
            return False
        
        # 1. Policy 생성
        policy = ImageTextRecognizePolicy()
        print(f"✅ ImageTextRecognizePolicy created: {policy.name}")
        
        # 2. Adapter 생성
        adapter = ImageTextRecognize(cfg_like=policy)
        print("✅ ImageTextRecognize adapter created")
        
        # 3. 이미지 로드
        img = Image.open(test_image)
        print(f"✅ Image loaded: {img.size} {img.mode}")
        
        # 4. run() 실행
        print("\n📝 Running OCR...")
        result = adapter.run(img)
        
        print(f"\n✅ ImageTextRecognize.run() successful!")
        print(f"   Detected: {len(result)} text items")
        
        # 결과 출력 (상위 10개)
        if result:
            print("\n📋 Top 10 OCR results:")
            for i, item in enumerate(result[:10], 1):
                print(f"   {i}. '{item.text}' (conf: {item.conf:.2f}, lang: {item.lang})")
        
        # 결과를 텍스트 파일로 저장
        output_path = output_dir / "01_ocr_result.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"OCR Results: {len(result)} items\n")
            f.write("="*80 + "\n\n")
            for i, item in enumerate(result, 1):
                f.write(f"{i}. {item.text} (conf: {item.conf:.2f}, lang: {item.lang})\n")
        print(f"\n💾 Results saved to: {output_path}")
        
        print("\n✅ ImageTextRecognize adapter test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ ImageTextRecognize adapter test FAILED")
        print(f"   Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_text_recognize()
    sys.exit(0 if success else 1)
