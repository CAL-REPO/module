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
        """Initialize ImageOverlay adapter.
        
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
        
        # LogManager 생성
        if log_manager:
            self.log = log_manager.logger
        elif self.policy.log:
            self.log = LogManager(self.policy.log).logger
        else:
            self.log = LogManager({"enabled": False}).logger
        
        self.log.debug("ImageOverlay initialized")
    
    # ==========================================================================
    # Config Loading
    # ==========================================================================
    
    def _load_config(self, cfg_like, **overrides) -> ImageOverlayPolicy:
        """Load ImageOverlayPolicy."""
        from cfg_utils.services.config_like_loader import ConfigLikeLoader
        
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=ImageOverlayPolicy,
            caller_file=__file__,
            default_config_filename="overlay.yaml",
            **overrides
        )
    
    # ==========================================================================
    # Main API (Translate pattern)
    # ==========================================================================
    
    def run(
        self,
        image: Image.Image,
        items: Optional[List[OverlayItemPolicy]] = None,
    ) -> Dict[str, Any]:
        """이미지에 텍스트/도형 오버레이 (Translate.run() pattern).
        
        Args:
            image: PIL Image 객체
            items: OverlayItemPolicy 리스트 (None이면 policy.items 사용)
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "image": PIL.Image.Image,
                "overlaid_items": int,
                "image_size": Tuple[int, int],
                "error": Optional[str]
            }
        
        Example:
            >>> overlay = ImageOverlay("config.yaml")
            >>> img = Image.open("test.jpg")
            >>> result = overlay.run(img)
            >>> overlaid_img = result["image"]
        """
        result = {
            "success": False,
            "image": None,
            "overlaid_items": 0,
            "image_size": image.size,
            "error": None,
        }
        
        try:
            # items 결정 (인자 우선, 없으면 policy.items 사용)
            overlay_items = items or self.policy.items
            
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
            
            # 🔍 디버깅: Overlay 렌더링 정보 (전역 설정 주입 전 - 원본 상태)
            self.log.info(f"\n{'='*80}")
            self.log.info(f"[OVERLAY DEBUG] Image size: {img.size}")
            self.log.info(f"[OVERLAY DEBUG] Total items to render: {len(overlay_items)}")
            self.log.info(f"{'='*80}\n")
            
            # 각 아이템 렌더링 (전역 설정 주입)
            debug_count = 0  # 디버깅용 카운터 (첫 3개만 출력)
            for idx, item in enumerate(overlay_items):
                try:
                    # 1. 전역 font와 개별 font 병합
                    if self.policy.font is not None:
                        if item.font is None:
                            # 아이템 font 없음 → 전역 font 사용
                            item.font = self.policy.font
                        else:
                            # 아이템 font 있음 → 전역 font와 병합 (아이템 우선)
                            from font_utils import FontPolicy
                            merged_font = self.policy.font.model_copy(deep=True)
                            
                            # 아이템에 설정된 필드만 오버라이드
                            item_font_dict = item.font.model_dump(exclude_unset=True)
                            for key, value in item_font_dict.items():
                                setattr(merged_font, key, value)
                            
                            item.font = merged_font
                    
                    # 2. 전역 mask_opacity 적용 (개별 설정이 기본값 1.0이면)
                    if self.policy.mask_opacity is not None and item.mask_opacity == 1.0:
                        item.mask_opacity = self.policy.mask_opacity
                    
                    # 🔍 디버깅: 전역 설정 주입 후 상태 (첫 3개만)
                    if debug_count < 3:
                        self.log.info(f"[OVERLAY RENDER] [{idx+1}] text='{item.text}'")
                        self.log.info(f"                 polygon={item.polygon}")
                        if item.font:
                            self.log.info(f"                 font: size={item.font.size}, family={item.font.family}")
                        else:
                            self.log.info(f"                 font: None")
                        self.log.info(f"                 mask_opacity={item.mask_opacity:.2f}")
                        debug_count += 1
                    
                    renderer.render_text(item)
                    result["overlaid_items"] += 1
                except Exception as e:
                    self.log.warning(f"Failed to render item {idx+1}: {e}")
                    continue
            
            # 레이어 합성
            self.log.debug("Compositing layers...")
            
            # 배경 투명도 적용 (0.0=투명, 1.0=불투명)
            if self.policy.background_opacity < 1.0:
                alpha = overlay_layer.split()[3]
                # background_opacity를 직접 곱함 (0.0 → 완전투명, 1.0 → 원본유지)
                alpha = alpha.point(lambda p: int(p * self.policy.background_opacity))
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
            
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            self.log.error(result["error"])
        
        return result
