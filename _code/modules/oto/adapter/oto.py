# -*- coding: utf-8 -*-
"""
Oto Adapter - 순수 OTO 파이프라인 로직.

책임:
1. OCR → Translate → Overlay 파이프라인 실행 (Image → Image)
2. OCRItem → OverlayItem 변환 로직
3. 3개 서비스 통합 (ImageTextRecognize, Translate, ImageOverlay)
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
from cfg_utils.services.section_extractor import SectionExtractor
from cfg_utils.services import filter_overrides_by_prefix
from logs_utils import LogManager

from oto.core.policy import OTOPolicy

from image_utils.core.policy import ImageLoadPolicy, ImageTextRecognizePolicy, ImageOverlayPolicy
from translate_utils.core.policy import TranslatePolicy

from image_utils.adapter.load import ImageLoad
from image_utils.adapter.text_recognize import ImageTextRecognize
from image_utils.adapter.overlay import ImageOverlay
from translate_utils.adapter.translate import Translate

from image_utils.core.models import OCRItem
from image_utils.core.policy import OverlayItemPolicy


class OTO:
    """OCR → Translate → Overlay 복합 Adapter (Pass-through Pattern).
    
    Architecture:
    1. ConfigLoader가 모든 section 병합 (image_load, image_text_recognize, translate, image_overlay)
    2. SectionExtractor가 Policy.name으로 section 추출 (Cascading Priority 적용)
    3. 각 모듈 Adapter에 추출된 cfg_like 전달
    4. 파이프라인 실행: ImageLoad → OCR → Translate → Overlay
    
    Design Pattern:
    - Pass-through: Oto는 ConfigLoader 병합 dict를 받아서 SectionExtractor로 추출만 수행
    - SRP: 각 모듈이 자신의 cfg_like 처리 담당 (cfg_like=None → Pydantic 기본값)
    - Cascading Priority: 개별 cfg_like > 병합 section > None
    
    Attributes:
        policy: OTOPolicy 설정 (로깅용 - 모든 서브 모듈 정책 통합)
        log: loguru logger 인스턴스
        image_load: ImageLoad Adapter (lazy-loaded)
        image_text_recognize: ImageTextRecognize Adapter (lazy-loaded)
        translate: Translate Adapter (lazy-loaded)
        image_overlay: ImageOverlay Adapter (lazy-loaded)
    
    Example:
        >>> # 기본값 사용 (모든 모듈이 Pydantic 기본값)
        >>> oto = Oto(log_manager=log_manager)
        
        >>> # 외부에서 ConfigLoader 실행 (권장)
        >>> from cfg_utils import ConfigLoader
        >>> config = ConfigLoader(
        ...     config_loader_cfg_path="configs/loader/config_loader_oto.yaml",
        ...     env_os=["CASHOP_PATHS"]  # 사용자 정의 env 변수
        ... )
        >>> oto = Oto(cfg_like=config.to_dict(), log_manager=log_manager)
        
        >>> # 개별 cfg_like 우선 (Cascading Priority)
        >>> oto = Oto(
        ...     cfg_like=config.to_dict(),  # 병합 dict (우선순위 2)
        ...     cfg_like_translate={"target_lang": "KO"},  # 개별 cfg_like (우선순위 1)
        ...     log_manager=log_manager
        ... )
        
        >>> # Runtime override (KeyPath 형식)
        >>> oto = Oto(
        ...     cfg_like=config.to_dict(),
        ...     image_text_recognize__provider__langs=["ch", "en"],
        ...     log_manager=log_manager
        ... )
    
    Note:
        ⚠️ ConfigLoader 실행은 EntryPoint 또는 외부 스크립트 책임.
        ⚠️ cfg_like=None 사용 시: 모든 모듈이 Pydantic 기본값 사용.
    """
    
    def __init__(
        self,
        cfg_like: Union[dict, None] = None,
        *,
        cfg_like_image_load: Union[BaseModel, Path, str, dict, None] = None,
        cfg_like_image_text_recognize: Union[BaseModel, Path, str, dict, None] = None,
        cfg_like_translate: Union[BaseModel, Path, str, dict, None] = None,
        cfg_like_image_overlay: Union[BaseModel, Path, str, dict, None] = None,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Pass-through 패턴 초기화 (완전 하드코딩 제거 + 캐싱).
        
        Architecture:
            1. ConfigLoader가 모든 section 병합 (image_load, image_text_recognize, translate, image_overlay, log)
            2. SectionExtractor.extract_batch()가 Policy.name으로 section 추출 (Cascading Priority)
            3. get_policy_name() 헬퍼로 추출 결과 접근 (하드코딩 없음)
            4. 각 모듈에 추출된 cfg_like 전달 (개별 > 병합 > None)
        
        Zero Hard-coding:
            - ✅ Policy 클래스만 사용 (section 이름 불필요)
            - ✅ Policy.name 필드로 자동 추출
            - ✅ get_policy_name() 캐싱으로 성능 최적화
        
        Logging Strategy:
            - Oto: Parent logger만 관리 (전체 파이프라인 기록)
            - 개별 모듈: 자신의 policy.log로 logger 생성 (SRP 준수)
            - log_manager 전달 시: 모듈이 parent logger 사용
        
        Args:
            cfg_like: 병합된 dict 또는 None
                - dict: 외부에서 준비한 병합 dict (ConfigLoader.to_dict() 결과)
                - None: 빈 dict (개별 모듈은 Pydantic 기본값 사용)
            cfg_like_image_load: ImageLoadPolicy 개별 설정 (우선순위 1)
            cfg_like_image_text_recognize: ImageTextRecognizePolicy 개별 설정 (우선순위 1)
            cfg_like_translate: TranslatePolicy 개별 설정 (우선순위 1)
            cfg_like_image_overlay: ImageOverlayPolicy 개별 설정 (우선순위 1)
            log_manager: LogManager 인스턴스 (없으면 policy.log로 생성)
            **overrides: 런타임 오버라이드 (image_text_recognize__provider__langs=["ch","en"] 등)
        
        Cascading Priority:
            1. cfg_like_image_load (개별 cfg_like) - 최우선
            2. cfg_like["image_load"] (병합 dict의 section) - Policy.name으로 추출
            3. None (Pydantic 기본값) - fallback
        
        Example:
            >>> # 기본값 사용 (모든 모듈이 Pydantic 기본값)
            >>> oto = Oto(log_manager=log_manager)
            
            >>> # 외부에서 ConfigLoader 실행 후 전달 (권장)
            >>> from cfg_utils import ConfigLoader
            >>> config = ConfigLoader(
            ...     config_loader_cfg_path="configs/loader/config_loader_oto.yaml",
            ...     env_os=["CASHOP_PATHS"]
            ... )
            >>> oto = Oto(cfg_like=config.to_dict(), log_manager=log_manager)
            
            >>> # 개별 cfg_like 우선 (Cascading Priority)
            >>> oto = Oto(
            ...     cfg_like=config.to_dict(),  # 병합 dict (우선순위 2)
            ...     cfg_like_translate={"target_lang": "KO"},  # 개별 cfg_like (우선순위 1)
            ...     log_manager=log_manager
            ... )
            
            >>> # Runtime override (KeyPath 형식)
            >>> oto = Oto(
            ...     cfg_like=None,
            ...     image_text_recognize__provider__langs=["ch", "en"],
            ...     log_manager=log_manager
            ... )
        
        Note:
            ⚠️ ConfigLoader 실행은 EntryPoint 또는 외부 스크립트에서 수행.
            ⚠️ cfg_like=None: 모든 모듈이 Pydantic 기본값 사용 (동작하지만 권장하지 않음).
        """
        # ========================================
        # Config 준비 (외부에서 준비한 dict 또는 None)
        # ========================================
        merged_config = cfg_like or {}
        
        # Runtime overrides 병합
        if overrides:
            from keypath_utils import KeyPathDict
            override_dict = KeyPathDict.to_nested_dict(overrides)
            merged_config = {**merged_config, **override_dict}
        
        # ========================================
        # ✅ SectionExtractor.extract_batch() 사용 (완전 하드코딩 제거)
        # ========================================
        # 우선순위: 개별 cfg_like > merged_config[Policy.name] > None
        extracted = SectionExtractor.extract_batch(
            merged_config=merged_config,
            individual_cfgs={
                ImageLoadPolicy: cfg_like_image_load,
                ImageTextRecognizePolicy: cfg_like_image_text_recognize,
                TranslatePolicy: cfg_like_translate,
                ImageOverlayPolicy: cfg_like_image_overlay,
            }
        )
        
        # ✅ get_policy_name() 헬퍼로 하드코딩 제거
        self._cfg_like_image_load = extracted[
            SectionExtractor.get_policy_name(ImageLoadPolicy)
        ]
        self._cfg_like_image_text_recognize = extracted[
            SectionExtractor.get_policy_name(ImageTextRecognizePolicy)
        ]
        self._cfg_like_translate = extracted[
            SectionExtractor.get_policy_name(TranslatePolicy)
        ]
        self._cfg_like_image_overlay = extracted[
            SectionExtractor.get_policy_name(ImageOverlayPolicy)
        ]
        
        # ========================================
        # OTOPolicy 생성 (통합 정책 - 로깅 설정 추출용)
        # ========================================
        try:
            self.policy = OTOPolicy(**merged_config)
        except Exception:
            # merged_config가 비어있거나 유효하지 않으면 기본값 사용
            self.policy = OTOPolicy()
        
        # ========================================
        # Logger 설정 (Parent logger만 관리, 개별 모듈은 자체 생성)
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
        
        # 각 Adapter는 lazy-load (첫 process() 호출 시 초기화)
        self._image_load: Optional[ImageLoad] = None
        self._image_text_recognize: Optional[ImageTextRecognize] = None
        self._translate: Optional[Translate] = None
        self._image_overlay: Optional[ImageOverlay] = None
        
        self.log.debug("Oto adapter initialized (parent logger only)")
    
    # ==========================================================================
    # Adapter Lazy Loading (with log_manager injection)
    # ==========================================================================
    
    @property
    def image_load(self) -> ImageLoad:
        """ImageLoad Adapter lazy-loading.
        
        cfg_like는 SectionExtractor로 이미 추출됨 (self._cfg_like_image_load).
        """
        if self._image_load is None:
            self._image_load = ImageLoad(
                cfg_like=self._cfg_like_image_load,  # type: ignore
                log_manager=self._parent_log_manager,
            )
        return self._image_load
    
    @property
    def image_text_recognize(self) -> ImageTextRecognize:
        """ImageTextRecognize Adapter lazy-loading.
        
        cfg_like는 SectionExtractor로 이미 추출됨 (self._cfg_like_image_text_recognize).
        """
        if self._image_text_recognize is None:
            self._image_text_recognize = ImageTextRecognize(
                cfg_like=self._cfg_like_image_text_recognize,  # type: ignore
                log_manager=self._parent_log_manager,
            )
        return self._image_text_recognize
    
    @property
    def translate(self) -> Translate:
        """Translate Adapter lazy-loading.
        
        cfg_like는 SectionExtractor로 이미 추출됨 (self._cfg_like_translate).
        
        run() 메서드를 사용하므로 매번 새 인스턴스를 생성할 필요 없음.
        이미지 여러 개 처리 시 동일 인스턴스를 재사용하여 Provider 연결 유지.
        """
        if self._translate is None:
            self._translate = Translate(
                cfg_like=self._cfg_like_translate,  # type: ignore
                log_manager=self._parent_log_manager,
            )
        return self._translate
    
    @property
    def image_overlay(self) -> ImageOverlay:
        """ImageOverlay Adapter lazy-loading.
        
        cfg_like는 SectionExtractor로 이미 추출됨 (self._cfg_like_image_overlay).
        """
        if self._image_overlay is None:
            self._image_overlay = ImageOverlay(
                cfg_like=self._cfg_like_image_overlay,  # type: ignore
                log_manager=self._parent_log_manager,
            )
        return self._image_overlay
    
    # ==========================================================================
    # Core Pipeline Methods
    # ==========================================================================
    
    def run(
        self,
        source_path: Union[Path, str],
        **overrides: Any
    ) -> Dict[str, Any]:
        """OCR → Translate → Overlay 파이프라인 실행 (경로 기반).
        
        Pipeline Flow:
            1. 원본 파일명 추출 및 모든 모듈 name 정책 override
            2. ImageLoader.run(source_path) → PIL.Image
            3. ImageTextRecognize.run(image) → List[OCRItem]
            4. Translate.run(texts) → Dict[str, str]
            5. OCRItem + translated_text → OverlayItemPolicy
            6. ImageOverlay.run(image, overlay_items, **overrides) → Final Image
        
        Args:
            source_path: 소스 이미지 파일 경로
            **overrides: 각 모듈의 런타임 오버라이드 (KeyPath 형식, 모듈 접두사 포함)
                예: image_load__save__enabled=True
                    image_text_recognize__provider__langs=["ch", "en"]
                    translate__target_lang="KO"
                    image_overlay__save__directory="output"
                    image_overlay__save__name__name="test"
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "source_path": Path,           # 입력 경로
                "image": Optional[PIL.Image.Image],  # 최종 오버레이된 이미지
                "ocr_items": List[OCRItem],    # OCR 결과
                "translated_dict": Dict[str, str],  # 번역 결과
                "overlay_items": List[OverlayItemPolicy],  # 오버레이 아이템
                "error": Optional[str]
            }
        
        Example:
            >>> oto = Oto(cfg_like=policy, log_manager=log_manager)
            >>> # 기본 저장 정책 사용 (원본 파일명 자동 적용)
            >>> result = oto.run(source_path="test.jpg")
            >>> # 모든 모듈의 save.name.name이 "test"로 override됨
            >>> 
            >>> # Runtime override (모든 모듈에 전달)
            >>> result = oto.run(
            ...     source_path="test.jpg",
            ...     image_load__save__enabled=True,  # ImageLoad 저장 활성화
            ...     image_text_recognize__save__enabled=True,  # OCR JSON 저장
            ...     translate__target_lang="KO",  # 번역 언어
            ...     image_overlay__save__directory="output/cas123",  # Overlay 저장 경로
            ...     image_overlay__save__name__name="cas123_image1"  # Overlay 파일명 (원본명 무시)
            ... )
        
        Note:
            ⚠️ 원본 파일명(확장자 제외)을 모든 모듈의 save.name.name에 자동 override.
            ⚠️ 사용자가 명시적으로 *__save__name__name을 제공하면 그것이 우선.
        """
        result = {
            "success": False,
            "source_path": None,
            "image": None,
            "output_path": None,  # ImageOverlayer가 저장한 경로
            "ocr_items": [],
            "translated_dict": {},
            "overlay_items": [],
            "error": None,
        }
        
        try:
            # source_path를 Path로 변환
            source_path = Path(source_path)
            result["source_path"] = source_path
            
            self.log.info(f"{'='*80}")
            self.log.info(f"🖼️  Oto Pipeline: {source_path.name}")
            self.log.info(f"{'='*80}\n")
            
            # ====================================================================
            # Step 0: ImageLoad Adapter - 이미지 로드
            # ====================================================================
            self.log.info("[0/5] ImageLoad: Loading image...")
            
            # ImageLoad Adapter의 run() 호출 (source=파일경로, source_path=source_path)
            # ⚠️ source_path로부터 자동으로 원본 파일명 추출됨
            # ⚠️ image_load__ 접두사만 필터링하여 전달
            load_result = self.image_load.run(
                source=source_path,
                source_path=source_path,  # ⭐ save/meta/name 자동 추출
                **filter_overrides_by_prefix(
                    overrides, 
                    f"{SectionExtractor.get_policy_name(ImageLoadPolicy)}__"
                )
            )
            
            if not load_result.get("success"):
                error_msg = load_result.get("error", "Image load failed")
                self.log.error(f"❌ Image load failed: {error_msg}")
                result["error"] = error_msg
                return result
            
            image = load_result.get("image")
            if image is None:
                self.log.error("❌ No image in load result")
                result["error"] = "No image in load result"
                return result
            
            self.log.success(f"✅ Image loaded: {image.size} {image.mode}")
            
            # ====================================================================
            # Step 1: ImageTextRecognize Adapter - OCR 실행
            # ====================================================================
            self.log.info("\n[1/5] ImageTextRecognize: Running OCR...")
            
            # ImageTextRecognize Adapter의 run() 호출 (image + source_path)
            # ⚠️ source_path로부터 자동으로 원본 파일명 추출됨
            # ⚠️ image_text_recognize__ 접두사만 필터링하여 전달
            ocr_result = self.image_text_recognize.run(
                image=image,
                source_path=source_path,  # ⭐ save/meta/name 자동 추출
                **filter_overrides_by_prefix(
                    overrides,
                    f"{SectionExtractor.get_policy_name(ImageTextRecognizePolicy)}__"
                )
            )
            ocr_items: List[OCRItem] = ocr_result.get("ocr_items", [])
            image = ocr_result.get("image", image)  # ⚠️ OCR 처리된 이미지로 업데이트 (resize된 경우 포함)
            
            result['ocr_items'] = ocr_items
            
            if ocr_result.get("resized"):
                self.log.info(f"   → Image resized for OCR (scale={ocr_result.get('scale_factor', 1.0):.3f})")
            
            self.log.success(f"✅ OCR completed: {len(ocr_items)} items")
            
            if not ocr_items:
                self.log.warning("No OCR items found - skipping translation/overlay")
                result['success'] = True
                return result
            
            # ====================================================================
            # Step 2: Translate Adapter - 번역 실행
            # ====================================================================
            self.log.info("\n[2/5] Translate: Translating texts...")
            
            # OCRItem에서 텍스트 추출
            original_texts = [item.text for item in ocr_items if item.text]
            
            if not original_texts:
                self.log.warning("No texts to translate")
                result['success'] = True
                return result
            
            self.log.info(f"  Original texts: {len(original_texts)}")
            
            # Translate Adapter의 run() 호출 (배치 번역 + 세그먼트 단위 캐싱)
            # ⚠️ translate__ 접두사만 필터링하여 전달
            try:
                translated_dict = self.translate.run(
                    texts=original_texts,
                    **filter_overrides_by_prefix(
                        overrides,
                        f"{SectionExtractor.get_policy_name(TranslatePolicy)}__"
                    )
                )
                
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
            self.log.info("\n[3/5] Conversion: OCRItem → OverlayItem...")
            
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
            # Step 4: ImageOverlay Adapter - 오버레이 렌더링 + 저장
            # ====================================================================
            self.log.info("\n[4/5] ImageOverlay: Rendering overlay + saving...")
            
            # ImageOverlay Adapter의 run() 호출 (image + items + source_path + overrides)
            # ⚠️ source_path로부터 자동으로 원본 파일명 추출됨
            # ⚠️ image_overlay__ 접두사만 필터링하여 전달
            
            filtered = filter_overrides_by_prefix(
                overrides,
                f"{SectionExtractor.get_policy_name(ImageOverlayPolicy)}__"
            )
            
            overlay_result = self.image_overlay.run(
                image=image,
                items=overlay_items,
                source_path=source_path,  # ⭐ save/meta/name 자동 추출
                **filtered
            )
            
            if not overlay_result.get("success"):
                error_msg = overlay_result.get("error", "Unknown overlay error")
                self.log.error(f"❌ Overlay failed: {error_msg}")
                result['error'] = error_msg
                return result
            
            # 최종 이미지
            final_image = overlay_result.get("image")
            result["image"] = final_image
            
            self.log.success(f"✅ Overlay completed (Adapter handled save/meta)")
            
            result['success'] = True
            
            self.log.info(f"\n{'='*80}")
            self.log.success(f"✅ Oto Pipeline Completed: {source_path.name}")
            self.log.info(f"{'='*80}\n")
            
        except Exception as e:
            result['error'] = f"Unexpected error: {type(e).__name__}: {e}"
            self.log.error(result['error'])
            
            import traceback
            self.log.error(traceback.format_exc())
        
        return result
    
    def __repr__(self) -> str:
        return f"OTO(policy={self.policy.__class__.__name__})"
