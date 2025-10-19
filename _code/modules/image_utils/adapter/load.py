# -*- coding: utf-8 -*-
"""ImageLoad - Core image processing adapter (Translate pattern)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from PIL import Image, ImageFilter, ImageOps

from logs_utils import LogManager
from path_utils import resolve

from ..core.policy import ImageLoadPolicy


class ImageLoad:
    """Image processing adapter following Translate pattern.
    
    Policy and __init__: NO source
    run(): receives Image object OR file path
    """
    
    def __init__(
        self,
        cfg_like: Union[Path, str, dict, ImageLoadPolicy, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize ImageLoad adapter."""
        self.policy = self._load_config(cfg_like, **overrides)
        
        if log_manager:
            self.log = log_manager.logger
        elif self.policy.log:
            self.log = LogManager(self.policy.log).logger
        else:
            self.log = LogManager({"enabled": False}).logger
        
        self.log.debug("ImageLoad initialized")
    
    def _load_config(self, cfg_like, **overrides) -> ImageLoadPolicy:
        """Load ImageLoadPolicy."""
        from cfg_utils.services.config_like_loader import ConfigLikeLoader
        
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=ImageLoadPolicy,
            caller_file=__file__,
            default_config_filename="image.yaml",
            **overrides
        )
    
    def run(self, source: Union[Image.Image, Path, str]) -> Dict[str, Any]:
        """Process image.
        
        Args:
            source: PIL Image OR file path
        
        Returns:
            dict with success, image, original_size, processed_size, processing, error
        """
        result = {
            "success": False,
            "image": None,
            "original_size": None,
            "processed_size": None,
            "processing": {},
            "error": None,
        }
        
        try:
            # 1. Load image
            if isinstance(source, Image.Image):
                img = source
                self.log.info(f"Processing Image object: {img.size} {img.mode}")
            else:
                source_path = resolve(Path(source))
                self.log.info(f"Loading from: {source_path}")
                img = Image.open(source_path)
                img = ImageOps.exif_transpose(img)
            
            result["original_size"] = img.size
            
            # 2. Process
            processed_img = img.copy()
            processing_applied = {}
            
            if self.policy.process.resize_to:
                processed_img = processed_img.resize(
                    self.policy.process.resize_to,
                    Image.Resampling.LANCZOS,
                )
                processing_applied["resize_to"] = self.policy.process.resize_to
            
            if self.policy.process.blur_radius:
                processed_img = processed_img.filter(
                    ImageFilter.GaussianBlur(radius=self.policy.process.blur_radius)
                )
                processing_applied["blur_radius"] = self.policy.process.blur_radius
            
            if self.policy.process.convert_mode:
                processed_img = processed_img.convert(self.policy.process.convert_mode)
                processing_applied["convert_mode"] = self.policy.process.convert_mode
            
            result["processed_size"] = processed_img.size
            result["processing"] = processing_applied
            result["image"] = processed_img
            result["success"] = True
            
            self.log.success(f"Completed: {result['original_size']} -> {result['processed_size']}")
            
        except FileNotFoundError as e:
            result["error"] = f"File not found: {e}"
            self.log.error(result["error"])
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            self.log.error(result["error"])
        
        return result
