# -*- coding: utf-8 -*-
"""ImageTextRecognizer - OCR execution entry point with preprocessing and normalization.

책임:
1. OCR 전처리 (리사이즈)
2. OCR 실행 (PaddleOCR)
3. OCR 결과 정규화 및 후처리
4. 결과 저장 및 메타데이터 관리
5. cfg_loader/logs_utils 통합
"""

import copy
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image
from pydantic import BaseModel, ValidationError

from cfg_utils import ConfigLoader
from cfg_utils.core.base_service_loader import BaseServiceLoader
from cfg_utils.core.policy import ConfigPolicy
from logs_utils import LogManager
from data_utils import GeometryOps, StringOps
from path_utils import resolve

from ..core.policy import ImageOCRPolicy
from ..core.models import OCRItem
from ..services.io import ImageWriter


class ImageTextRecognizer(BaseServiceLoader[ImageOCRPolicy]):
    """OCR 실행 및 결과 처리 EntryPoint (ImageLoader와 완전 대칭).
    
    BaseServiceLoader를 상속하여 ConfigLoader 통합 및 일관된 설정 로딩을 제공합니다.
    
    Attributes:
        policy: ImageOCRPolicy 설정
        log: loguru logger 인스턴스
        ocr_engine: OCR 엔진 인스턴스 (lazy-loaded)
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
        """ConfigLoader와 동일한 인자 패턴으로 초기화 (ImageLoader와 완전 대칭).
        
        Args:
            cfg_like: BaseModel, YAML 경로, dict, 또는 None
                - BaseModel: ImageOCRPolicy 인스턴스 직접 전달
                - str/Path: YAML 파일 경로
                - dict: 설정 딕셔너리
                - None: 기본 설정 파일 사용
            policy: ConfigPolicy 인스턴스
            config_loader_path: config_loader_ocr.yaml 경로 override (선택)
            log: 외부 LogManager (없으면 policy.log로 생성)
            **overrides: 런타임 오버라이드 값 (source__path, provider__langs 등)
        
        Example:
            >>> # YAML 파일에서 로드
            >>> ocr = ImageTextRecognizer("configs/ocr.yaml")
            
            >>> # dict로 직접 설정
            >>> ocr = ImageTextRecognizer({"source": {"path": "test.jpg"}})
            
            >>> # config_loader_path override
            >>> ocr = ImageTextRecognizer(config_loader_path="./custom_config_loader.yaml")
            
            >>> # 런타임 오버라이드 (KeyPath 형식)
            >>> ocr = ImageTextRecognizer("config.yaml", source__path="image.jpg", provider__langs=["ch"])
        """
        # BaseServiceLoader 초기화 (self.policy 설정)
        super().__init__(cfg_like, policy=policy, config_loader_path=config_loader_path, **overrides)
        
        # LogManager 초기화
        if log is None:
            log_manager = LogManager(self.policy.log)
            self.log = log_manager.logger
        else:
            self.log = log.logger if isinstance(log, LogManager) else log
        
        # OCR 엔진은 lazy-load (첫 run() 호출 시 초기화)
        self._ocr_engine = None
        
        # ImageWriter 초기화 (FSO 기반)
        self.writer = ImageWriter(self.policy.save, self.policy.meta)
        
        self.log.info(f"ImageTextRecognizer initialized: source={self.policy.source.path}, provider={self.policy.provider.provider}")
    
    # ==========================================================================
    # BaseServiceLoader Abstract Methods Implementation
    # ==========================================================================
    
    def _get_policy_model(self) -> type[ImageOCRPolicy]:
        """Policy 모델 클래스 반환."""
        return ImageOCRPolicy
    
    def _get_config_loader_path(self) -> Path:
        """config_loader_ocr.yaml 경로 반환."""
        return Path(__file__).parent.parent / "configs" / "config_loader_ocr.yaml"
    
    def _get_default_section(self) -> str:
        """기본 section 이름: 'ocr'."""
        return "ocr"
    
    def _get_config_path(self) -> Path:
        """마지막 안전 장치용 기본 설정 파일: ocr.yaml."""
        return Path(__file__).parent.parent / "configs" / "ocr.yaml"
    
    def _get_reference_context(self) -> dict[str, Any]:
        """paths.local.yaml을 reference_context로 제공."""
        from modules.cfg_utils.services.paths_loader import PathsLoader
        try:
            return PathsLoader.load()
        except FileNotFoundError:
            # paths.local.yaml이 없어도 동작 계속 (선택 사항)
            return {}
    
    # ==========================================================================
    # OCR Engine Management
    # ==========================================================================
    
    @property
    def ocr_engine(self):
        """OCR 엔진 lazy-loading."""
        if self._ocr_engine is None:
            self._load_ocr_engine()
        return self._ocr_engine
    
    def _load_ocr_engine(self):
        """OCR 엔진 초기화 (현재는 PaddleOCR만 지원)."""
        provider = self.policy.provider.provider
        
        if provider == "paddle":
            try:
                from paddleocr import PaddleOCR
                
                self.log.info(f"Initializing PaddleOCR: langs={self.policy.provider.langs}")
                
                # PaddleOCR 초기화 옵션
                ocr_kwargs = {
                    "use_angle_cls": self.policy.provider.paddle_use_angle_cls,
                    "lang": self.policy.provider.langs[0] if self.policy.provider.langs else "ch",
                }
                
                self._ocr_engine = PaddleOCR(**ocr_kwargs)
                self.log.success("PaddleOCR initialized successfully")
                
            except ImportError as e:
                self.log.error(f"PaddleOCR not installed: {e}")
                raise ImportError("PaddleOCR is required. Install with: pip install paddleocr paddlepaddle")
        else:
            raise ValueError(f"Unsupported OCR provider: {provider}")
    
    # ==========================================================================
    # Private Methods
    # ==========================================================================
    
    def _normalize_ocr_result(self, raw_result: List) -> List[OCRItem]:
        """PaddleOCR 결과를 OCRItem으로 정규화.
        
        PaddleX/PaddleOCR 최신 버전 형식:
        - raw_result: list[dict]
        - 각 dict: {"rec_boxes": [[x1,y1,x2,y2], ...], "rec_texts": [...], "rec_scores": [...]}
        
        Args:
            raw_result: PaddleOCR predict() 결과
            
        Returns:
            OCRItem 리스트
        """
        items = []
        
        if not raw_result:
            return items
        
        order = 0
        for item_dict in raw_result:
            # 최신 PaddleOCR 형식
            boxes = item_dict.get("rec_boxes")
            texts = item_dict.get("rec_texts")
            scores = item_dict.get("rec_scores")
            
            # numpy.ndarray → list 변환
            if hasattr(boxes, "tolist"):
                boxes = boxes.tolist()
            
            if not (isinstance(boxes, list) and isinstance(texts, list)):
                continue
            
            if not isinstance(scores, list):
                scores = [1.0] * len(texts)
            
            # 각 텍스트 항목 처리
            for box, text, score in zip(boxes, texts, scores):
                if not (isinstance(box, (list, tuple)) and len(box) == 4):
                    continue
                
                # rec_boxes: [x_min, y_min, x_max, y_max]
                x1, y1, x2, y2 = map(float, box)
                
                # quad 구성 (좌상→우상→우하→좌하)
                quad = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                
                try:
                    conf = float(score)
                except Exception:
                    conf = 0.0
                
                # bbox 계산
                bbox = {
                    "x_min": x1,
                    "y_min": y1,
                    "x_max": x2,
                    "y_max": y2,
                }
                
                # 각도 계산 (상단 변 기준)
                import math
                angle_deg = math.degrees(math.atan2(y1 - y1, x2 - x1))  # 수평이므로 0도
                
                item = OCRItem(
                    text=str(text),
                    conf=conf,
                    quad=quad,
                    bbox=bbox,
                    angle_deg=angle_deg,
                    lang=self.policy.provider.langs[0] if self.policy.provider.langs else "unknown",
                    order=order,
                )
                
                items.append(item)
                order += 1
        
        return items
    
    def _postprocess_items(self, items: List[OCRItem]) -> List[OCRItem]:
        """OCR 결과 후처리.
        
        Args:
            items: OCRItem 리스트
            
        Returns:
            후처리된 OCRItem 리스트
        """
        processed = items
        
        # 1. 신뢰도 필터링
        if self.policy.provider.min_conf > 0:
            before = len(processed)
            processed = [item for item in processed if item.conf >= self.policy.provider.min_conf]
            if len(processed) < before:
                self.log.info(f"Filtered by confidence: {before} -> {len(processed)}")
        
        # 2. 특수문자 제거 (StringOps 사용)
        if self.policy.postprocess.strip_special_chars:
            for item in processed:
                original = item.text
                item.text = StringOps.strip_special_chars(item.text)
                if item.text != original:
                    self.log.debug(f"Stripped special chars: '{original}' -> '{item.text}'")
        
        # 3. 영숫자 필터링 (StringOps 사용)
        if self.policy.postprocess.filter_alphanumeric:
            before = len(processed)
            processed = [
                item for item in processed 
                if item.text.strip() and not StringOps.is_alphanumeric_only(item.text)
            ]
            if len(processed) < before:
                self.log.info(f"Filtered alphanumeric-only items: {before} -> {len(processed)}")
        
        # 4. 중복 제거 (IoU 기반 - GeometryOps 사용)
        if self.policy.postprocess.deduplicate_iou_threshold > 0:
            processed = self._deduplicate_by_iou(
                processed,
                threshold=self.policy.postprocess.deduplicate_iou_threshold
            )
        
        # 5. 언어 우선순위 정렬
        if self.policy.postprocess.prefer_lang_order:
            lang_priority = {lang: idx for idx, lang in enumerate(self.policy.provider.langs)}
            processed = sorted(
                processed,
                key=lambda x: (lang_priority.get(x.lang, 999), x.order)
            )
        
        return processed
    
    def _deduplicate_by_iou(self, items: List[OCRItem], threshold: float) -> List[OCRItem]:
        """IoU 기반 중복 제거 (언어 우선순위 + 신뢰도 기반).
        
        백업 파일 로직:
        - 정렬 우선순위: 신뢰도 내림차순 → 언어 선호도
        - 이미 채택된 박스와 IoU >= threshold면 스킵
        """
        if not items:
            return items
        
        # bbox 형식 변환: {x_min, y_min, x_max, y_max} → {x0, y0, x1, y1}
        def convert_bbox(bbox: Dict) -> Dict:
            return {
                "x0": bbox["x_min"],
                "y0": bbox["y_min"],
                "x1": bbox["x_max"],
                "y1": bbox["y_max"],
            }
        
        # 언어 우선순위 함수
        prefer_lang_order = self.policy.postprocess.prefer_lang_order or ["ch", "en"]
        def lang_rank(lang: str) -> int:
            return prefer_lang_order.index(lang) if lang in prefer_lang_order else len(prefer_lang_order)
        
        # 신뢰도 내림차순 → 언어 우선순위 정렬
        sorted_items = sorted(items, key=lambda x: (-x.conf, lang_rank(x.lang)))
        keep = []
        
        for item in sorted_items:
            # 이미 keep에 있는 항목과 IoU 비교
            is_duplicate = False
            item_bbox = convert_bbox(item.bbox)
            
            for kept_item in keep:
                kept_bbox = convert_bbox(kept_item.bbox)
                iou = GeometryOps.bbox_intersection_over_union(item_bbox, kept_bbox)
                
                if iou >= threshold:
                    is_duplicate = True
                    self.log.debug(f"Duplicate removed: '{item.text}' (IoU={iou:.2f} with '{kept_item.text}')")
                    break
            
            if not is_duplicate:
                keep.append(item)
        
        # 원래 순서로 재정렬
        keep = sorted(keep, key=lambda x: x.order)
        
        if len(keep) < len(items):
            self.log.info(f"Deduplication: {len(items)} -> {len(keep)}")
        
        return keep
    
    def run(
        self,
        source_override: Optional[Union[str, Path]] = None,
        image: Optional[Union["Image.Image", List["Image.Image"]]] = None,
    ) -> Dict[str, Any]:
        """OCR 실행 및 결과 처리.
        
        ImageLoader와 동일한 구조를 따르되, 추가로 Pillow 객체 리스트도 지원합니다.
        
        Args:
            source_override: 소스 경로 오버라이드 (image가 None일 때만 사용)
            image: PIL Image 객체 또는 리스트 (제공되면 파일 로딩 없이 바로 사용)
                  - 단일 Image.Image: 해당 이미지만 처리
                  - List[Image.Image]: 첫 번째 이미지 처리 (일관성 유지)
                  - ImageFile, JpegImagePlugin 등 모든 PIL 서브클래스 지원
        
        Returns:
            결과 딕셔너리 (ImageLoader와 일관성 유지):
            {
                "success": bool,
                "image": PIL.Image.Image,  # 처리된 단일 이미지
                "original_path": Optional[Path],
                "ocr_items": List[OCRItem],  # 여러 OCR 결과 (리스트)
                "saved_path": Optional[Path],
                "meta_path": Optional[Path],
                "original_size": Tuple[int, int],
                "preprocessed_size": Optional[Tuple[int, int]],
                "error": Optional[str]
            }
        """
        result = {
            "success": False,
            "image": None,
            "original_path": None,
            "ocr_items": [],
            "saved_path": None,
            "meta_path": None,
            "original_size": None,
            "preprocessed_size": None,
            "error": None,
        }
        
        try:
            # 1. 이미지 소스 결정
            if image is not None:
                # 제공된 이미지 객체 사용 (단일 또는 리스트)
                if isinstance(image, list):
                    # 리스트인 경우: 첫 번째 이미지 사용 (ImageLoader와 일관성)
                    if not image:
                        raise ValueError("Empty image list provided")
                    img = image[0]
                    self.log.info(f"Using first image from list ({len(image)} total): {img.size} {img.mode}")
                else:
                    # 단일 이미지
                    img = image
                    self.log.info(f"Using provided image object: {img.size} {img.mode}")
                
                source_path = None
            else:
                # 파일에서 로드
                source_path = source_override or self.policy.source.path
                source_path = resolve(source_path)
                result["original_path"] = source_path
                
                self.log.info(f"Loading image for OCR: {source_path}")
                
                # PIL Image로 직접 로드
                img = Image.open(source_path)
                
                # EXIF orientation 처리
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
                
                # convert_mode 처리
                if self.policy.source.convert_mode:
                    img = img.convert(self.policy.source.convert_mode)
            
            result["original_path"] = source_path
            result["original_size"] = img.size
            
            self.log.info(f"Image ready for OCR: {img.size} {img.mode}")
            
            # 3. 전처리 (리사이즈)
            preprocessed_img = img
            if self.policy.preprocess.max_width and img.width > self.policy.preprocess.max_width:
                self.log.info(f"Resizing for OCR: {img.width} -> {self.policy.preprocess.max_width}")
                
                scale = self.policy.preprocess.max_width / img.width
                new_height = int(img.height * scale)
                preprocessed_img = img.resize(
                    (self.policy.preprocess.max_width, new_height),
                    Image.Resampling.LANCZOS
                )
            
            result["preprocessed_size"] = preprocessed_img.size
            
            # 4. OCR 실행
            self.log.info("Running OCR...")
            
            # PIL Image를 numpy array로 변환
            import numpy as np
            img_array = np.array(preprocessed_img)
            
            # PaddleOCR predict (최신 버전은 cls 인자 미지원)
            raw_result = self.ocr_engine.predict(img_array)
            
            # 5. 결과 정규화
            ocr_items = self._normalize_ocr_result(raw_result)
            self.log.info(f"OCR detected {len(ocr_items)} items")
            
            # 6. 후처리
            ocr_items = self._postprocess_items(ocr_items)
            result["ocr_items"] = ocr_items
            
            self.log.success(f"OCR completed: {len(ocr_items)} items after postprocessing")
            
            # 7. 결과 이미지 저장 (선택)
            if self.policy.save.save_copy and source_path:
                self.log.info("Saving OCR result image...")
                
                saved_path = self.writer.save_image(
                    image=preprocessed_img,
                    base_path=source_path,
                )
                result["saved_path"] = saved_path
                self.log.success(f"Saved to: {saved_path}")
            
            # 8. 메타데이터 저장
            if self.policy.meta.save_meta and source_path:
                self.log.info("Saving OCR metadata...")
                
                meta_data = {
                    "original_path": str(source_path) if source_path else None,
                    "original_size": result["original_size"],
                    "preprocessed_size": result["preprocessed_size"],
                    "saved_path": str(result["saved_path"]) if result["saved_path"] else None,
                    "ocr_items": [item.model_dump() for item in ocr_items],
                    "provider": {
                        "name": self.policy.provider.provider,
                        "langs": self.policy.provider.langs,
                        "min_conf": self.policy.provider.min_conf,
                    }
                }
                
                # Use ImageWriter for metadata with FSO
                meta_path = self.writer.save_meta(meta_data, source_path)
                if meta_path:
                    result["meta_path"] = meta_path
                    self.log.success(f"Metadata saved to: {meta_path}")
            
            # 9. Image 객체 반환에 추가
            result["image"] = preprocessed_img
            result["success"] = True
            self.log.success("ImageTextRecognizer completed successfully")
            
        except FileNotFoundError as e:
            result["error"] = f"File not found: {e}"
            self.log.error(result["error"])
        except ImportError as e:
            result["error"] = f"Import error: {e}"
            self.log.error(result["error"])
        except ValidationError as e:
            result["error"] = f"Validation error: {e}"
            self.log.error(result["error"])
        except Exception as e:
            result["error"] = f"Unexpected error: {type(e).__name__}: {e}"
            self.log.error(result["error"])
        
        return result
    
    def __repr__(self) -> str:
        return f"ImageTextRecognizer(source={self.policy.source.path}, provider={self.policy.provider.provider})"

