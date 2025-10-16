# -*- coding: utf-8 -*-
"""ImageOverlay - Text and graphics overlay entry point.

책임:
1. 이미지에 텍스트 오버레이
2. OCR 결과 기반 자동 오버레이
3. 배경, 폰트, 색상 처리
4. cfg_loader/logs_utils 통합
"""

import copy
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image
from pydantic import BaseModel, ValidationError

from cfg_utils import ConfigLoader
from logs_utils import LogManager
from data_utils import GeometryOps
from path_utils import resolve

from ..core.policy import ImageOverlayPolicy, OverlayItemPolicy
from ..services.io import ImageWriter
from ..services.renderer import OverlayTextRenderer


class ImageOverlay:
    """텍스트 오버레이 EntryPoint.
    
    ConfigLoader와 동일한 패턴으로 다양한 입력 형태를 지원합니다.
    
    Attributes:
        policy: ImageOverlayPolicy 설정
        log: loguru logger 인스턴스
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        *,
        policy_overrides: Optional[Dict[str, Any]] = None,
        log: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize ImageOverlay with flexible config input.
        
        Args:
            cfg_like: Policy 인스턴스, YAML 경로, dict, 또는 None
            policy_overrides: ConfigPolicy 필드 개별 오버라이드
            log: 외부 LogManager (없으면 policy.log로 생성)
            **overrides: 런타임 오버라이드
        """
        self.policy = self._load_config(cfg_like, policy_overrides=policy_overrides, **overrides)
        
        # LogManager 초기화
        if log is None:
            log_manager = LogManager(self.policy.log)
            self.log = log_manager.logger
        else:
            self.log = log.logger if isinstance(log, LogManager) else log
        
        # ImageWriter 초기화 (FSO 기반)
        self.writer = ImageWriter(self.policy.save, self.policy.meta)
        
        # OverlayTextRenderer는 나중에 이미지와 함께 초기화
        self.renderer = None
        
        self.log.info(f"ImageOverlay initialized: source={self.policy.source.path}, items={len(self.policy.items)}")
    
    def _load_config(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None],
        *,
        policy_overrides: Optional[Dict[str, Any]] = None,
        **overrides: Any
    ) -> ImageOverlayPolicy:
        """설정 로드 (간소화 버전)
        
        Args:
            cfg_like: 설정 소스
            policy_overrides: ConfigPolicy 필드 개별 오버라이드
            **overrides: 런타임 오버라이드
        
        Returns:
            ImageOverlayPolicy 인스턴스
        """
        # cfg_like가 None이면 기본 파일 경로 + 섹션을 policy_overrides로 지정
        if cfg_like is None:
            default_path = Path(__file__).parent.parent / "configs" / "overlay.yaml"
            if policy_overrides is None:
                policy_overrides = {}
            
            # ImageOverlay 전용 ConfigLoader 정책 파일 지정
            policy_overrides.setdefault("config_loader_path", 
                str(Path(__file__).parent.parent / "configs" / "config_loader_overlay.yaml")
            )
            
            # yaml.source_paths에 dict 형태로 전달
            policy_overrides.setdefault("yaml.source_paths", {
                "path": str(default_path),
                "section": "overlay"
            })
        
        return ConfigLoader.load(
            cfg_like,
            model=ImageOverlayPolicy,
            policy_overrides=policy_overrides,
            **overrides
        )
    
    # ==========================================================================
    # Pipeline Integration
    # ==========================================================================
    # Note: OCR → OverlayItem 변환은 pipeline scripts에서 수행
    # OCRItem.to_overlay_item()을 사용하여 변환
    
    def run(
        self,
        source_path: Union[str, Path],
        image: Optional[Image.Image] = None,
        overlay_items: Optional[List[OverlayItemPolicy]] = None,
    ) -> Dict[str, Any]:
        """텍스트 오버레이 실행.
        
        SRP: ImageOverlay는 주어진 overlay_items를 이미지에 렌더링하는 것만 담당.
        OCR → Translation → OverlayItem 변환은 pipeline scripts에서 처리.
        
        Args:
            source_path: 소스 경로 (메타데이터 저장용)
            image: PIL Image 객체 (None이면 source_path에서 로드)
            overlay_items: OverlayItemPolicy 리스트 (None이면 policy.items 사용)
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "source_path": Path,
                "saved_path": Optional[Path],
                "meta_path": Optional[Path],
                "overlaid_items": int,
                "image_size": Tuple[int, int],
                "image": Optional[Image.Image],  # 오버레이된 이미지
                "error": Optional[str]
            }
        """
        result = {
            "success": False,
            "source_path": resolve(source_path),
            "saved_path": None,
            "meta_path": None,
            "overlaid_items": 0,
            "image_size": None,
            "image": None,
            "error": None,
        }
        
        try:
            # 1. 이미지 로드 (제공되지 않은 경우)
            if image is None:
                self.log.info(f"Loading image from: {result['source_path']}")
                from ..services.io import ImageReader
                reader = ImageReader()
                img = reader.read(
                    path=result['source_path'],
                    must_exist=self.policy.source.must_exist,
                    convert_mode=self.policy.source.convert_mode,
                )
            else:
                self.log.info(f"Using provided image object")
                img = image
            
            result["image_size"] = img.size
            self.log.info(f"Image size: {img.size} {img.mode}")
            
            # 2. overlay_items 결정
            items = overlay_items or self.policy.items
            
            if not items:
                self.log.warning("No overlay items to render")
                result["success"] = True
                result["image"] = img
                return result
            
            self.log.info(f"Overlaying {len(items)} items...")
            
            # 3. RGBA 변환 (투명도 처리를 위해)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            
            # 4. 오버레이 레이어 생성
            overlay_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            
            # 5. 각 아이템 렌더링
            from PIL import ImageDraw
            from ..services.renderer import OverlayTextRenderer
            
            draw = ImageDraw.Draw(overlay_layer)
            renderer = OverlayTextRenderer(draw)  # draw 객체와 함께 초기화
            
            for idx, item in enumerate(items):
                try:
                    self.log.debug(f"Rendering item {idx+1}/{len(items)}: '{item.text}'")
                    
                    # OverlayItemPolicy를 OverlayTextRenderer에 전달
                    renderer.render_text(item)
                    
                    result["overlaid_items"] += 1
                    
                except Exception as e:
                    self.log.warning(f"Failed to render item {idx+1}: {e}")
                    continue
            
            # 6. 레이어 합성
            self.log.info("Compositing layers...")
            
            # 배경 투명도 적용
            if self.policy.background_opacity < 1.0:
                alpha = overlay_layer.split()[3]
                alpha = alpha.point(lambda p: int(p * self.policy.background_opacity))
                overlay_layer.putalpha(alpha)
            
            # 합성
            result_img = Image.alpha_composite(img, overlay_layer)
            
            # RGB 변환 (저장 시 호환성을 위해)
            if result_img.mode == "RGBA":
                rgb_img = Image.new("RGB", result_img.size, (255, 255, 255))
                rgb_img.paste(result_img, mask=result_img.split()[3])
                result_img = rgb_img
            
            result["image"] = result_img
            self.log.success(f"Overlay completed: {result['overlaid_items']} items rendered")
            
            # 7. 이미지 저장
            if self.policy.save.save_copy:
                self.log.info("Saving overlaid image...")
                
                base_path = Path(result['source_path'])
                saved_path = self.writer.save_image(
                    image=result_img,
                    base_path=base_path,
                )
                result["saved_path"] = saved_path
                self.log.success(f"Saved to: {saved_path}")
            
            # 8. 메타데이터 저장
            if self.policy.meta.save_meta:
                self.log.info("Saving overlay metadata...")
                
                meta_data = {
                    "source_path": str(result['source_path']),
                    "image_size": result["image_size"],
                    "saved_path": str(result["saved_path"]) if result["saved_path"] else None,
                    "overlaid_items": result["overlaid_items"],
                    "background_opacity": self.policy.background_opacity,
                    "items": [
                        {
                            "text": item.text,
                            "polygon": item.polygon,
                            "font": item.font.model_dump() if item.font else None,
                            "conf": item.conf,
                            "lang": item.lang,
                        }
                        for item in items
                    ]
                }
                
                # Use ImageWriter for metadata with FSO
                base_path = Path(result['source_path'])
                meta_path = self.writer.save_meta(meta_data, base_path)
                if meta_path:
                    result["meta_path"] = meta_path
                    self.log.success(f"Metadata saved to: {meta_path}")
            
            result["success"] = True
            self.log.success("ImageOverlay completed successfully")
            
        except FileNotFoundError as e:
            result["error"] = f"File not found: {e}"
            self.log.error(result["error"])
        except ValidationError as e:
            result["error"] = f"Validation error: {e}"
            self.log.error(result["error"])
        except Exception as e:
            result["error"] = f"Unexpected error: {type(e).__name__}: {e}"
            self.log.error(result["error"])
        
        return result
    
    def __repr__(self) -> str:
        return f"ImageOverlay(source={self.policy.source.path}, items={len(self.policy.items)})"
