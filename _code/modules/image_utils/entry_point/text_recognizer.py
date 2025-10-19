# -*- coding: utf-8 -*-
"""ImageTextRecognizer - OCR entry point (Translator pattern).

책임:
1. source에서 이미지 파일 로드
2. ImageTextRecognize adapter에 위임하여 OCR 처리
3. 결과 저장 (정책에 따라)

translate_utils의 Translator와 동일한 패턴:
- Policy: ImageTextRecognizerPolicy (source + text_recognize)
- source에서 데이터 로드
- adapter.run(data) 호출
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image, ImageOps

from logs_utils import LogManager
from path_utils import resolve

from ..core.policy import ImageTextRecognizerPolicy
from ..adapter.text_recognize import ImageTextRecognize
from ..core.models import OCRItem


class ImageTextRecognizer:
    """OCR 텍스트 인식 EntryPoint (Translator pattern).
    
    translate_utils의 Translator와 동일한 구조:
    - source에서 이미지 파일 로드
    - ImageTextRecognize adapter에 위임하여 처리
    - 결과 저장
    
    Attributes:
        policy: ImageTextRecognizerPolicy 설정 (source + text_recognize)
        text_recognize: ImageTextRecognize 인스턴스
        log: loguru logger
    """
    
    def __init__(
        self,
        cfg_like: Union[Path, str, dict, ImageTextRecognizerPolicy, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize ImageTextRecognizer.
        
        Args:
            cfg_like: ImageTextRecognizerPolicy, YAML 경로, dict, 또는 None
            log_manager: 외부 LogManager (선택사항)
            **overrides: 런타임 오버라이드 (source__path 등)
        
        Example:
            >>> recognizer = ImageTextRecognizer("configs/ocr.yaml")
            >>> recognizer = ImageTextRecognizer({"source": {"path": "test.jpg"}})
        """
        # Load policy
        self.policy = self._load_config(cfg_like, **overrides)
        
        # ImageTextRecognize adapter 생성 (text_recognize policy만 전달)
        self.text_recognize = ImageTextRecognize(
            cfg_like=self.policy.text_recognize,
            log_manager=log_manager
        )
        
        # Log는 adapter의 log 사용
        self.log = self.text_recognize.log
        
        self.log.info(f"ImageTextRecognizer initialized: source={self.policy.source.path}")
    
    # ==========================================================================
    # Config Loading
    # ==========================================================================
    
    def _load_config(self, cfg_like, **overrides) -> ImageTextRecognizerPolicy:
        """Load ImageTextRecognizerPolicy."""
        from cfg_utils.services.config_like_loader import ConfigLikeLoader
        
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=ImageTextRecognizerPolicy,
            caller_file=__file__,
            default_config_filename="ocr.yaml",
            **overrides
        )
    
    # ==========================================================================
    # Main Execution (Translator pattern)
    # ==========================================================================
    
    def run(
        self,
        source_override: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """OCR 실행 (Translator.run() pattern).
        
        1. source에서 이미지 파일 로드
        2. ImageTextRecognize adapter의 run()에 Image 객체 전달
        3. 결과 반환
        
        Args:
            source_override: 소스 경로 오버라이드 (None이면 policy.source.path 사용)
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "image": PIL.Image.Image,
                "ocr_items": List[OCRItem],
                "source_path": Path,
                "original_size": Tuple[int, int],
                "error": Optional[str]
            }
        """
        self.log.info("=" * 70)
        self.log.info("[ImageTextRecognizer] Starting OCR processing")
        
        result = {
            "success": False,
            "image": None,
            "ocr_items": [],
            "source_path": None,
            "original_size": None,
            "error": None,
        }
        
        try:
            # 1. source 경로 결정
            source_path = source_override or self.policy.source.path
            if source_path is None:
                raise ValueError("source_path must be provided or set in policy.source.path")
            
            source_path = resolve(Path(source_path))
            result["source_path"] = source_path
            
            self.log.info(f"  Source: {source_path}")
            
            # 2. 파일 존재 확인
            if not source_path.exists() and self.policy.source.must_exist:
                raise FileNotFoundError(f"Image not found: {source_path}")
            
            # 3. 이미지 로드
            img = Image.open(source_path)
            img = ImageOps.exif_transpose(img)
            
            self.log.info(f"  Loaded: {img.size} {img.mode}")
            result["original_size"] = img.size
            
            # 4. ImageTextRecognize adapter에 위임 (Image 객체 전달)
            ocr_result = self.text_recognize.run(img)
            
            # 5. 결과 저장
            result["image"] = ocr_result.get("image", img)
            result["ocr_items"] = ocr_result.get("ocr_items", [])
            result["success"] = True
            
            self.log.success(f"[ImageTextRecognizer] Completed: {len(result['ocr_items'])} items")
            
        except FileNotFoundError as e:
            result["error"] = f"File not found: {e}"
            self.log.error(result["error"])
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            self.log.error(result["error"])
        
        self.log.info("=" * 70)
        
        return result
    
    def __repr__(self) -> str:
        return f"ImageTextRecognizer(source={self.policy.source.path})"
