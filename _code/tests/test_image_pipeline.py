# -*- coding: utf-8 -*-
"""Image Processing Pipeline Test - Updated for New Architecture

Tests the complete pipeline with SRP compliance:
ImageLoader → ImageOCR → [Translation in script] → ImageOverlay

Key Design Principles:
1. Each module does only its job (SRP)
2. Pipeline coordination happens in script
3. OCRItem → OverlayItemPolicy conversion in script
4. Image objects passed between modules (no redundant FSO access)
"""

from pathlib import Path
from typing import List
import sys

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from image_utils.services.image_loader import ImageLoader
from image_utils.services.image_ocr import ImageOCR
from image_utils.services.image_overlay import ImageOverlay
from image_utils.core.models import OCRItem
from image_utils.core.policy import OverlayItemPolicy


def test_pipeline(image_path: Path):
    """Test complete image processing pipeline.
    
    Args:
        image_path: Path to test image
    """
    print("=" * 80)
    print("Image Processing Pipeline Test - New Architecture")
    print("=" * 80)
    print(f"Test image: {image_path}")
    
    # =========================================================================
    # Step 1: Load Image
    # =========================================================================
    print("\n[Step 1/5] ImageLoader: Load and preprocess image")
    print("-" * 80)
    
    loader = ImageLoader()
    loader_result = loader.run(source_override=str(image_path))
    
    if not loader_result["success"]:
        print(f"❌ ImageLoader failed: {loader_result['error']}")
        return
    
    image = loader_result["image"]
    print(f"✅ Image loaded: {image.size} {image.mode}")
    print(f"   Source: {loader_result['original_path']}")
    if loader_result.get("saved_path"):
        print(f"   Saved to: {loader_result['saved_path']}")
    
    # =========================================================================
    # Step 2: OCR (Optical Character Recognition)
    # =========================================================================
    print("\n[Step 2/5] ImageOCR: Detect text in image")
    print("-" * 80)
    
    ocr = ImageOCR()
    ocr_result = ocr.run(
        source_override=str(image_path),
        image=image,  # Pass Image object from Step 1 (no redundant FSO)
    )
    
    if not ocr_result["success"]:
        print(f"❌ ImageOCR failed: {ocr_result['error']}")
        return
    
    ocr_items: List[OCRItem] = ocr_result["ocr_items"]
    preprocessed_image = ocr_result["image"]
    
    print(f"✅ OCR completed: {len(ocr_items)} text items detected")
    for idx, item in enumerate(ocr_items[:5]):  # Show first 5
        print(f"   [{idx+1}] '{item.text}' (conf={item.conf:.2f}, lang={item.lang})")
    if len(ocr_items) > 5:
        print(f"   ... and {len(ocr_items) - 5} more items")
    
    if not ocr_items:
        print("⚠️  No text detected, skipping overlay")
        return
    
    # =========================================================================
    # Step 3: Translation (Optional - script responsibility)
    # =========================================================================
    print("\n[Step 3/5] Translation: Translate OCR results (script responsibility)")
    print("-" * 80)
    
    # Here you would call TranslateUtils or similar
    # For this test, we'll simulate translation by reversing text
    translated_texts = {}
    for item in ocr_items:
        # Simulate translation: reverse the text for demo
        translated_texts[item.text] = f"[TR] {item.text[::-1]}"
    
    print(f"✅ Translation completed: {len(translated_texts)} texts translated")
    for original, translated in list(translated_texts.items())[:3]:
        print(f"   '{original}' → '{translated}'")
    
    # =========================================================================
    # Step 4: Convert OCRItem → OverlayItemPolicy (script responsibility)
    # =========================================================================
    print("\n[Step 4/5] Conversion: OCRItem → OverlayItemPolicy (script responsibility)")
    print("-" * 80)
    
    overlay_items: List[OverlayItemPolicy] = []
    for item in ocr_items:
        # Use OCRItem.to_overlay_item() method
        translated_text = translated_texts.get(item.text, item.text)
        overlay_item = item.to_overlay_item(text_override=translated_text)
        overlay_items.append(overlay_item)
    
    print(f"✅ Conversion completed: {len(overlay_items)} overlay items created")
    for idx, item in enumerate(overlay_items[:3]):
        print(f"   [{idx+1}] '{item.text[:30]}...' polygon={len(item.polygon)} points")
    
    # =========================================================================
    # Step 5: Image Overlay
    # =========================================================================
    print("\n[Step 5/5] ImageOverlay: Render overlay items on image")
    print("-" * 80)
    
    overlay = ImageOverlay()
    overlay_result = overlay.run(
        source_path=str(image_path),
        image=preprocessed_image,  # Pass preprocessed image from Step 2
        overlay_items=overlay_items,  # Pass converted items from Step 4
    )
    
    if not overlay_result["success"]:
        print(f"❌ ImageOverlay failed: {overlay_result['error']}")
        return
    
    final_image = overlay_result["image"]
    print(f"✅ Overlay completed: {overlay_result['overlaid_items']} items rendered")
    print(f"   Image size: {overlay_result['image_size']}")
    if overlay_result.get("saved_path"):
        print(f"   Saved to: {overlay_result['saved_path']}")
    if overlay_result.get("meta_path"):
        print(f"   Metadata: {overlay_result['meta_path']}")
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("Pipeline Test Summary")
    print("=" * 80)
    print(f"✅ All steps completed successfully!")
    print(f"   1. Loaded image: {image.size} {image.mode}")
    print(f"   2. Detected texts: {len(ocr_items)}")
    print(f"   3. Translated texts: {len(translated_texts)}")
    print(f"   4. Converted items: {len(overlay_items)}")
    print(f"   5. Overlaid items: {overlay_result['overlaid_items']}")
    print(f"   → Final image: {final_image.size} {final_image.mode}")
    print("=" * 80)
    print("\n✨ Pipeline architecture validated:")
    print("   - SRP compliance: Each module does one thing")
    print("   - Image objects passed (no redundant FSO)")
    print("   - Conversion logic in script (not in modules)")
    print("=" * 80)


if __name__ == "__main__":
    # Test with first available image
    images_dir = Path(__file__).parent.parent.parent / "_public" / "01.IMAGE"
    
    test_image = None
    
    # Find first image
    if images_dir.exists():
        for category_dir in images_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            # Try JPG
            for img_file in list(category_dir.glob("*.[jJ][pP][gG]"))[:1]:
                test_image = img_file
                break
            
            # Try PNG
            if not test_image:
                for img_file in list(category_dir.glob("*.[pP][nN][gG]"))[:1]:
                    test_image = img_file
                    break
            
            if test_image:
                break
    
    # Fallback to test_images
    if not test_image:
        test_dir = Path(__file__).parent.parent / "output" / "test_images"
        if test_dir.exists():
            for img_file in list(test_dir.glob("*.png"))[:1] + list(test_dir.glob("*.jpg"))[:1]:
                test_image = img_file
                break
    
    if test_image and test_image.exists():
        print(f"Using test image: {test_image}\n")
        test_pipeline(test_image)
    else:
        print("❌ No test images found!")
        print("   Please provide an image in:")
        print(f"   - {images_dir}")
        print(f"   - {Path(__file__).parent.parent / 'output' / 'test_images'}")

