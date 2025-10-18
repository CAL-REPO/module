# -*- coding: utf-8 -*-
"""ImageOverlayer - Text and graphics overlay entry point.

책임:
1. 이미지에 텍스트 오버레이
2. OCR 결과 기반 자동 오버레이
3. 배경, 폰트, 색상 처리
4. BaseServiceLoader 통합 (ImageLoader/OCR과 완전 대칭)
"""

import copy
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image
from pydantic import BaseModel, ValidationError

from cfg_utils import ConfigLoader, ConfigPolicy, BaseServiceLoader
from logs_utils import LogManager
from data_utils import GeometryOps
from path_utils import resolve

from ..core.policy import ImageOverlayPolicy, OverlayItemPolicy
from ..services.io import ImageWriter
from ..services.renderer import OverlayTextRenderer


class ImageOverlayer(BaseServiceLoader[ImageOverlayPolicy]):
    """텍스트 오버레이 EntryPoint (ImageLoader/OCR와 완전 대칭).
    
    BaseServiceLoader를 상속하여 ConfigLoader 통합 및 일관된 설정 로딩을 제공합니다.
    
    Attributes:
        policy: ImageOverlayPolicy 설정
        log: loguru logger 인스턴스
        writer: ImageWriter 인스턴스
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        *,
        policy: Optional[ConfigPolicy] = None,
        config_loader_path: Optional[Union[str, Path]] = None,
        log: Optional[LogManager] = None,
        **overrides: Any
    ):
        """ConfigLoader와 동일한 인자 패턴으로 초기화 (ImageLoader/OCR와 완전 대칭).
        
        Args:
            cfg_like: BaseModel, YAML 경로, dict, 또는 None
                - BaseModel: ImageOverlayPolicy 인스턴스 직접 전달
                - str/Path: YAML 파일 경로
                - dict: 설정 딕셔너리
                - None: 기본 설정 파일 사용
            policy: ConfigPolicy 인스턴스
            config_loader_path: config_loader_overlay.yaml 경로 override (선택)
            log: 외부 LogManager (없으면 policy.log로 생성)
            **overrides: 런타임 오버라이드 값 (source__path, save__directory 등)
        
        Example:
            >>> # YAML 파일에서 로드
            >>> overlay = ImageOverlayer("configs/overlay.yaml")
            
            >>> # dict로 직접 설정
            >>> overlay = ImageOverlayer({"source": {"path": "test.jpg"}})
            
            >>> # config_loader_path override
            >>> overlay = ImageOverlayer(config_loader_path="./custom_config_loader.yaml")
            
            >>> # 런타임 오버라이드 (KeyPath 형식)
            >>> overlay = ImageOverlayer("config.yaml", source__path="image.jpg", save__directory="output")
        """
        # BaseServiceLoader 초기화 (self.policy 설정)
        super().__init__(cfg_like, policy=policy, config_loader_path=config_loader_path, **overrides)
        
        # LogManager 초기화
        if log is None:
            log_manager = LogManager(self.policy.log)
            self.log = log_manager.logger
        else:
            self.log = log.logger if isinstance(log, LogManager) else log
        
        # ImageWriter 초기화 (FSO 기반)
        self.writer = ImageWriter(self.policy.save, self.policy.meta)
        
        self.log.info(f"ImageOverlayer initialized: source={self.policy.source.path}, items={len(self.policy.items)}")
    
    # ==========================================================================
    # BaseServiceLoader Abstract Methods Implementation
    # ==========================================================================
    
    def _get_policy_model(self) -> type[ImageOverlayPolicy]:
        """Policy 모델 클래스 반환."""
        return ImageOverlayPolicy
    
    def _get_config_loader_path(self) -> Path:
        """config_loader_overlay.yaml 경로 반환."""
        return Path(__file__).parent.parent / "configs" / "config_loader_overlay.yaml"
    
    def _get_default_section(self) -> str:
        """기본 section 이름: 'overlay'."""
        return "overlay"
    
    def _get_config_path(self) -> Path:
        """마지막 안전 장치용 기본 설정 파일: overlay.yaml."""
        return Path(__file__).parent.parent / "configs" / "overlay.yaml"
    
    def _get_reference_context(self) -> dict[str, Any]:
        """paths.local.yaml을 reference_context로 제공."""
        from modules.cfg_utils.services.paths_loader import PathsLoader
        try:
            return PathsLoader.load()
        except FileNotFoundError:
            # paths.local.yaml이 없어도 동작 계속 (선택 사항)
            self.log.warning("paths.local.yaml not found (CASHOP_PATHS not set)")
            return {}
    
    # ==========================================================================
    # Core Methods
    # ==========================================================================
    
    def run(
        self,
        source_override: Optional[Union[str, Path]] = None,
        image: Optional[Union[Image.Image, List[Image.Image]]] = None,
        overlay_items: Optional[List[OverlayItemPolicy]] = None,
    ) -> Dict[str, Any]:
        """텍스트 오버레이 실행 (ImageLoader와 완전 대칭).
        
        SRP: ImageOverlayer는 주어진 overlay_items를 이미지에 렌더링하는 것만 담당.
        OCR → Translation → OverlayItem 변환은 pipeline scripts에서 처리.
        
        Args:
            source_override: 소스 경로 오버라이드 (policy.source.path 대신 사용)
            image: PIL Image 객체 또는 리스트 (None이면 source_path에서 로드)
                - None: policy.source.path에서 로드
                - Image.Image: 단일 이미지 사용
                - List[Image.Image]: 첫 번째 이미지만 사용 (ImageTextRecognizer과 동일)
            overlay_items: OverlayItemPolicy 리스트 (None이면 policy.items 사용)
        
        Returns:
            결과 딕셔너리 (ImageLoader와 일관성 유지):
            {
                "success": bool,
                "image": PIL.Image.Image,  # 오버레이된 단일 이미지
                "metadata": Dict[str, Any],  # 단일 메타데이터
                "original_path": Path,
                "saved_path": Optional[Path],
                "meta_path": Optional[Path],
                "overlaid_items": int,
                "image_size": Tuple[int, int],
                "error": Optional[str]
            }
        """
        result = {
            "success": False,
            "image": None,  # 단일 이미지 객체 (ImageLoader/OCR과 일관성)
            "metadata": None,  # 단일 메타데이터
            "original_path": None,
            "saved_path": None,
            "meta_path": None,
            "overlaid_items": 0,
            "image_size": None,
            "error": None,
        }
        
        try:
            # 1. 소스 경로 결정
            source_path = source_override or self.policy.source.path
            source_path = resolve(source_path)
            result["original_path"] = source_path
            
            # 2. 이미지 로드 (제공되지 않은 경우)
            if image is None:
                self.log.info(f"Loading image from: {source_path}")
                
                if not source_path.exists() and self.policy.source.must_exist:
                    raise FileNotFoundError(f"Image not found: {source_path}")
                
                # PIL Image로 직접 로드
                img = Image.open(source_path)
                
                # EXIF orientation 처리
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
                
                # convert_mode 처리
                if self.policy.source.convert_mode:
                    img = img.convert(self.policy.source.convert_mode)
            else:
                # Pillow 리스트 입력 처리 (ImageTextRecognizer과 동일한 패턴)
                if isinstance(image, list):
                    if not image:
                        raise ValueError("Empty image list provided")
                    img = image[0]  # 첫 번째 이미지만 사용
                    self.log.info(f"Using first image from list ({len(image)} total)")
                else:
                    self.log.info(f"Using provided image object")
                    img = image
            
            result["image_size"] = img.size
            self.log.info(f"Image size: {img.size} {img.mode}")
            
            # 3. overlay_items 결정
            items = overlay_items or self.policy.items
            
            if not items:
                self.log.warning("No overlay items to render")
                result["success"] = True
                result["image"] = img
                result["metadata"] = {
                    "original_path": str(source_path),
                    "image_size": result["image_size"],
                    "overlaid_items": 0,
                }
                return result
            
            self.log.info(f"Overlaying {len(items)} items...")
            
            # 4. RGBA 변환 (투명도 처리를 위해)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            
            # 5. 오버레이 레이어 생성
            overlay_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            
            # 6. 각 아이템 렌더링
            from PIL import ImageDraw
            from ..services.renderer import OverlayTextRenderer
            
            draw = ImageDraw.Draw(overlay_layer)
            renderer = OverlayTextRenderer(draw)  # draw 객체와 함께 초기화
            
            for idx, item in enumerate(items):
                try:
                    # OverlayItemPolicy를 OverlayTextRenderer에 전달
                    renderer.render_text(item)
                    
                    result["overlaid_items"] += 1
                    
                except Exception as e:
                    self.log.warning(f"Failed to render item {idx+1}: {e}")
                    import traceback
                    self.log.debug(traceback.format_exc())
                    continue
            
            # 7. 레이어 합성
            self.log.info("Compositing layers...")
            
            # 배경 투명도 적용 (background_opacity는 배경의 투명도, 0.0=불투명, 1.0=투명)
            # 0.0 = 오버레이 완전 불투명 (기본값, 정상)
            # 1.0 = 오버레이 완전 투명 (안 보임)
            if self.policy.background_opacity > 0.0:
                alpha = overlay_layer.split()[3]
                # 1.0 - opacity로 변환 (0.0 → 1.0 불투명, 1.0 → 0.0 투명)
                opacity_multiplier = 1.0 - self.policy.background_opacity
                alpha = alpha.point(lambda p: int(p * opacity_multiplier))
                overlay_layer.putalpha(alpha)
            
            # 합성
            result_img = Image.alpha_composite(img, overlay_layer)
            
            # RGB 변환 (저장 시 호환성을 위해)
            if result_img.mode == "RGBA":
                rgb_img = Image.new("RGB", result_img.size, (255, 255, 255))
                rgb_img.paste(result_img, mask=result_img.split()[3])
                result_img = rgb_img
            
            self.log.success(f"Overlay completed: {result['overlaid_items']} items rendered")
            
            # 8. 메타데이터 준비
            meta_data = {
                "original_path": str(source_path),
                "image_size": result["image_size"],
                "saved_path": None,  # 저장 후 업데이트
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
            
            # 9. 정책에 따라 이미지 저장 (save_copy=True일 때만)
            if self.policy.save.save_copy:
                self.log.info("Saving overlaid image...")
                saved_path = self.writer.save_image(result_img, source_path)
                result["saved_path"] = saved_path
                meta_data["saved_path"] = str(saved_path)
                self.log.success(f"Saved to: {saved_path}")
            else:
                self.log.info("Image save skipped (save_copy=False)")
            
            # 10. 정책에 따라 메타데이터 저장 (save_meta=True일 때만)
            if self.policy.meta.save_meta:
                # 메타 파일명: 원본 이미지 기준 (ImageTextRecognizer과 동일)
                # ImageTextRecognizer: source_path 사용 → 01_ocr_meta_001.json
                # ImageOverlayer: source_path 사용 → 01_overlay_meta_001.json (중복 방지)
                meta_path = self.writer.save_meta(meta_data, source_path)
                if meta_path:
                    result["meta_path"] = meta_path
                    self.log.success(f"Metadata saved to: {meta_path}")
            else:
                self.log.info("Metadata save skipped (save_meta=False)")
            
            # 11. 결과 저장 (단일 값, ImageLoader/OCR과 일관성)
            result["image"] = result_img
            result["metadata"] = meta_data
            
            result["success"] = True
            self.log.success("ImageOverlayer completed successfully")
            
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
        return f"ImageOverlayer(source={self.policy.source.path}, items={len(self.policy.items)})"


