# -*- coding: utf-8 -*-
"""
Oto Adapter - 순수 OTO 파이프라인 로직.

책임:
1. OCR → Translate → Overlay 파이프라인 실행 (Image → Image)
2. OCRItem → OverlayItem 변환 로직
3. 4개 서비스 통합 (ImageLoad, ImageTextRecognize, Translate, ImageOverlay)
4. Standalone 사용 가능 (YAML 로딩 없음)

EntryPoint와의 역할 분담:
- Adapter (이 파일): 순수 파이프라인 로직, Image 객체 처리
- EntryPoint: YAML 로딩, 파일 I/O, 메타데이터 저장
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image
from pydantic import BaseModel

from cfg_utils.services.config_like_loader import ConfigLikeLoader
from logs_utils import LogManager

from oto.policy.oto_policy import OTOPolicy

from image_utils.adapter.load import ImageLoad
from image_utils.adapter.text_recognize import ImageTextRecognize
from image_utils.adapter.overlay import ImageOverlay
from image_utils.core.models import OCRItem
from image_utils.core.policy import OverlayItemPolicy

from translate_utils.adapter.translate import Translate


class Oto:
    """OCR → Translate → Overlay 순수 파이프라인 로직 (Standalone Adapter).
    
    Image 객체를 받아서 OCR → 번역 → 오버레이를 수행하고 최종 Image를 반환합니다.
    Adapter Pattern: Policy에 source 없음, run()에서 image 받음
    
    Attributes:
        policy: OTOPolicy 설정 (4개 Adapter 정책 통합)
        log: loguru logger 인스턴스
        image_load: ImageLoad adapter (lazy-loaded)
        image_text_recognize: ImageTextRecognize adapter (lazy-loaded)
        translate: Translate adapter (lazy-loaded)
        image_overlay: ImageOverlay adapter (lazy-loaded)
    
    Example:
        >>> # Standalone 사용
        >>> from PIL import Image
        >>> policy = OTOPolicy(...)
        >>> oto = Oto(cfg_like=policy, log_manager=log_manager)
        >>> image = Image.open("test.jpg")
        >>> result = oto.run(image=image)
        >>> result['image'].show()
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """OTOPolicy 기반 초기화 (ConfigLikeLoader 패턴).
        
        Args:
            cfg_like: BaseModel, YAML 경로, dict, 또는 None
                - BaseModel: OTOPolicy 인스턴스 직접 전달
                - str/Path: YAML 파일 경로 (PolicyLoader로 로드)
                - dict: 설정 딕셔너리
                - None: 기본 설정 파일 사용 (configs/oto/image.yaml)
            log_manager: LogManager 인스턴스 (없으면 policy.log로 생성)
            **overrides: 런타임 오버라이드 (image__source__path 등)
        
        Example:
            >>> # Policy 인스턴스 직접 전달
            >>> oto = Oto(OTOPolicy(...), log_manager=log_manager)
            
            >>> # YAML 파일에서 로드
            >>> oto = Oto("configs/oto/image.yaml", log_manager=log_manager)
            
            >>> # dict로 직접 설정
            >>> oto = Oto({"image": {...}, "ocr": {...}}, log_manager=log_manager)
            
            >>> # 런타임 오버라이드
            >>> oto = Oto("config.yaml", ocr__provider__langs=["ch", "en"])
        """
        # ConfigLikeLoader로 정책 로드
        self.policy = self._load_config(cfg_like, **overrides)
        
        # LogManager 초기화
        if log_manager:
            self.log = log_manager.logger
        elif self.policy.log:
            self.log = LogManager(self.policy.log).logger
        else:
            self.log = LogManager({"enabled": False}).logger
        
        # 각 adapter는 lazy-load (첫 process() 호출 시 초기화)
        self._image_load: Optional[ImageLoad] = None
        self._image_text_recognize: Optional[ImageTextRecognize] = None
        self._translate: Optional[Translate] = None
        self._image_overlay: Optional[ImageOverlay] = None
        
        self.log.debug("Oto adapter initialized")
    
    # ==========================================================================
    # ConfigLikeLoader Integration
    # ==========================================================================
    
    @staticmethod
    def _load_config(
        cfg_like: Union[BaseModel, Path, str, dict, None],
        **overrides: Any
    ) -> OTOPolicy:
        """ConfigLikeLoader로 정책 로드 (ImageLoad, ImageTextRecognize, ImageOverlay와 동일 패턴).
        
        Args:
            cfg_like: BaseModel, YAML 경로, dict, 또는 None
            **overrides: 런타임 오버라이드
        
        Returns:
            OTOPolicy 인스턴스
        """
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=OTOPolicy,
            caller_file=__file__,
            default_config_filename="image.yaml",  # configs/oto/image.yaml
            **overrides
        )
    
    # ==========================================================================
    # Adapter Lazy Loading
    # ==========================================================================
    
    @property
    def image_load(self) -> ImageLoad:
        """ImageLoad adapter lazy-loading."""
        if self._image_load is None:
            self._image_load = ImageLoad(
                cfg_like=self.policy.image_load,
                log_manager=None,  # 각 adapter가 자체 LogManager 생성
            )
        return self._image_load
    
    @property
    def image_text_recognize(self) -> ImageTextRecognize:
        """ImageTextRecognize adapter lazy-loading."""
        if self._image_text_recognize is None:
            self._image_text_recognize = ImageTextRecognize(
                cfg_like=self.policy.text_recognize,
                log_manager=None,  # 각 adapter가 자체 LogManager 생성
            )
        return self._image_text_recognize
    
    @property
    def translate(self) -> Translate:
        """Translate adapter lazy-loading (인스턴스 재사용).
        
        run() 메서드를 사용하므로 매번 새 인스턴스를 생성할 필요 없음.
        이미지 여러 개 처리 시 동일 인스턴스를 재사용하여 Provider 연결 유지.
        """
        if self._translate is None:
            self._translate = Translate(
                cfg_like=self.policy.translate,
                log_manager=None,  # Translate가 자체 LogManager 생성
            )
        return self._translate
    
    @property
    def image_overlay(self) -> ImageOverlay:
        """ImageOverlay adapter lazy-loading."""
        if self._image_overlay is None:
            self._image_overlay = ImageOverlay(
                cfg_like=self.policy.overlay,
                log_manager=None,  # 각 adapter가 자체 LogManager 생성
            )
        return self._image_overlay
    
    # ==========================================================================
    # Core Pipeline Methods
    # ==========================================================================
    
    def run(
        self,
        image: Image.Image,
        source_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """OCR → Translate → Overlay 파이프라인 실행 (Adapter Pattern).
        
        Adapter Pattern: run()에서 Image 객체를 받아서 처리합니다.
        
        Pipeline Flow:
            1. ImageTextRecognize.run(image) → List[OCRItem]
            2. Translate.run(texts) → Dict[str, str]
            3. OCRItem + translated_text → OverlayItemPolicy
            4. ImageOverlay.run(image, overlay_items) → Final Image
        
        Args:
            image: 입력 PIL Image 객체
            source_path: 소스 경로 (로깅용, 선택)
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "image": PIL.Image.Image,  # 최종 오버레이된 이미지
                "ocr_items": List[OCRItem],  # OCR 결과
                "translated_dict": Dict[str, str],  # 번역 결과
                "overlay_items": List[OverlayItemPolicy],  # 오버레이 아이템
                "error": Optional[str]
            }
        
        Example:
            >>> from PIL import Image
            >>> oto = Oto(cfg_like=policy, log_manager=log_manager)
            >>> image = Image.open("test.jpg")
            >>> result = oto.run(image=image)
            >>> if result['success']:
            ...     result['image'].show()
        """
        result = {
            "success": False,
            "image": None,
            "ocr_items": [],
            "translated_dict": {},
            "overlay_items": [],
            "error": None,
        }
        
        try:
            source_name = source_path.name if source_path else "Image"
            
            self.log.info(f"{'='*80}")
            self.log.info(f"🖼️  Oto Pipeline: {source_name}")
            self.log.info(f"{'='*80}\n")
            
            # ====================================================================
            # Step 1: ImageTextRecognize - OCR 실행
            # ====================================================================
            self.log.info("[1/4] ImageTextRecognize: Running OCR...")
            
            # ImageTextRecognize.run(image) → Dict {"ocr_items", "image", ...}
            ocr_result = self.image_text_recognize.run(image=image)
            ocr_items: List[OCRItem] = ocr_result.get("ocr_items", [])
            image = ocr_result.get("image", image)  # ⚠️ OCR 처리된 이미지로 업데이트 (resize된 경우 포함)
            
            result['ocr_items'] = ocr_items
            
            if ocr_result.get("resized"):
                self.log.info(f"   → Image resized for OCR (scale={ocr_result.get('scale_factor', 1.0):.3f})")
            
            self.log.success(f"✅ OCR completed: {len(ocr_items)} items")
            
            if not ocr_items:
                self.log.warning("No OCR items found - skipping translation/overlay")
                result['success'] = True
                result['image'] = image
                return result
            
            # ====================================================================
            # Step 2: Translate - 번역 실행
            # ====================================================================
            self.log.info("\n[2/4] Translate: Translating texts...")
            
            # OCRItem에서 텍스트 추출
            original_texts = [item.text for item in ocr_items if item.text]
            
            if not original_texts:
                self.log.warning("No texts to translate")
                result['success'] = True
                result['image'] = image
                return result
            
            self.log.info(f"  Original texts: {len(original_texts)}")
            
            # Translate.run() 실행 (배치 번역 + 세그먼트 단위 캐싱)
            try:
                translated_dict = self.translate.run(original_texts)
                
                # 결과 검증
                if not isinstance(translated_dict, dict):
                    self.log.warning(f"Translation returned non-dict: {type(translated_dict)} - using original texts")
                    translated_dict = {text: text for text in original_texts}
                elif not translated_dict:
                    self.log.warning("Translation returned empty dict - using original texts")
                    translated_dict = {text: text for text in original_texts}
                
                # 누락된 텍스트는 원본 사용
                for text in original_texts:
                    if text not in translated_dict:
                        translated_dict[text] = text
                    
            except Exception as e:
                self.log.error(f"Translation error: {e} - using original texts")
                import traceback
                self.log.debug(traceback.format_exc())
                translated_dict = {text: text for text in original_texts}
            
            result['translated_dict'] = translated_dict
            self.log.success(f"✅ Translation completed: {len(translated_dict)} texts")
            
            # ====================================================================
            # Step 3: Conversion - OCRItem → OverlayItemPolicy
            # ====================================================================
            self.log.info("\n[3/4] Conversion: OCRItem → OverlayItem...")
            
            overlay_items: List[OverlayItemPolicy] = []
            
            for item in ocr_items:
                if not item.text:
                    continue
                
                # 번역된 텍스트 가져오기
                translated_text = translated_dict.get(item.text, item.text)
                
                # OCRItem.to_overlay_item() 사용
                overlay_item = item.to_overlay_item(text_override=translated_text)
                overlay_items.append(overlay_item)
            
            result['overlay_items'] = overlay_items
            self.log.success(f"✅ Converted: {len(overlay_items)} overlay items")
            
            # ====================================================================
            # Step 4: ImageOverlay - 오버레이 렌더링
            # ====================================================================
            self.log.info("\n[4/4] ImageOverlay: Rendering overlay...")
            
            # ImageOverlay.run(image, items) → Dict with "image"
            overlay_result = self.image_overlay.run(image=image, items=overlay_items)
            
            if not overlay_result.get("success"):
                error_msg = overlay_result.get("error", "Unknown overlay error")
                self.log.error(f"Overlay failed: {error_msg}")
                result['error'] = error_msg
                result['image'] = image  # 원본 반환
                return result
            
            final_image = overlay_result.get("image")
            result['image'] = final_image
            
            self.log.success(f"✅ Overlay completed")
            
            result['success'] = True
            
            self.log.info(f"\n{'='*80}")
            self.log.success(f"✅ Oto Pipeline Completed: {source_name}")
            self.log.info(f"{'='*80}\n")
            
        except Exception as e:
            result['error'] = f"Unexpected error: {type(e).__name__}: {e}"
            self.log.error(result['error'])
            
            import traceback
            self.log.error(traceback.format_exc())
        
        return result
    
    def __repr__(self) -> str:
        return f"Oto(policy={self.policy.__class__.__name__})"
