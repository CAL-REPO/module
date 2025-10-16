# -*- coding: utf-8 -*-
"""ImageLoader - Image loading, copying, and processing entry point.

책임:
1. 이미지 로드 및 복사
2. 리사이즈, 블러 등 기본 처리
3. 메타데이터 저장
4. cfg_loader/logs_utils 통합
"""

import copy
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image
from pydantic import BaseModel, ValidationError

from modules.structured_io.core.base_policy import SourcePathConfig
from cfg_utils import ConfigLoader
from logs_utils import LogManager
from path_utils import resolve

from ..core.policy import ImageLoaderPolicy
from ..services.io import ImageWriter


class ImageLoader:
    """이미지 로드 및 기본 처리 EntryPoint.
    
    ConfigLoader와 동일한 패턴으로 다양한 입력 형태를 지원합니다.
    
    Attributes:
        policy: ImageLoaderPolicy 설정
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
        """ConfigLoader와 동일한 인자 패턴으로 초기화.
        
        Args:
            cfg_like: BaseModel, YAML 경로, dict, 또는 None
                - BaseModel: ImageLoaderPolicy 인스턴스 직접 전달
                - str/Path: YAML 파일 경로
                - dict: 설정 딕셔너리
                - None: 기본 설정 파일 사용
            policy_overrides: ConfigPolicy 필드 개별 오버라이드 (merge_mode, yaml.source_paths 등)
            log: 외부 LogManager (없으면 policy.log로 생성)
            **overrides: 런타임 오버라이드 값 (source__path, save__directory 등)
        
        Example:
            >>> # YAML 파일에서 로드
            >>> loader = ImageLoader("configs/image.yaml")
            
            >>> # dict로 직접 설정
            >>> loader = ImageLoader({"source": {"path": "test.jpg"}})
            
            >>> # 런타임 오버라이드 (KeyPath 형식)
            >>> loader = ImageLoader("config.yaml", source__path="image.jpg", save__directory="output")
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
        
        self.log.info(f"ImageLoader initialized: source={self.policy.source.path}")
    
    def _load_config(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None],
        *,
        policy_overrides: Optional[Dict[str, Any]] = None,
        **overrides: Any
    ) -> ImageLoaderPolicy:
        """ImageLoaderPolicy 로드 (BaseWebDriver 패턴 준수)
        
        Args:
            cfg_like: 설정 소스 (ImageLoaderPolicy, YAML 경로, dict 등)
            policy_overrides: ConfigPolicy 필드 개별 오버라이드 (merge_mode, yaml.source_paths 등)
            **overrides: 런타임 오버라이드 (source__path, save__directory 등)
                - KeyPath 형식: source__path → source.path
        
        Returns:
            로드된 ImageLoaderPolicy 인스턴스
        """
        if cfg_like is None:
            # ✅ CRITICAL FIX: ConfigLoader의 역할 명확화
            # - cfg_like: 데이터 파일 (None이면 policy.yaml.source_paths만 사용)
            # - policy_overrides["config_loader_path"]: 정책 파일
            # 
            # config_loader_image.yaml을 정책으로 사용하되, cfg_like는 None 유지
            # → ConfigLoader가 config_loader_image.yaml에 정의된 yaml.source_paths를 따라
            #    image.yaml의 "image" 섹션을 자동으로 로드
            
            if policy_overrides is None:
                policy_overrides = {}
            
            # ConfigLoader 정책 파일 지정
            policy_overrides.setdefault("config_loader_path",
                str(Path(__file__).parent.parent / "configs" / "config_loader_image.yaml"))
        
        return ConfigLoader.load(
            cfg_like,
            model=ImageLoaderPolicy,
            policy_overrides=policy_overrides,
            **overrides
        )
    
    # ==========================================================================
    # Core Methods
    # ==========================================================================
    
    def run(
        self,
        source_override: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """이미지 로드, 처리 및 저장.
        
        Args:
            source_override: 소스 경로 오버라이드 (policy.source.path 대신 사용)
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "image": PIL.Image.Image,
                "original_path": Path,
                "saved_path": Optional[Path],
                "meta_path": Optional[Path],
                "original_size": Tuple[int, int],
                "processed_size": Optional[Tuple[int, int]],
                "error": Optional[str]
            }
        """
        result = {
            "success": False,
            "image": None,
            "original_path": None,
            "saved_path": None,
            "meta_path": None,
            "original_size": None,
            "processed_size": None,
            "error": None,
        }
        
        try:
            # 1. 소스 경로 결정
            source_path = source_override or self.policy.source.path
            source_path = resolve(source_path)
            result["original_path"] = source_path
            
            self.log.info(f"Loading image: {source_path}")
            
            # 2. 이미지 로드
            from PIL import Image, ImageFilter
            
            if not source_path.exists() and self.policy.source.must_exist:
                raise FileNotFoundError(f"Image not found: {source_path}")
            
            img = Image.open(source_path)
            
            # Original 정보 저장 (변환 전)
            original_mode = img.mode
            original_format = img.format
            
            # EXIF orientation 처리
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
            
            # convert_mode 처리
            if self.policy.source.convert_mode:
                img = img.convert(self.policy.source.convert_mode)
            
            result["original_size"] = img.size
            result["original_mode"] = original_mode
            result["original_format"] = original_format
            
            self.log.info(f"Loaded image: {img.size} {img.mode}")
            
            # 3. 이미지 처리
            processed_img = img
            if self.policy.process.resize_to:
                self.log.info(f"Resizing to: {self.policy.process.resize_to}")
                processed_img = processed_img.resize(
                    self.policy.process.resize_to,
                    Image.Resampling.LANCZOS,
                )
            
            if self.policy.process.blur_radius:
                self.log.info(f"Applying blur: radius={self.policy.process.blur_radius}")
                processed_img = processed_img.filter(
                    ImageFilter.GaussianBlur(radius=self.policy.process.blur_radius)
                )
            
            if self.policy.process.convert_mode:
                self.log.info(f"Converting to mode: {self.policy.process.convert_mode}")
                processed_img = processed_img.convert(self.policy.process.convert_mode)
            
            result["processed_size"] = processed_img.size
            
            # 4. 이미지 저장
            if self.policy.save.save_copy:
                self.log.info("Saving processed image...")
                saved_path = self.writer.save_image(processed_img, source_path)
                result["saved_path"] = saved_path
                self.log.success(f"Saved to: {saved_path}")
            
            # 5. 메타데이터 저장
            meta_data = {
                "original_path": str(source_path),
                "original_size": result["original_size"],
                "original_mode": result.get("original_mode"),
                "original_format": result.get("original_format"),
                "processed_size": result["processed_size"],
                "saved_path": str(result["saved_path"]) if result["saved_path"] else None,
                "processing": {
                    "resize_to": self.policy.process.resize_to,
                    "blur_radius": self.policy.process.blur_radius,
                    "convert_mode": self.policy.process.convert_mode,
                }
            }
            
            # Meta 파일명에도 suffix_counter 반영 (이미지와 동일한 번호)
            meta_source_path = source_path
            if result.get("saved_path"):
                # 저장된 이미지 파일명 기준으로 메타 파일명 생성
                meta_source_path = Path(result["saved_path"]).with_suffix('.jpg')  # 확장자는 임시
            
            meta_path = self.writer.save_meta(meta_data, meta_source_path)
            if meta_path:
                result["meta_path"] = meta_path
                self.log.success(f"Metadata saved to: {meta_path}")
            
            # 6. Image 객체 반환에 추가
            result["image"] = processed_img
            result["success"] = True
            self.log.success("ImageLoader completed successfully")
            
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
        return f"ImageLoader(source={self.policy.source.path})"
