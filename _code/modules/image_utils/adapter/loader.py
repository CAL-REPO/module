"""ImageLoader: First entrypoint for pillow_utils.

Loads images with optional processing, copy, and metadata persistence.
Uses ImageLoaderPolicy from policy.py which combines source, image, meta, and processing configs.

Core features:
- Load image from source (ImageFilePolicy)
- Optional processing (resize, blur, convert)
- Optional save_copy to disk (ImagePolicy with FSO_utils)
- Metadata always generated, optional save_meta (ImageMetaPolicy)
- Supports YAML config + **kwargs runtime override
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple, Any, Dict, Union

from PIL import Image

from fso_utils import FSONamePolicy, FSOOpsPolicy, ExistencePolicy, FSOPathBuilder
from log_utils import LogManager, LogPolicy
from path_utils.os_paths import OSPath
from modules.cfg_utils import ConfigLoader
from ..core.policy import ImageLoaderPolicy


class ImageLoader:
    """First entrypoint: Loads image with optional processing and persistence.
    
    Uses ImageLoaderPolicy which combines:
    - source: ImageFilePolicy (path, must_exist, convert_mode)
    - image: ImagePolicy (save_copy, directory, filename, suffix, etc.)
    - meta: ImageMetaPolicy (save_meta, directory, filename)
    - processing: ImageProcessingPolicy (resize_to, blur_radius, convert_mode)
    
    Supports YAML config + **kwargs runtime override.
    """

    def __init__(self, policy_or_path: Union[ImageLoaderPolicy, str, Path], **kwargs: Any):
        """Initialize with policy or YAML path, optional **kwargs override.
        
        The ConfigLoader will automatically detect the 'pillow' section from:
        - Section-based YAML: pillow: { source: {...}, image: {...}, ... }
        - Direct YAML: source: {...}, image: {...}, ...
        - Unified config file with multiple sections
        """
        if isinstance(policy_or_path, (str, Path)):
            # ConfigLoader auto-detects 'pillow' section from ImageLoaderPolicy name
            cfg = ConfigLoader(policy_or_path).as_model(ImageLoaderPolicy)
            if kwargs:
                policy_dict = cfg.model_dump()
                policy_dict.update(kwargs)
                self.policy = ImageLoaderPolicy(**policy_dict)
            else:
                self.policy = cfg
        elif isinstance(policy_or_path, ImageLoaderPolicy):
            if kwargs:
                policy_dict = policy_or_path.model_dump()
                policy_dict.update(kwargs)
                self.policy = ImageLoaderPolicy(**policy_dict)
            else:
                self.policy = policy_or_path
        else:
            raise TypeError(f"Expected ImageLoaderPolicy or path, got {type(policy_or_path)}")
        
        # Setup logger
        log_policy = kwargs.get('log_policy') or LogPolicy()  # pyright: ignore
        self.logger = LogManager(name="ImageLoader", policy=log_policy).setup()

    def _get_default_dir(self) -> Path:
        """Get default directory using path_utils.downloads()."""
        return OSPath.downloads()
    
    def _build_dest_path(self, source_path: Path) -> Path:
        """Build image save path using FSO_utils with policy settings."""
        # Determine directory: policy.image.directory or path_utils.download()
        target_dir = self.policy.image.directory or self._get_default_dir()
        target_dir = target_dir.resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine filename: explicit or auto-generated
        if self.policy.image.filename:
            name = self.policy.image.filename
        else:
            name = f"{source_path.stem}{self.policy.image.suffix}{source_path.suffix}"
        
        # Build with FSO_utils
        name_policy = FSONamePolicy(  # pyright: ignore
            as_type="file",
            name=Path(name).stem,
            extension=Path(name).suffix,
            tail_mode="counter" if self.policy.image.ensure_unique else None,
            ensure_unique=self.policy.image.ensure_unique,
        )
        ops_policy = FSOOpsPolicy(  # pyright: ignore
            as_type="file",
            exist=ExistencePolicy(create_if_missing=True),  # pyright: ignore
        )
        builder = FSOPathBuilder(base_dir=target_dir, name_policy=name_policy, ops_policy=ops_policy)
        return builder()

    def _build_meta_path(self, source_path: Path) -> Path:
        """Build metadata JSON path using policy settings."""
        # Determine directory: policy.meta.directory or path_utils.download()
        meta_dir = self.policy.meta.directory or self._get_default_dir()
        meta_dir = meta_dir.resolve()
        meta_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine filename: explicit or auto-generated
        if self.policy.meta.filename:
            filename = self.policy.meta.filename
        else:
            filename = f"{source_path.stem}_meta.json"
        
        return meta_dir / filename

    def run(self, image: Optional[Image.Image] = None) -> Dict[str, Any]:
        """Execute image loading pipeline with new policy structure.
        
        Args:
            image: Optional pre-loaded PIL Image (avoids re-loading)
            
        Returns:
            Dict with: image, metadata, saved_image_path, saved_meta_path
        """
        source_path = self.policy.source.path
        
        self.logger.info("=" * 70)
        self.logger.info(f"[ImageLoader] Source: {source_path}")
        self.logger.info("=" * 70)
        
        try:
            # Step 1: Load image
            if source_path.exists() or not self.policy.source.must_exist:
                img = image or Image.open(source_path)
            else:
                raise FileNotFoundError(f"Source not found: {source_path}")
            
            orig_width, orig_height = img.size
            orig_mode = img.mode
            orig_format = img.format
            self.logger.info(f"[Load] {orig_width}x{orig_height} {orig_mode} {orig_format or 'unknown'}")
            
            # Optional source mode conversion
            if self.policy.source.convert_mode:
                img = img.convert(self.policy.source.convert_mode)
                self.logger.info(f"[Load] Converted to: {self.policy.source.convert_mode}")
            
            # Step 2: Process image (resize, blur, convert)
            processed_img = img
            width_ratio = height_ratio = 1.0
            
            if self.policy.processing.resize_to:
                new_width, new_height = self.policy.processing.resize_to
                processed_img = processed_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                width_ratio = new_width / orig_width
                height_ratio = new_height / orig_height
                self.logger.info(
                    f"[Process] Resize: {orig_width}x{orig_height} → {new_width}x{new_height} "
                    f"(ratio: {width_ratio:.3f}, {height_ratio:.3f})"
                )
            
            if self.policy.processing.blur_radius:
                from PIL import ImageFilter
                processed_img = processed_img.filter(
                    ImageFilter.GaussianBlur(self.policy.processing.blur_radius)
                )
                self.logger.info(f"[Process] Blur: radius={self.policy.processing.blur_radius}")
            
            if self.policy.processing.convert_mode:
                processed_img = processed_img.convert(self.policy.processing.convert_mode)
                self.logger.info(f"[Process] Convert: {self.policy.processing.convert_mode}")
            
            new_width, new_height = processed_img.size
            
            # Step 3: Save image copy if requested
            saved_image_path = None
            if self.policy.image.save_copy:
                dest_path = self._build_dest_path(source_path)
                
                save_format = self.policy.image.format or orig_format
                save_kwargs = {}
                if save_format in ['JPEG', 'JPG', 'WEBP']:
                    save_kwargs['quality'] = self.policy.image.quality
                
                processed_img.save(dest_path, format=save_format, **save_kwargs)
                saved_image_path = dest_path
                self.logger.info(f"[Save] Image: {dest_path}")
            else:
                self.logger.info("[Save] Image save skipped (save_copy=False)")
            
            # Step 4: Build metadata (always generated)
            metadata = {
                "source": {
                    "path": str(source_path),
                    "width": orig_width,
                    "height": orig_height,
                    "mode": orig_mode,
                    "format": orig_format,
                },
                "processed": {
                    "width": new_width,
                    "height": new_height,
                    "mode": processed_img.mode,
                },
                "ratios": {
                    "width": width_ratio,
                    "height": height_ratio,
                },
                "saved_image_path": str(saved_image_path) if saved_image_path else None,
            }
            
            # Step 5: Save metadata if requested
            saved_meta_path = None
            if self.policy.meta.save_meta:
                meta_path = self._build_meta_path(source_path)
                meta_path.write_text(
                    json.dumps(metadata, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
                saved_meta_path = meta_path
                metadata["saved_meta_path"] = str(meta_path)
                self.logger.info(f"[Save] Metadata: {meta_path}")
            else:
                metadata["saved_meta_path"] = None
                self.logger.info("[Save] Metadata save skipped (save_meta=False)")
            
            self.logger.info("=" * 70)
            self.logger.info("[ImageLoader] ✅ Complete")
            self.logger.info("=" * 70)
            
            return {
                "image": processed_img,
                "metadata": metadata,
                "saved_image_path": saved_image_path,
                "saved_meta_path": saved_meta_path,
            }
            
        except Exception as e:
            self.logger.error(f"[ImageLoader] ❌ Error: {e}", exc_info=True)
            raise