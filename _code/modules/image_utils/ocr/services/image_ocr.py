"""ImageOCR: OCR processing pipeline (2nd entrypoint for pillow_utils).

This module provides OCR workflow as standalone entrypoint:
1. Load image (can reuse ImageLoader configuration)
2. Optional resize for OCR (tracks resize_ratio for overlay coordinate transformation)
3. Run OCR using PaddleOCR provider
4. Post-process results (text cleaning, deduplication)
5. Return dict with img, metadata, resize_ratio, geometry
6. Save OCR metadata JSON if configured

Returns dict format for easy integration with image_overlay.py:
{
    'image': PIL.Image.Image (original or resized),
    'image_meta': {width, height, mode, ...},
    'resize_ratio': (width_ratio, height_ratio) or None,
    'ocr_results': [{text, bbox, polygon, conf, lang}, ...],
    'metadata': {...},  # Full OCR run metadata
}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import time
import json
from PIL import Image

from pillow_utils.image_loader import ImageLoader, ImageLoaderPolicy
from log_utils import LogManager
from modules.cfg_utils import ConfigLoader
from modules.data_utils import StringOps, GeometryOps
from ..core.policy import OcrPolicy, OCRItem
from .providers import build_paddle_instances, predict_with_paddle


class ImageOCR:
    """OCR pipeline for complete image→OCR→results workflow.
    
    Features:
    - Image loading (from file or pre-loaded PIL Image)
    - OCR execution via PaddleOCR
    - Text post-processing (cleaning, filtering)
    - Bounding box deduplication
    - OCR metadata persistence
    - Structured logging
    """
    
    def __init__(self, policy_or_path: Union[OcrPolicy, str, Path]):
        """Initialize ImageOCR with policy or config path."""
        # Load OcrPolicy from path or use directly
        if isinstance(policy_or_path, (str, Path)):
            loader = ConfigLoader(policy_or_path)
            self.policy = loader.as_model(OcrPolicy)
        elif isinstance(policy_or_path, OcrPolicy):
            self.policy = policy_or_path
        else:
            raise TypeError(f"policy_or_path must be OcrPolicy or path, got {type(policy_or_path)}")
        
        # Setup OCR-specific logger
        self.logger = LogManager(name="ImageOCR", policy=self.policy.log).setup() # pyright: ignore
    
    def _postprocess_items(
        self,
        raw_items: List[OCRItem],
        prefer_lang_order: List[str] = ["ch", "en"]
    ) -> List[OCRItem]:
        """Post-process OCR items: clean text, filter, and deduplicate by IoU."""
        self.logger.info(f"[PostProcess] Processing {len(raw_items)} raw items")
        
        # Step 1: Clean text and filter
        out = []
        for it in raw_items:
            new_text = StringOps.strip_special_chars(it.text)
            if not new_text or StringOps.is_alphanumeric_only(new_text):
                continue
            it.text = new_text
            out.append(it)
        
        self.logger.info(f"[PostProcess] After text cleaning: {len(out)} items")
        
        # Step 2: Deduplicate by bbox IoU
        kept: List[OCRItem] = []
        
        def lang_rank(lang: str) -> int:
            return prefer_lang_order.index(lang) if lang in prefer_lang_order else len(prefer_lang_order)
        
        items_sorted = sorted(out, key=lambda it: (-float(it.conf), lang_rank(it.lang)))
        
        for it in items_sorted:
            if any(GeometryOps.bbox_intersection_over_union(it.bbox, k.bbox) >= 0.7 for k in kept):
                continue
            kept.append(it)
        
        self.logger.info(f"[PostProcess] After deduplication: {len(kept)} items")
        return kept
    
    def _run_impl(self, image: Optional[Image.Image] = None) -> Dict[str, Any]:
        """Run OCR and return dict with image, metadata, and geometry."""
        t0_all = time.time()
        
        # Get source path
        src_path = self.policy.source.path if self.policy.source else Path(self.policy.file.file_path) # pyright: ignore
        
        self.logger.info("=" * 70)
        self.logger.info(f"[ImageOCR] Starting: {src_path}")
        self.logger.info("=" * 70)
        
        try:
            # Step 1: Load original image
            t0 = time.time()
            img_original = image or Image.open(src_path).convert("RGB")
            orig_width, orig_height = img_original.size
            t_load = int((time.time() - t0) * 1000)
            self.logger.info(f"[Image] Loaded {orig_width}x{orig_height} in {t_load}ms")
            
            # Step 2: Optional resize for OCR (track resize_ratio)
            img_for_ocr = img_original
            resize_ratio = None
            
            mw = self.policy.preprocess.max_width
            if mw and img_original.width > mw:
                width_ratio = mw / float(img_original.width)
                height_ratio = width_ratio  # Keep aspect ratio
                new_size = (mw, int(round(img_original.height * height_ratio)))
                img_for_ocr = img_original.resize(new_size, Image.Resampling.LANCZOS)
                resize_ratio = (width_ratio, height_ratio)
                self.logger.info(
                    f"[Image] Resized to {new_size} for OCR "
                    f"(ratio: {width_ratio:.3f}, {height_ratio:.3f})"
                )
            
            # Step 3: Run OCR on (possibly resized) image
            t0 = time.time()
            insts = build_paddle_instances(
                self.policy.provider.langs,
                device=self.policy.provider.paddle_device,
                use_angle_cls=self.policy.provider.paddle_use_angle_cls,
                existing=self.policy.provider.paddle_instance
            )
            raw_items, timings_each = predict_with_paddle(
                img_for_ocr,
                self.policy.provider.langs,
                insts,
                min_conf=self.policy.provider.min_conf
            )
            t_ocr = int((time.time() - t0) * 1000)
            self.logger.info(f"[OCR] Detected {len(raw_items)} items in {t_ocr}ms")
            
            self.policy.provider.paddle_instance = insts
            items_final = self._postprocess_items(raw_items)
            
            # Step 4: Determine output path
            if self.policy.file.save_img and self.policy.file.save_dir:
                dest_dir = Path(self.policy.file.save_dir)
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / f"{src_path.stem}{self.policy.file.save_suffix}{src_path.suffix}"
                img_for_ocr.save(dest_path)
                self.logger.info(f"[Image] Saved OCR image to {dest_path}")
            else:
                dest_path = src_path
            
            # Step 5: Build image metadata
            image_meta = {
                "src_path": str(src_path),
                "width": orig_width,
                "height": orig_height,
                "mode": img_original.mode,
                "format": img_original.format,
            }
            
            # Step 6: Build OCR results dict list (for image_overlay)
            # Convert quad [[x,y], [x,y], ...] to polygon [(x,y), (x,y), ...]
            ocr_results = [
                {
                    "text": it.text,
                    "bbox": it.bbox,
                    "polygon": [(pt[0], pt[1]) for pt in it.quad],  # quad to polygon
                    "conf": it.conf,
                    "lang": it.lang,
                }
                for it in items_final
            ]
            
            # Step 7: Build full metadata
            total_ms = int((time.time() - t0_all) * 1000)
            full_metadata = {
                "schema_version": "ocr-overlay-v1",
                "provider": self.policy.provider.provider,
                "langs": self.policy.provider.langs,
                "preprocess": self.policy.preprocess.model_dump(),
                "timings_ms": {"load": t_load, "ocr": t_ocr, "ocr_each": timings_each, "total": total_ms},
                "image": image_meta,
                "resize_ratio": resize_ratio,
                "counts": {"raw": len(raw_items), "final": len(items_final)},
                "items": ocr_results,
            }
            
            # Step 8: Save OCR metadata JSON if configured
            saved_meta_path = None
            if self.policy.file.save_ocr_meta:
                meta_dir = Path(self.policy.file.ocr_meta_dir) if self.policy.file.ocr_meta_dir else dest_path.parent
                meta_dir.mkdir(parents=True, exist_ok=True)
                meta_name = self.policy.file.ocr_meta_name or "meta_ocr.json"
                meta_path = meta_dir / meta_name
                meta_path.write_text(json.dumps(full_metadata, ensure_ascii=False, indent=2), encoding="utf-8")
                saved_meta_path = meta_path
                self.logger.info(f"[Metadata] Saved to {meta_path}")
            
            # Step 9: Build return dict
            result_dict = {
                "image": img_original,  # Always return original size image
                "image_meta": image_meta,
                "resize_ratio": resize_ratio,  # For overlay coordinate transformation
                "ocr_results": ocr_results,  # For image_overlay.py
                "metadata": full_metadata,  # Complete metadata
                "meta_path": str(saved_meta_path) if saved_meta_path else None,
            }
            
            self.logger.info("=" * 70)
            self.logger.info(f"[ImageOCR] ✅ Completed in {total_ms}ms: {len(items_final)} items")
            if resize_ratio:
                self.logger.info(f"[ImageOCR] Resize ratio: {resize_ratio} (apply to overlay)")
            self.logger.info("=" * 70)
            
            return result_dict
            
        except Exception as e:
            self.logger.error(f"[ImageOCR] ❌ Error: {e}", exc_info=True)
            raise
    
    def run(self, image: Optional[Image.Image] = None) -> Dict[str, Any]:
        """Run complete OCR pipeline.
        
        Returns:
            Dict containing:
            - image: PIL.Image.Image (original size)
            - image_meta: {src_path, width, height, mode, format}
            - resize_ratio: (width_ratio, height_ratio) or None
            - ocr_results: [{text, bbox, polygon, conf, lang}, ...]
            - metadata: Complete metadata dict
            - meta_path: Path to saved JSON metadata (if saved)
        """
        return self._run_impl(image)