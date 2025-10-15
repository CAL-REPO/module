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
        """Initialize ImageLoader with flexible config input.
        
        ConfigLoader와 동일한 인자 패턴:
        - BaseModel (ImageLoaderPolicy) 직접 전달
        - YAML 파일 경로 (str/Path)
        - Dictionary
        - None (기본 설정 파일 사용)
        
        Args:
            cfg_like: Policy 인스턴스, YAML 경로, dict, 또는 None
            policy_overrides: ConfigPolicy 필드 개별 오버라이드
            log: 외부 LogManager (없으면 policy.log로 생성)
            **overrides: 런타임 데이터 오버라이드
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
        """설정 로드 (간소화 버전)
        
        Args:
            cfg_like: 설정 소스
            policy_overrides: ConfigPolicy 필드 개별 오버라이드
            **overrides: 런타임 데이터 오버라이드
        
        Returns:
            ImageLoaderPolicy 인스턴스
        """
        # cfg_like가 None이면 기본 파일 경로 + 섹션을 policy_overrides로 지정
        if cfg_like is None:
            default_path = Path(__file__).parent.parent / "configs" / "image.yaml"
            if policy_overrides is None:
                policy_overrides = {}
            
            # ImageLoader 전용 ConfigLoader 정책 파일 지정
            policy_overrides.setdefault("config_loader_path", 
                str(Path(__file__).parent.parent / "configs" / "config_loader_image.yaml")
            )
            
            # yaml.source_paths에 dict 형태로 전달 (Pydantic이 자동 변환)
            policy_overrides.setdefault("yaml.source_paths", {
                "path": str(default_path),
                "section": "image"
            })
        
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
            
            # EXIF orientation 처리
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
            
            # convert_mode 처리
            if self.policy.source.convert_mode:
                img = img.convert(self.policy.source.convert_mode)
            
            result["original_size"] = img.size
            
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
                "processed_size": result["processed_size"],
                "saved_path": str(result["saved_path"]) if result["saved_path"] else None,
                "processing": {
                    "resize_to": self.policy.process.resize_to,
                    "blur_radius": self.policy.process.blur_radius,
                    "convert_mode": self.policy.process.convert_mode,
                }
            }
            
            meta_path = self.writer.save_meta(meta_data, source_path)
            if meta_path:
                result["meta_path"] = meta_path
                self.log.success(f"Metadata saved to: {meta_path}")
            
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
