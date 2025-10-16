# -*- coding: utf-8 -*-
"""ImageOCR - OCR execution entry point with preprocessing and normalization.

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
from logs_utils import LogManager
from data_utils import GeometryOps, StringOps
from path_utils import resolve

from ..core.policy import ImageOCRPolicy
from ..core.models import OCRItem
from ..services.io import ImageWriter


class ImageOCR:
    """OCR 실행 및 결과 처리 EntryPoint.
    
    ConfigLoader와 동일한 패턴으로 다양한 입력 형태를 지원합니다.
    
    Attributes:
        policy: ImageOCRPolicy 설정
        log: loguru logger 인스턴스
        ocr_engine: OCR 엔진 인스턴스 (lazy-loaded)
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        *,
        policy_overrides: Optional[Dict[str, Any]] = None,
        log: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize ImageOCR with flexible config input.
        
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
        
        # OCR 엔진은 lazy-load (첫 run() 호출 시 초기화)
        self._ocr_engine = None
        
        # ImageWriter 초기화 (FSO 기반)
        self.writer = ImageWriter(self.policy.save, self.policy.meta)
        
        # ImageLoader의 reader/processor 불필요 (OCR는 직접 PIL 사용)
        
        self.log.info(f"ImageOCR initialized: source={self.policy.source.path}, provider={self.policy.provider.provider}")
    
    def _load_config(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None],
        *,
        policy_overrides: Optional[Dict[str, Any]] = None,
        **overrides: Any
    ) -> ImageOCRPolicy:
        """설정 로드 (간소화 버전)
        
        Args:
            cfg_like: 설정 소스
            policy_overrides: ConfigPolicy 필드 개별 오버라이드
            **overrides: 런타임 오버라이드
        
        Returns:
            ImageOCRPolicy 인스턴스
        """
        # cfg_like가 None이면 기본 파일 경로 + 섹션을 policy_overrides로 지정
        if cfg_like is None:
            default_path = Path(__file__).parent.parent / "configs" / "ocr.yaml"
            if policy_overrides is None:
                policy_overrides = {}
            
            # ImageOCR 전용 ConfigLoader 정책 파일 지정
            policy_overrides.setdefault("config_loader_path", 
                str(Path(__file__).parent.parent / "configs" / "config_loader_ocr.yaml")
            )
            
            # yaml.source_paths에 dict 형태로 전달
            policy_overrides.setdefault("yaml.source_paths", {
                "path": str(default_path),
                "section": "ocr"
            })
        
        return ConfigLoader.load(
            cfg_like,
            model=ImageOCRPolicy,
            policy_overrides=policy_overrides,
            **overrides
        )
    
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
        image: Optional[Image.Image] = None,
    ) -> Dict[str, Any]:
        """OCR 실행 및 결과 처리.
        
        Args:
            source_override: 소스 경로 오버라이드 (image가 None일 때만 사용)
            image: PIL Image 객체 (제공되면 파일 로딩 없이 바로 사용)
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "image": PIL.Image.Image,
                "original_path": Optional[Path],
                "ocr_items": List[OCRItem],
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
                # 제공된 이미지 객체 사용
                img = image
                source_path = None
                self.log.info(f"Using provided image object: {img.size} {img.mode}")
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
            self.log.success("ImageOCR completed successfully")
            
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
        return f"ImageOCR(source={self.policy.source.path}, provider={self.policy.provider.provider})"
