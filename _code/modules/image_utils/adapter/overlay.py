# -*- coding: utf-8 -*-
"""ImageOverlay - Core overlay adapter (Translate pattern).

책임:
1. 이미지에 텍스트/도형 오버레이 실행
2. PIL 기반 레이어 합성 및 렌더링
3. run(image, items) API 제공

translate_utils의 Translate와 동일한 패턴:
- Policy: ImageOverlayPolicy (source 없음)
- __init__: cfg_like만 받음
- run(image, items): Image 객체 + 오버레이 항목 받아서 처리
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image, ImageDraw

from logs_utils import LogManager

from ..core.policy import ImageOverlayPolicy, OverlayItemPolicy


class ImageOverlay:
    """오버레이 처리 adapter (Translate pattern).
    
    translate_utils의 Translate와 동일한 구조:
    - Policy: ImageOverlayPolicy (source 없음)
    - run(image, items): Image 객체 + 오버레이 항목 받아서 처리
    
    Attributes:
        policy: ImageOverlayPolicy 설정
        log: loguru logger
    """
    
    def __init__(
        self,
        cfg_like: Union[Path, str, dict, ImageOverlayPolicy, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize ImageOverlay adapter with dual logging support.
        
        Logging Strategy:
            1. Primary Logger (Parent): 통합 로그 - 전체 파이프라인 기록
            2. Secondary Logger (Module): 모듈별 로그 - 상세 디버깅용 (선택적)
        
        Args:
            cfg_like: ImageOverlayPolicy, YAML 경로, dict, 또는 None
            log_manager: 외부 LogManager (선택사항)
            **overrides: 런타임 오버라이드
        
        Example:
            >>> overlay = ImageOverlay("configs/overlay.yaml")
            >>> overlay = ImageOverlay({"items": [...]})
        """
        # Load policy
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
        
        self.log.debug("ImageOverlay initialized with dual logging")
        if self._module_logger:
            self._module_logger.debug("Module-specific logger enabled for detailed debugging")
    
    # ==========================================================================
    # Config Loading
    # ==========================================================================
    
    def _load_config(self, cfg_like, **overrides) -> ImageOverlayPolicy:
        """Load ImageOverlayPolicy."""
        from cfg_utils.services.config_like_loader import ConfigLikeLoader
        
        return ConfigLikeLoader.load(
            cfg_like=cfg_like,
            policy_class=ImageOverlayPolicy,
            module_file=__file__,
            config_filename="image_overlay.yaml",
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
    
    # ==========================================================================
    # Main API (Translate pattern)
    # ==========================================================================
    
    def run(
        self,
        image: Image.Image,
        items: Optional[List[OverlayItemPolicy]] = None,
        source_path: Optional[Union[Path, str]] = None,
        **overrides: Any
    ) -> Dict[str, Any]:
        """이미지에 텍스트/도형 오버레이 (런타임 override 지원 + save/meta).
        
        Args:
            image: PIL Image 객체
            items: OverlayItemPolicy 리스트 (None이면 policy.items 사용)
            source_path: 원본 파일 경로 (save/meta에 사용, 선택)
            **overrides: 런타임 정책 오버라이드 (KeyPath 형식)
                예: save__directory="output", save__name__name="test"
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "image": PIL.Image.Image,
                "overlaid_items": int,
                "image_size": Tuple[int, int],
                "output_path": Optional[Path],  # save_copy=True인 경우
                "error": Optional[str]
            }
        
        Example:
            >>> overlay = ImageOverlay("config.yaml")
            >>> img = Image.open("test.jpg")
            >>> result = overlay.run(img, source_path="test.jpg")
            >>> overlaid_img = result["image"]
            >>> 
            >>> # 런타임 override
            >>> result = overlay.run(
            ...     img, 
            ...     source_path="test.jpg",
            ...     save__directory="output",
            ...     save__name__name="test"
            ... )
        """
        # 런타임 override 적용
        if overrides:
            from keypath_utils import KeyPathDict
            override_dict = KeyPathDict.to_nested_dict(overrides)
            working_policy = self.policy.model_copy(deep=True)
            
            # Pydantic 모델을 dict로 변환
            policy_dict = working_policy.model_dump()
            
            # KeyPathDict로 deep merge
            kp_dict = KeyPathDict(policy_dict)
            kp_dict.merge(override_dict, deep=True, inplace=True)
            
            # 병합된 dict로 새 Policy 객체 생성
            from ..core.policy import ImageOverlayPolicy
            working_policy = ImageOverlayPolicy(**kp_dict.data)
        else:
            working_policy = self.policy
        
        result = {
            "success": False,
            "image": None,
            "overlaid_items": 0,
            "image_size": image.size,
            "output_path": None,
            "error": None,
        }
        
        try:
            # items 결정 (인자 우선, 없으면 policy.items 사용)
            overlay_items = items or working_policy.items
            
            if not overlay_items:
                self.log.warning("No overlay items to render")
                result["success"] = True
                result["image"] = image
                return result
            
            self.log.info(f"Overlaying {len(overlay_items)} items on image {image.size}...")
            
            # RGBA 변환 (투명도 처리)
            if image.mode != "RGBA":
                img = image.convert("RGBA")
            else:
                img = image.copy()
            
            # 오버레이 레이어 생성
            overlay_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay_layer)
            
            # 렌더러 생성
            from ..services.renderer import OverlayTextRenderer
            renderer = OverlayTextRenderer(draw)
            
            # 각 아이템 렌더링 (전역 설정 주입)
            for idx, item in enumerate(overlay_items):
                try:
                    # 1. 전역 font와 개별 font 병합
                    if working_policy.font is not None:
                        if item.font is None:
                            # 아이템 font 없음 → 전역 font 사용
                            item.font = working_policy.font
                        else:
                            # 아이템 font 있음 → 전역 font와 병합 (아이템 우선)
                            from font_utils import FontPolicy
                            merged_font = working_policy.font.model_copy(deep=True)
                            
                            # 아이템에 설정된 필드만 오버라이드
                            item_font_dict = item.font.model_dump(exclude_unset=True)
                            for key, value in item_font_dict.items():
                                setattr(merged_font, key, value)
                            
                            item.font = merged_font
                    
                    # 2. 전역 mask_opacity 적용 (개별 설정이 기본값 1.0이면)
                    if working_policy.mask_opacity is not None and item.mask_opacity == 1.0:
                        item.mask_opacity = working_policy.mask_opacity
                    
                    renderer.render_text(item)
                    result["overlaid_items"] += 1
                except Exception as e:
                    self.log.warning(f"Failed to render item {idx+1}: {e}")
                    continue
            
            # 레이어 합성
            self.log.debug("Compositing layers...")
            
            # 배경 투명도 적용 (0.0=투명, 1.0=불투명)
            if working_policy.background_opacity < 1.0:
                alpha = overlay_layer.split()[3]
                # background_opacity를 직접 곱함 (0.0 → 완전투명, 1.0 → 원본유지)
                alpha = alpha.point(lambda p: int(p * working_policy.background_opacity))
                overlay_layer.putalpha(alpha)
            
            # 합성
            result_img = Image.alpha_composite(img, overlay_layer)
            
            # RGB 변환 (저장 시 호환성)
            if result_img.mode == "RGBA":
                rgb_img = Image.new("RGB", result_img.size, (255, 255, 255))
                rgb_img.paste(result_img, mask=result_img.split()[3])
                result_img = rgb_img
            
            result["image"] = result_img
            result["success"] = True
            
            self.log.success(f"Overlay completed: {result['overlaid_items']} items rendered")
            
            # ✨ Save image (if enabled and source_path available)
            if working_policy.save.save_copy and source_path:
                actual_source_path = Path(source_path) if isinstance(source_path, str) else source_path
                self._save_image(result_img, actual_source_path, working_policy)
            
            # ✨ Save metadata (if enabled and source_path available)
            if working_policy.meta.save_meta and source_path:
                actual_source_path = Path(source_path) if isinstance(source_path, str) else source_path
                self._save_metadata(result, actual_source_path, working_policy)
            
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            self.log.error(result["error"])
        
        return result
    
    def _save_image(self, image: Image.Image, source_path: Path, policy: ImageOverlayPolicy):
        """Save overlaid image using fso_utils.
        
        Args:
            image: Overlaid PIL Image
            source_path: Original source file path for name generation
            policy: ImageOverlayPolicy (working_policy from run())
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
            
            self._log_both("info", f"Overlaid image saved: {output_path}")
            
        except Exception as e:
            self._log_both("error", f"Failed to save overlaid image: {e}", exc_info=True)
    
    def _save_metadata(self, result: Dict[str, Any], source_path: Path, policy: ImageOverlayPolicy):
        """Save overlay metadata using fso_utils.
        
        Args:
            result: Overlay result dict
            source_path: Original source file path for name generation
            policy: ImageOverlayPolicy (working_policy from run())
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
            meta_path = builder.build(name=source_stem)
            
            # Extract metadata
            metadata = {
                "overlaid_items": result["overlaid_items"],
                "image_size": result["image_size"],
                "success": result["success"]
            }
            
            meta_path.parent.mkdir(parents=True, exist_ok=True)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            self._log_both("info", f"Overlay metadata saved: {meta_path}")
            
        except Exception as e:
            self._log_both("error", f"Failed to save overlay metadata: {e}", exc_info=True)
