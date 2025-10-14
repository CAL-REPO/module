# -*- coding: utf-8 -*-
"""Test script for 3-entrypoint image pipeline.

Demonstrates the complete workflow:
1. ImageLoader - Load and optionally resize image
2. ImageOCR - Run OCR and get results dict with resize_ratio
3. ImageOverlay - Overlay OCR results on original image
"""

from pathlib import Path
from PIL import Image
import sys

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from pillow_utils import ImageLoader, ImageLoaderPolicy, ImageOverlay, ImageOverlayPolicy, ImageSourcePolicy, ImagePolicy, OverlayFontPolicy
from ocr_utils import ImageOCR, OcrPolicy


def test_pipeline(image_path: Path):
    """Test complete pipeline: load → ocr → overlay."""
    
    print("=" * 70)
    print("3-Entrypoint Image Pipeline Test")
    print("=" * 70)
    
    # ========================================================================
    # Entrypoint 1: ImageLoader
    # ========================================================================
    print("\n[1/3] ImageLoader - Loading image")
    print("-" * 70)
    
    loader_policy = ImageLoaderPolicy(
        src_path=image_path,
        # Optional: save copy, resize, etc.
    )
    loader = ImageLoader(loader_policy)
    result = loader.run()
    
    print(f"✅ Loaded: {result['image'].size} {result['image'].mode}")
    print(f"   Metadata: {result['metadata']}")
    
    # ========================================================================
    # Entrypoint 2: ImageOCR
    # ========================================================================
    print("\n[2/3] ImageOCR - Running OCR")
    print("-" * 70)
    
    ocr_policy = OcrPolicy(
        file={"file_path": str(image_path), "save_img": False, "save_ocr_meta": True},
        preprocess={"max_width": 1024},  # Resize for OCR
        provider={"langs": ["ch", "en"], "min_conf": 0.3},
    )
    
    try:
        ocr = ImageOCR(ocr_policy)
        ocr_result = ocr.run()
        
        print(f"✅ OCR Complete:")
        print(f"   Image: {ocr_result['image_meta']['width']}x{ocr_result['image_meta']['height']}")
        print(f"   Resize ratio: {ocr_result['resize_ratio']}")
        print(f"   OCR items: {len(ocr_result['ocr_results'])}")
        
        # Print first few OCR results
        for idx, item in enumerate(ocr_result['ocr_results'][:3], 1):
            print(f"   [{idx}] '{item['text']}' (conf: {item['conf']:.2f})")
        
    except Exception as e:
        print(f"❌ OCR failed: {e}")
        print("   Skipping overlay test")
        return
    
    # ========================================================================
    # Entrypoint 3: ImageOverlay
    # ========================================================================
    print("\n[3/3] ImageOverlay - Overlaying OCR results")
    print("-" * 70)
    
    overlay_policy = ImageOverlayPolicy(
        source=ImageSourcePolicy(path=image_path),  # pyright: ignore
        output=ImagePolicy(  # pyright: ignore
            directory=image_path.parent / "output",
            suffix="_overlay",
        ),
        ocr_results=ocr_result['ocr_results'],
        resize_ratio=ocr_result['resize_ratio'],  # Apply coordinate transformation
        font=OverlayFontPolicy(  # pyright: ignore
            family="arial.ttf",
            size=20,
            fill="#FF0000",
        ),
        background_opacity=0.3,
    )
    
    try:
        overlay = ImageOverlay(overlay_policy)
        output_path, output_meta = overlay.run()
        
        print(f"✅ Overlay Complete:")
        print(f"   Output: {output_path}")
        print(f"   Size: {output_meta.width}x{output_meta.height} if output_meta else 'N/A'}")
        
    except Exception as e:
        print(f"❌ Overlay failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Pipeline test complete!")
    print("=" * 70)


if __name__ == "__main__":
    # Test with first available image in _public/01.IMAGES/
    images_dir = Path(__file__).parent.parent.parent / "_public" / "01.IMAGES"
    
    # Find first JPG/PNG
    for category_dir in images_dir.iterdir():
        if not category_dir.is_dir():
            continue
        
        for img_file in category_dir.glob("*.[jJ][pP][gG]"):
            print(f"Testing with: {img_file}")
            test_pipeline(img_file)
            break
        else:
            # Try PNG
            for img_file in category_dir.glob("*.[pP][nN][gG]"):
                print(f"Testing with: {img_file}")
                test_pipeline(img_file)
                break
        
        # Found image, stop searching
        if img_file:
            break
    else:
        print("No test images found in _public/01.IMAGES/")
        print("Please provide an image path manually.")
