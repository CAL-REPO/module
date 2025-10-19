# -*- coding: utf-8 -*-
"""ImageTextRecognize - Core OCR adapter (Translate pattern).

책임:
1. OCR 실행 (PaddleOCR)
2. OCR 결과 정규화 및 후처리
3. run(image) API 제공

translate_utils의 Translate와 동일한 패턴:
- Policy: ImageTextRecognizePolicy (source 없음)
- __init__: cfg_like만 받음
- run(image): Image 객체 받아서 텍스트 인식
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import math

from PIL import Image
import numpy as np

from logs_utils import LogManager
from data_utils import GeometryOps, StringOps

from ..core.policy import ImageTextRecognizePolicy
from ..core.models import OCRItem


class ImageTextRecognize:
    """OCR processing adapter (Translate pattern).
    
    translate_utils의 Translate와 동일한 구조:
    - Policy: ImageTextRecognizePolicy (source 없음)
    - run(image): Image 객체 받아서 처리
    
    Attributes:
        policy: ImageTextRecognizePolicy 설정
        log: loguru logger
        ocr_engine: OCR 엔진 (lazy-loaded)
    """
    
    def __init__(
        self,
        cfg_like: Union[Path, str, dict, ImageTextRecognizePolicy, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize ImageTextRecognize adapter.
        
        Args:
            cfg_like: ImageTextRecognizePolicy, YAML 경로, dict, 또는 None
            log_manager: 외부 LogManager (선택사항)
            **overrides: 런타임 오버라이드
        
        Example:
            >>> ocr = ImageTextRecognize("configs/ocr.yaml")
            >>> ocr = ImageTextRecognize({"provider": {"provider": "paddle"}})
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
        
        # OCR 엔진은 lazy-load
        self._ocr_engine = None
        
        self.log.debug("ImageTextRecognize initialized")
    
    # ==========================================================================
    # Config Loading
    # ==========================================================================
    
    def _load_config(self, cfg_like, **overrides) -> ImageTextRecognizePolicy:
        """Load ImageTextRecognizePolicy."""
        from cfg_utils.services.config_like_loader import ConfigLikeLoader
        
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=ImageTextRecognizePolicy,
            caller_file=__file__,
            default_config_filename="ocr.yaml",
            **overrides
        )
    
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
    # Main API (Translate pattern)
    # ==========================================================================
    
    def run(self, image: Image.Image) -> Dict[str, Any]:
        """이미지에서 텍스트 인식 (Translate.run() pattern).
        
        Args:
            image: PIL Image 객체
        
        Returns:
            결과 딕셔너리:
            {
                "ocr_items": List[OCRItem],  # 원본 크기 기준 좌표
                "image": Image.Image,         # OCR 처리된 이미지 (원본 or resize)
                "original_size": Tuple[int, int],
                "resized": bool,
                "scale_factor": float
            }
        
        Example:
            >>> ocr = ImageTextRecognize("configs/ocr.yaml")
            >>> img = Image.open("test.jpg")
            >>> result = ocr.run(img)
            >>> items = result["ocr_items"]
            >>> processed_img = result["image"]
        """
        self.log.info(f"Running OCR on image: {image.size} {image.mode}")
        
        # 원본 크기 저장
        original_size = image.size
        
        # 전처리: max_width에 맞춰 resize
        scale_factor = 1.0
        if self.policy.preprocess.max_width and image.width > self.policy.preprocess.max_width:
            scale_factor = self.policy.preprocess.max_width / image.width
            new_height = int(image.height * scale_factor)
            image = image.resize(
                (self.policy.preprocess.max_width, new_height),
                Image.Resampling.LANCZOS
            )
            self.log.info(f"Resized for OCR: {original_size} -> {image.size} (scale={scale_factor:.3f})")
        
        # PIL Image를 numpy array로 변환
        img_array = np.array(image)
        
        # 🔍 디버깅: OCR 입력 이미지 정보
        self.log.info(f"\n{'='*80}")
        self.log.info(f"[OCR INPUT DEBUG] PIL Image size: {image.size} (width, height)")
        self.log.info(f"[OCR INPUT DEBUG] numpy array shape: {img_array.shape} (height, width, channels)")
        self.log.info(f"[OCR INPUT DEBUG] Image mode: {image.mode}")
        self.log.info(f"{'='*80}\n")
        
        # 🔍 디버깅: OCR 입력 이미지 저장
        debug_dir = Path(r"M:\CALife\CAShop - 구매대행\_public\01.IMAGE\CAPEA-001\translated")
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_input_path = debug_dir / "debug_ocr_input.jpg"
        image.save(debug_input_path, quality=95)
        self.log.info(f"[DEBUG] Saved OCR input image to: {debug_input_path}")
        
        # PaddleOCR는 BGR 형식을 기대 (OpenCV 호환)
        if img_array.ndim == 3 and img_array.shape[2] == 3:
            img_array = img_array[:, :, ::-1]  # RGB → BGR
        
        # PaddleOCR predict (문서 전처리 비활성화)
        raw_result = self.ocr_engine.predict(
            img_array,
            use_doc_orientation_classify=False,  # 🔧 문서 방향 분류 비활성화
            use_doc_unwarping=False              # 🔧 문서 왜곡 보정 비활성화
        )
        
        # 🔍 디버깅: PaddleOCR output_img 저장
        if raw_result and len(raw_result) > 0:
            first_result = raw_result[0]
            if hasattr(first_result, 'get') and 'doc_preprocessor_res' in first_result:
                doc_res = first_result['doc_preprocessor_res']
                if 'output_img' in doc_res:
                    output_img_array = doc_res['output_img']
                    # BGR → RGB
                    if output_img_array.ndim == 3 and output_img_array.shape[2] == 3:
                        output_img_array = output_img_array[:, :, ::-1]
                    output_img = Image.fromarray(output_img_array)
                    debug_output_path = debug_dir / "debug_paddle_output.jpg"
                    output_img.save(debug_output_path, quality=95)
                    self.log.info(f"[DEBUG] Saved PaddleOCR output_img to: {debug_output_path}")
        
        # 🔍 디버깅: PaddleOCR 원본 출력 확인
        self.log.info(f"\n{'='*80}")
        self.log.info(f"[OCR RAW DEBUG] PaddleOCR raw_result type: {type(raw_result)}")
        self.log.info(f"[OCR RAW DEBUG] Length: {len(raw_result) if raw_result else 0}")
        if raw_result and len(raw_result) > 0:
            self.log.info(f"[OCR RAW DEBUG] First item type: {type(raw_result[0])}")
            self.log.info(f"[OCR RAW DEBUG] First item keys: {raw_result[0].keys() if isinstance(raw_result[0], dict) else 'N/A'}")
            self.log.info(f"[OCR RAW DEBUG] First item sample:")
            self.log.info(f"{raw_result[0]}")
        self.log.info(f"{'='*80}\n")
        
        # 결과 정규화
        ocr_items = self._normalize_ocr_result(raw_result)
        self.log.info(f"OCR detected {len(ocr_items)} items")
        
        # 🔍 디버깅: OCR 결과 좌표 샘플 출력
        if ocr_items:
            self.log.info(f"\n{'='*80}")
            self.log.info(f"[OCR DEBUG] Image size: {image.size} (resized={scale_factor != 1.0}, scale={scale_factor:.3f})")
            self.log.info(f"[OCR DEBUG] Sample items (first 3):")
            for i, item in enumerate(ocr_items[:3]):
                self.log.info(f"  [{i+1}] text='{item.text}'")
                self.log.info(f"      bbox={item.bbox}")
                self.log.info(f"      quad={item.quad}")
                self.log.info(f"      conf={item.conf:.2f}, lang={item.lang}")
            self.log.info(f"{'='*80}\n")
        
        # ⚠️ 좌표 스케일링은 하지 않음!
        # OCR 좌표를 resize된 이미지 기준으로 유지
        # Overlay도 동일한 resize된 이미지를 사용하므로 좌표가 일치함
        
        # 후처리
        ocr_items = self._postprocess_items(ocr_items)
        
        # 🔧 임시 수정: Y좌표 보정 (+100 픽셀)
        # PaddleOCR이 Y좌표를 약 100픽셀 위로 잘못 감지하는 문제 보정
        Y_OFFSET = 100
        self.log.warning(f"[WORKAROUND] Applying Y-offset correction: +{Y_OFFSET}px")
        for item in ocr_items:
            # quad 보정
            item.quad = [[x, y + Y_OFFSET] for x, y in item.quad]
            # bbox 보정
            item.bbox["y_min"] += Y_OFFSET
            item.bbox["y_max"] += Y_OFFSET
        
        self.log.success(f"OCR completed: {len(ocr_items)} items after postprocessing")
        
        # 결과 반환 (이미지 + 좌표 모두 resize된 크기 기준)
        return {
            "ocr_items": ocr_items,  # resize된 이미지 기준 좌표
            "image": image,  # resize된 이미지 (또는 원본)
            "original_size": original_size,
            "resized": scale_factor != 1.0,
            "scale_factor": scale_factor
        }
    
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
            # PaddleX/PaddleOCR 형식
            boxes = item_dict.get("rec_boxes")  # bbox 형식: [x_min, y_min, x_max, y_max]
            polys = item_dict.get("rec_polys")  # polygon 형식: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            texts = item_dict.get("rec_texts")
            scores = item_dict.get("rec_scores")
            
            # numpy.ndarray → list 변환
            # 🔍 디버깅: polys 타입 확인
            self.log.info(f"\n[POLYS DEBUG] polys type: {type(polys)}")
            if polys:
                self.log.info(f"[POLYS DEBUG] polys length: {len(polys)}")
                self.log.info(f"[POLYS DEBUG] polys[0] type: {type(polys[0])}")
                self.log.info(f"[POLYS DEBUG] polys[0] content: {polys[0]}")
                self.log.info(f"[POLYS DEBUG] polys[1] type: {type(polys[1])}")
                self.log.info(f"[POLYS DEBUG] polys[1] content: {polys[1]}")
            
            if hasattr(boxes, "tolist"):
                boxes = boxes.tolist()
            if hasattr(polys, "tolist"):
                polys = polys.tolist()
            
            # 🔍 디버깅: tolist() 후
            self.log.info(f"[POLYS DEBUG] After tolist() - polys type: {type(polys)}")
            if polys:
                self.log.info(f"[POLYS DEBUG] After tolist() - polys[0] type: {type(polys[0])}")
                self.log.info(f"[POLYS DEBUG] After tolist() - polys[0]: {polys[0]}")
                self.log.info(f"[POLYS DEBUG] After tolist() - polys[1] type: {type(polys[1])}")
                self.log.info(f"[POLYS DEBUG] After tolist() - polys[1]: {polys[1]}\n")
            
            if not isinstance(texts, list):
                continue
            
            if not isinstance(scores, list):
                scores = [1.0] * len(texts)
            
            # 각 텍스트 항목 처리
            for idx, (text, score) in enumerate(zip(texts, scores)):
                # ✅ rec_polys 우선 사용 (실제 감지 영역)
                if polys and idx < len(polys):
                    poly = polys[idx]
                    if hasattr(poly, "tolist"):
                        poly = poly.tolist()
                    
                    # 🔍 디버깅: 원본 poly 확인 (첫 3개만)
                    if order < 3:
                        self.log.info(f"\n[NORMALIZE DEBUG] [{order}] text='{text}'")
                        self.log.info(f"  poly (raw): {poly}")
                        self.log.info(f"  poly type: {type(poly)}, len: {len(poly) if isinstance(poly, list) else 'N/A'}")
                    
                    # polygon은 4점: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    if isinstance(poly, list) and len(poly) == 4:
                        # quad 그대로 사용
                        quad = [[float(pt[0]), float(pt[1])] for pt in poly]
                        
                        # bbox 계산 (quad에서 min/max 추출)
                        xs = [pt[0] for pt in quad]
                        ys = [pt[1] for pt in quad]
                        bbox = {
                            "x_min": min(xs),
                            "y_min": min(ys),
                            "x_max": max(xs),
                            "y_max": max(ys),
                        }
                        
                        # 🔍 디버깅: 계산된 좌표 확인 (첫 3개만)
                        if order < 3:
                            self.log.info(f"  quad (converted): {quad}")
                            self.log.info(f"  bbox (calculated): {bbox}")
                    else:
                        continue
                
                # ⚠️ fallback: rec_boxes 사용 (polygon 없을 때만)
                elif boxes and idx < len(boxes):
                    box = boxes[idx]
                    if not (isinstance(box, (list, tuple)) and len(box) == 4):
                        continue
                    
                    # rec_boxes: [x_min, y_min, x_max, y_max]
                    x1, y1, x2, y2 = map(float, box)
                    
                    # quad 구성 (좌상→우상→우하→좌하)
                    quad = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                    
                    bbox = {
                        "x_min": x1,
                        "y_min": y1,
                        "x_max": x2,
                        "y_max": y2,
                    }
                else:
                    continue
                
                # 신뢰도
                try:
                    conf = float(score)
                except Exception:
                    conf = 0.0
                
                # 각도 계산 (quad 기준 - 좌상→우상 벡터)
                if len(quad) >= 2:
                    dx = quad[1][0] - quad[0][0]
                    dy = quad[1][1] - quad[0][1]
                    angle_deg = math.degrees(math.atan2(dy, dx))
                else:
                    angle_deg = 0.0
                
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
    
    def _scale_coordinates(self, items: List[OCRItem], scale: float) -> List[OCRItem]:
        """OCRItem의 좌표를 스케일링.
        
        resize된 이미지로 OCR을 수행한 경우, 좌표를 원본 크기로 복원하기 위해 사용.
        
        Args:
            items: OCRItem 리스트
            scale: 스케일 비율 (원본 / resize = 1.0 / scale_factor)
            
        Returns:
            스케일링된 OCRItem 리스트
        """
        scaled_items = []
        
        for item in items:
            # quad 스케일링
            scaled_quad = [[x * scale, y * scale] for x, y in item.quad]
            
            # bbox 스케일링
            scaled_bbox = {
                "x_min": item.bbox["x_min"] * scale,
                "y_min": item.bbox["y_min"] * scale,
                "x_max": item.bbox["x_max"] * scale,
                "y_max": item.bbox["y_max"] * scale,
            }
            
            # OCRItem 복사 및 좌표 업데이트
            scaled_item = OCRItem(
                text=item.text,
                conf=item.conf,
                quad=scaled_quad,
                bbox=scaled_bbox,
                angle_deg=item.angle_deg,  # 각도는 변하지 않음
                lang=item.lang,
                order=item.order,
            )
            
            scaled_items.append(scaled_item)
        
        return scaled_items
    
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
        
        Args:
            items: OCRItem 리스트
            threshold: IoU threshold (0.0-1.0)
            
        Returns:
            중복 제거된 OCRItem 리스트
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
    
    def __repr__(self) -> str:
        return f"ImageTextRecognize(provider={self.policy.provider.provider}, langs={self.policy.provider.langs})"
