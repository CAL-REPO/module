# -*- coding: utf-8 -*-
"""ImageOverlay: Overlay text/graphics on images.

This module provides the third entrypoint for pillow_utils:
1. Accepts manual overlay specifications (text, coordinates, fonts)
2. Renders overlays using renderer module
3. Returns only the overlaid image (no metadata)

Note: OCR+translation integration is handled by translate module entrypoint.
This module accepts only pre-transformed overlay specifications from YAML or dict override.

EntryPoint: ImageOverlay class with ImageOverlayPolicy
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from PIL import Image, ImageDraw

from log_utils import LogManager, LogPolicy
from modules.cfg_utils import ConfigLoader
from font_utils import FontPolicy
from .io import ImageReader, ImageWriter
from .policy import ImageOverlayPolicy, OverlayTextPolicy
from .renderer import OverlayTextRenderer


class ImageOverlay:
    """Image overlay entrypoint - renders text overlays from manual specifications.
    
    This class:
    1. Loads the source image
    2. Renders overlays using OverlayRenderer with manual specifications
    3. Saves and returns only the overlaid image path
    
    Note: All overlay specifications (text, coordinates) must be provided via:
    - YAML configuration file
    - Runtime dict override via **kwargs
    
    OCR+translation integration is handled by translate module.
    
    Usage:
        # From YAML config
        overlay = ImageOverlay('overlay_config.yaml')
        result_path = overlay.run()
        
        # With runtime override
        from pillow_utils.policy import ImageOverlayPolicy, ImageSourcePolicy, OverlayTextPolicy
        
        policy = ImageOverlayPolicy(
            source=ImageSourcePolicy(path=img_path),
            texts=[
                OverlayTextPolicy(
                    text="Hello", 
                    polygon=[(10,10), (100,10), (100,50), (10,50)]
                )
            ]
        )
        overlay = ImageOverlay(policy)
        result_path = overlay.run()
    """
    
    def __init__(
        self, 
        policy_or_path: Union[ImageOverlayPolicy, str, Path],
        **kwargs
    ):
        """Initialize ImageOverlay with policy or config path.
        
        The ConfigLoader will automatically detect the 'overlay' section from:
        - Section-based YAML: overlay: { source: {...}, output: {...}, ... }
        - Direct YAML: source: {...}, output: {...}, ...
        - Unified config file with multiple sections
        
        Args:
            policy_or_path: ImageOverlayPolicy instance or path to YAML config
            **kwargs: Runtime overrides for policy fields
        """
        # Load policy
        if isinstance(policy_or_path, (str, Path)):
            loader = ConfigLoader(policy_or_path)
            # ConfigLoader auto-detects 'overlay' section from ImageOverlayPolicy name
            base_policy = loader.as_model(ImageOverlayPolicy)
            # Apply runtime overrides
            if kwargs:
                self.policy = ImageOverlayPolicy(**{**base_policy.model_dump(), **kwargs})
            else:
                self.policy = base_policy
        elif isinstance(policy_or_path, ImageOverlayPolicy):
            self.policy = policy_or_path
        else:
            raise TypeError(f"Expected ImageOverlayPolicy or path, got {type(policy_or_path)}")
        
        # Setup logger
        self.logger = LogManager(name="ImageOverlay").setup()
    
    def run(self) -> Path:
        """Execute image overlay pipeline.
        
        Returns:
            Path to overlaid image
        """
        self.logger.info("=" * 70)
        self.logger.info("[ImageOverlay] Starting overlay pipeline")
        self.logger.info(f"[ImageOverlay] Source: {self.policy.source.path}")
        self.logger.info("=" * 70)
        
        try:
            # Step 1: Load source image
            self.logger.info("[Load] Reading source image")
            reader = ImageReader(self.policy.source)
            image, _ = reader.load()
            self.logger.info(f"[Load] Image loaded: {image.size} {image.mode}")
            
            # Step 2: Get text policies from configuration
            text_policies = self.policy.texts
            self.logger.info(f"[Overlay] Using {len(text_policies)} text overlays")
            
            if not text_policies:
                self.logger.warning("[Overlay] No text policies to render, saving original image")
                writer = ImageWriter(self.policy.output, self.policy.meta)
                output_path = writer.save_image(image, self.policy.source.path)
                self.logger.info(f"[Save] Saved to: {output_path}")
                return output_path
            
            # Step 3: Render overlays
            self.logger.info(f"[Render] Rendering {len(text_policies)} overlays")
            
            # Convert image to RGBA for compositing
            if image.mode != "RGBA":
                image = image.convert("RGBA")
            
            # Create overlay layer
            overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Render each text
            text_renderer = OverlayTextRenderer(draw)
            for idx, text_config in enumerate(text_policies, 1):
                self.logger.info(f"[Render] Text {idx}/{len(text_policies)}: '{text_config.text[:30]}...'")
                text_renderer.render_text(text_config)
            
            # Apply background if specified
            if self.policy.background_opacity > 0:
                alpha = int(max(0.0, min(1.0, self.policy.background_opacity)) * 255)
                background = Image.new("RGBA", image.size, (255, 255, 255, alpha))
                overlay = Image.alpha_composite(background, overlay)
                self.logger.info(f"[Background] Applied opacity: {self.policy.background_opacity}")
            
            # Composite
            composed = Image.alpha_composite(image, overlay)
            self.logger.info("[Composite] Overlaid text onto image")
            
            # Step 4: Save result
            writer = ImageWriter(self.policy.output, self.policy.meta)
            output_path = writer.save_image(composed.convert("RGB"), self.policy.source.path)
            self.logger.info(f"[Save] Saved to: {output_path}")
            
            self.logger.info("=" * 70)
            self.logger.info("[ImageOverlay] ✅ Completed successfully")
            self.logger.info("=" * 70)
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"[ImageOverlay] ❌ Error: {e}", exc_info=True)
            raise
