"""Unified Pipeline Test: ImageLoader → ImageOCR → ImageOverlay

Tests the complete image processing pipeline using unified.yaml configuration:
1. ImageLoader: Load and preprocess image
2. ImageOCR: Extract text with OCR
3. ImageOverlay: Overlay translated/processed text back onto image
"""

from pathlib import Path
from image_utils.adapter.loader import ImageLoader
from image_utils.services.ocr.services.image_ocr import ImageOCR
from image_utils.adapter.image_overlay import ImageOverlay


def main():
    """Run complete image processing pipeline."""
    cfg_path = "M:/CALife/CAShop - 구매대행/_code/configs/unified.yaml"
    
    print("=" * 80)
    print("UNIFIED PIPELINE TEST")
    print("=" * 80)
    
    # Step 1: Load and preprocess image
    print("\n[1/3] ImageLoader: Loading and preprocessing image...")
    loader = ImageLoader(cfg_path)
    loader_result = loader.run()
    
    processed_image = loader_result["image"]
    saved_image_path = loader_result["saved_image_path"]
    print(f"✅ Image loaded: {processed_image.size}")
    if saved_image_path:
        print(f"✅ Saved to: {saved_image_path}")
    
    # Step 2: Run OCR
    print("\n[2/3] ImageOCR: Extracting text with OCR...")
    ocr = ImageOCR(cfg_path)
    ocr_result = ocr.run(image=processed_image)
    
    ocr_items = ocr_result["ocr_results"]
    resize_ratio = ocr_result["resize_ratio"]
    print(f"✅ OCR completed: {len(ocr_items)} text regions detected")
    if resize_ratio:
        print(f"   Resize ratio: {resize_ratio}")
    
    # Step 3: Overlay text
    print("\n[3/3] ImageOverlay: Overlaying text on image...")
    overlay = ImageOverlay(cfg_path)
    output_path = overlay.run()
    
    print(f"✅ Overlay completed: {output_path}")
    
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"\nFinal output: {output_path}")
    
    return {
        "loader_result": loader_result,
        "ocr_result": ocr_result,
        "output_path": output_path,
    }


if __name__ == "__main__":
    main()