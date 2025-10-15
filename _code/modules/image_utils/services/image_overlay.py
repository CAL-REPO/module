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

from ..core.policy import ImageOverlayPolicy, OverlayTextPolicy
from ..core.models import OCRItem
from ..services.io import ImageWriter


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
        
        self.log.info(f"ImageOverlay initialized: source={self.policy.source.path}, texts={len(self.policy.texts)}")
    
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
    # Factory Methods
    # ==========================================================================
    
    @classmethod
    def from_ocr_items(
        cls,
        source_path: Union[str, Path],
        ocr_items: List[OCRItem],
        background_opacity: float = 0.7,
        save_policy: Optional[Dict[str, Any]] = None,
        log: Optional[LogManager] = None,
    ) -> "ImageOverlay":
        """OCR 결과에서 ImageOverlay 생성.
        
        Args:
            source_path: 소스 이미지 경로
            ocr_items: OCRItem 리스트
            background_opacity: 배경 투명도 (0.0-1.0)
            save_policy: 저장 정책 딕셔너리
            log: 외부 LogManager
        
        Returns:
            ImageOverlay 인스턴스
        """
        # OCRItem → OverlayTextPolicy 변환
        texts = []
        for item in ocr_items:
            text_policy = OverlayTextPolicy(
                text=item.text,
                polygon=item.quad,
            )
            texts.append(text_policy)
        
        # ImageOverlayPolicy 생성
        config_dict = {
            "source": {"path": str(source_path)},
            "texts": [t.model_dump() for t in texts],
            "background_opacity": background_opacity,
        }
        
        if save_policy:
            config_dict["save"] = save_policy
        
        policy = ImageOverlayPolicy(**config_dict)
        return cls(policy=policy, log=log)
    
    def run(
        self,
        source_override: Optional[Union[str, Path]] = None,
        texts_override: Optional[List[OverlayTextPolicy]] = None,
    ) -> Dict[str, Any]:
        """텍스트 오버레이 실행.
        
        Args:
            source_override: 소스 경로 오버라이드 (policy.source.path 대신 사용)
            texts_override: 텍스트 정책 오버라이드 (policy.texts 대신 사용)
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "original_path": Path,
                "saved_path": Optional[Path],
                "meta_path": Optional[Path],
                "overlaid_texts": int,
                "original_size": Tuple[int, int],
                "error": Optional[str]
            }
        """
        result = {
            "success": False,
            "original_path": None,
            "saved_path": None,
            "meta_path": None,
            "overlaid_texts": 0,
            "original_size": None,
            "error": None,
        }
        
        try:
            # 1. 소스 경로 결정
            source_path = source_override or self.policy.source.path
            source_path = resolve(source_path)
            result["original_path"] = source_path
            
            self.log.info(f"Loading image for overlay: {source_path}")
            
            # 2. 이미지 로드
            img = self.reader.read(
                path=source_path,
                must_exist=self.policy.source.must_exist,
                convert_mode=self.policy.source.convert_mode,
            )
            result["original_size"] = img.size
            
            self.log.info(f"Loaded image: {img.size} {img.mode}")
            
            # 3. 텍스트 정책 결정
            texts = texts_override or self.policy.texts
            
            if not texts:
                self.log.warning("No texts to overlay")
                result["success"] = True
                return result
            
            self.log.info(f"Overlaying {len(texts)} text items...")
            
            # 4. RGBA 변환 (투명도 처리를 위해)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            
            # 5. 오버레이 레이어 생성
            overlay_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            
            # 6. 각 텍스트 렌더링
            from PIL import ImageDraw
            draw = ImageDraw.Draw(overlay_layer)
            
            for idx, text_policy in enumerate(texts):
                try:
                    self.log.debug(f"Rendering text {idx+1}/{len(texts)}: '{text_policy.text}'")
                    
                    # OverlayTextRenderer 사용
                    self.renderer.render_text_on_polygon(
                        draw=draw,
                        text=text_policy.text,
                        polygon=text_policy.polygon,
                        font_policy=text_policy.font,
                        anchor=text_policy.anchor,
                        offset=text_policy.offset,
                        max_width_ratio=text_policy.max_width_ratio,
                        background_opacity=self.policy.background_opacity,
                    )
                    
                    result["overlaid_texts"] += 1
                    
                except Exception as e:
                    self.log.warning(f"Failed to render text {idx+1}: {e}")
                    continue
            
            # 7. 레이어 합성
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
            
            self.log.success(f"Overlay completed: {result['overlaid_texts']} texts rendered")
            
            # 8. 이미지 저장
            if self.policy.save.save_copy:
                self.log.info("Saving overlaid image...")
                
                saved_path = self.writer.write(
                    image=result_img,
                    policy=self.policy.save,
                    source_path=source_path,
                )
                result["saved_path"] = saved_path
                self.log.success(f"Saved to: {saved_path}")
            
            # 9. 메타데이터 저장
            if self.policy.meta.save_meta:
                self.log.info("Saving overlay metadata...")
                
                meta_data = {
                    "original_path": str(source_path),
                    "original_size": result["original_size"],
                    "saved_path": str(result["saved_path"]) if result["saved_path"] else None,
                    "overlaid_texts": result["overlaid_texts"],
                    "background_opacity": self.policy.background_opacity,
                    "texts": [
                        {
                            "text": t.text,
                            "polygon": t.polygon,
                            "font": t.font.model_dump() if t.font else None,
                        }
                        for t in texts
                    ]
                }
                
                # Use ImageWriter for metadata with FSO
                meta_path = self.writer.save_meta(meta_data, source_path)
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
        return f"ImageOverlay(source={self.policy.source.path}, texts={len(self.policy.texts)})"
