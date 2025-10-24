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
        """Initialize ImageLoad adapter with dual logging support.
        
        Logging Strategy:
            1. Primary Logger (Parent): 통합 로그 - 전체 파이프라인 기록
            2. Secondary Logger (Module): 모듈별 로그 - 상세 디버깅용 (선택적)
        """
        self.policy = self._load_config(cfg_like, **overrides)
        
        # ========================================
        # Primary Logger: Parent logger (통합 로그)
        # ========================================
        if log_manager:
            self.log = log_manager.logger
            self._parent_log_manager = log_manager
        elif self.policy.log:
            self._parent_log_manager = LogManager(self.policy.log)
            self.log = self._parent_log_manager.logger
        else:
            self._parent_log_manager = None
            self.log = LogManager({"enabled": False}).logger
        
        # ========================================
        # Secondary Logger: Module logger (모듈별 로그 - 선택적)
        # ========================================
        self._module_log_manager = None
        self._module_logger = None
        
        if self.policy.log and self.policy.log.enabled and log_manager:
            # Parent logger가 있고 policy.log도 enabled면 모듈 전용 LogManager 생성
            self._module_log_manager = LogManager(self.policy.log)
            self._module_logger = self._module_log_manager.logger
        
        self.log.debug("ImageLoad initialized with dual logging")
        if self._module_logger:
            self._module_logger.debug("Module-specific logger enabled for detailed debugging")
    
    def _load_config(self, cfg_like, **overrides) -> ImageLoadPolicy:
        """Load ImageLoadPolicy."""
        from cfg_utils.services.config_like_loader import ConfigLikeLoader
        
        return ConfigLikeLoader.load(
            cfg_like=cfg_like,
            policy_class=ImageLoadPolicy,
            module_file=__file__,
            config_filename="image_load.yaml",
            **overrides
        )
    
    def _log_both(self, level: str, message: str, **kwargs):
        """Log to both parent and module loggers.
        
        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            **kwargs: Additional context (e.g., exc_info=True)
        """
        # Primary: Parent logger (항상 기록)
        getattr(self.log, level)(message, **kwargs)
        
        # Secondary: Module logger (있으면 기록)
        if self._module_logger:
            getattr(self._module_logger, level)(message, **kwargs)
    
    def run(
        self, 
        source: Union[Image.Image, Path, str],
        source_path: Optional[Union[Path, str]] = None,
        **overrides: Any
    ) -> Dict[str, Any]:
        """Process image with optional save/meta.
        
        Args:
            source: PIL Image OR file path
            source_path: Original file path for save/meta (optional)
            **overrides: Runtime overrides (접두사 없음, 예: save__enabled=True, save__name__name="custom")
        
        Returns:
            dict with success, image, original_size, processed_size, processing, error
        
        Note:
            ⚠️ overrides는 모듈 내부 KeyPath 형식 (접두사 없음)
            ⚠️ Composite Adapter에서 image_load__ 접두사 제거 후 전달
            ⚠️ source_path.stem이 자동으로 save.name.name 기본값이 됨
        """
        from keypath_utils import KeyPathDict
        
        # Runtime override 적용
        if overrides:
            override_dict = KeyPathDict.to_nested_dict(overrides)
            working_policy = self.policy.model_copy(deep=True)
            # override_dict를 working_policy에 병합
            policy_dict = working_policy.model_dump()
            kp_dict = KeyPathDict(policy_dict)
            kp_dict.merge(override_dict, deep=True, inplace=True)
            working_policy = ImageLoadPolicy(**kp_dict.data)
        else:
            working_policy = self.policy
        
        result = {
            "success": False,
            "image": None,
            "original_size": None,
            "processed_size": None,
            "processing": {},
            "error": None,
        }
        
        # Determine source_path for save/meta
        actual_source_path = None
        if source_path:
            actual_source_path = resolve(Path(source_path))
        elif isinstance(source, (Path, str)):
            actual_source_path = resolve(Path(source))
        
        try:
            # 1. Load image
            if isinstance(source, Image.Image):
                img = source
                self._log_both("info", f"Processing Image object: {img.size} {img.mode}")
            else:
                source_file = resolve(Path(source))
                self._log_both("info", f"Loading from: {source_file}")
                img = Image.open(source_file)
                img = ImageOps.exif_transpose(img)
            
            result["original_size"] = img.size
            
            # Module logger: detailed info
            if self._module_logger:
                self._module_logger.debug(f"Original size: {img.size}, mode: {img.mode}")
            
            # 2. Process
            processed_img = img.copy()
            processing_applied = {}
            
            if working_policy.process.resize_to:
                if self._module_logger:
                    self._module_logger.debug(f"Resizing to: {working_policy.process.resize_to}")
                processed_img = processed_img.resize(
                    working_policy.process.resize_to,
                    Image.Resampling.LANCZOS,
                )
                processing_applied["resize_to"] = working_policy.process.resize_to
            
            if working_policy.process.blur_radius:
                if self._module_logger:
                    self._module_logger.debug(f"Applying blur radius: {working_policy.process.blur_radius}")
                processed_img = processed_img.filter(
                    ImageFilter.GaussianBlur(radius=working_policy.process.blur_radius)
                )
                processing_applied["blur_radius"] = working_policy.process.blur_radius
            
            if working_policy.process.convert_mode:
                if self._module_logger:
                    self._module_logger.debug(f"Converting mode to: {working_policy.process.convert_mode}")
                processed_img = processed_img.convert(working_policy.process.convert_mode)
                processing_applied["convert_mode"] = working_policy.process.convert_mode
            
            result["processed_size"] = processed_img.size
            result["processing"] = processing_applied
            result["image"] = processed_img
            result["success"] = True
            
            self._log_both("success", f"Completed: {result['original_size']} -> {result['processed_size']}")
            
            # 3. ✨ Save image (if enabled and source_path available)
            if working_policy.save.save_copy and actual_source_path:
                self._save_image(processed_img, actual_source_path, working_policy)
            
            # 4. ✨ Save metadata (if enabled and source_path available)
            if working_policy.meta.save_meta and actual_source_path:
                self._save_metadata(result, actual_source_path, working_policy)
            
        except FileNotFoundError as e:
            result["error"] = f"File not found: {e}"
            self._log_both("error", result["error"])
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            self._log_both("error", result["error"], exc_info=True)
        
        return result
    
    def _save_image(self, image: Image.Image, source_path: Path, policy: ImageLoadPolicy):
        """Save processed image using fso_utils.
        
        Args:
            image: Processed PIL Image
            source_path: Original source file path for name generation
            policy: ImageLoadPolicy (working_policy from run())
        """
        try:
            from fso_utils import FSOPathBuilder
            from path_utils import downloads
            
            # Use directory or downloads() as fallback
            target_dir = policy.save.directory or downloads()
            
            # Extract source stem for name override
            source_stem = source_path.stem
            
            # Build output path using FSOPathBuilder
            builder = FSOPathBuilder(
                base_dir=target_dir,
                name_policy=policy.save.name,
                ops_policy=policy.save.ops
            )
            # Override name with source stem (if policy.save.name.name is still template)
            output_path = builder.build(name=source_stem)
            
            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with format/quality
            save_kwargs = {}
            if policy.save.format:
                save_kwargs["format"] = policy.save.format
            if policy.save.format in ("JPEG", "WebP"):
                save_kwargs["quality"] = policy.save.quality
            
            image.save(output_path, **save_kwargs)
            
            self._log_both("info", f"Image saved: {output_path}")
            
        except Exception as e:
            self._log_both("error", f"Failed to save image: {e}", exc_info=True)
    
    def _save_metadata(self, result: Dict[str, Any], source_path: Path, policy: ImageLoadPolicy):
        """Save processing metadata using fso_utils.
        
        Args:
            result: Processing result dict
            source_path: Original source file path for name generation
            policy: ImageLoadPolicy (working_policy from run())
        """
        try:
            import json
            from fso_utils import FSOPathBuilder
            
            # Use directory or same as source
            target_dir = policy.meta.directory
            if target_dir is None:
                target_dir = source_path.parent
            
            # Extract source stem for name override
            source_stem = source_path.stem
            
            # Build metadata path using FSOPathBuilder
            builder = FSOPathBuilder(
                base_dir=target_dir,
                name_policy=policy.meta.name,
                ops_policy=policy.meta.ops
            )
            # Override name with source stem
            meta_path = builder.build(name=source_stem)
            
            # Extract metadata
            metadata = {
                "original_size": result["original_size"],
                "processed_size": result["processed_size"],
                "processing": result["processing"],
                "success": result["success"]
            }
            
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            self._log_both("info", f"Metadata saved: {meta_path}")
            
        except Exception as e:
            self._log_both("error", f"Failed to save metadata: {e}", exc_info=True)
