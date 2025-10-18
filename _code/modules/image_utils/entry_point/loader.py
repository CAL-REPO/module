# -*- coding: utf-8 -*-
"""ImageLoader - Image loading, copying, and processing entry point.

책임:
1. 이미지 로드 및 복사
2. 리사이즈, 블러 등 기본 처리
3. 메타데이터 저장
4. cfg_loader/logs_utils 통합
"""


from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Dict

from PIL import Image
from pydantic import BaseModel, ValidationError

from cfg_utils import ConfigPolicy, BaseServiceLoader
from logs_utils import LogManager
from path_utils import resolve

from ..core.policy import ImageLoaderPolicy
from ..services.io import ImageWriter


class ImageLoader(BaseServiceLoader[ImageLoaderPolicy]):
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
        policy: Optional[ConfigPolicy] = None,
        config_loader_path: Optional[Union[str, Path]] = None,
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
            policy: ConfigPolicy 인스턴스
            config_loader_path: config_loader_image.yaml 경로 override (선택)
            log: 외부 LogManager (없으면 policy.log로 생성)
            **overrides: 런타임 오버라이드 값 (source__path, save__directory 등)
        
        Example:
            >>> # YAML 파일에서 로드
            >>> loader = ImageLoader("configs/image.yaml")
            
            >>> # dict로 직접 설정
            >>> loader = ImageLoader({"source": {"path": "test.jpg"}})
            
            >>> # config_loader_path override
            >>> loader = ImageLoader(config_loader_path="./custom_config_loader.yaml")
            
            >>> # 런타임 오버라이드 (KeyPath 형식)
            >>> loader = ImageLoader("config.yaml", source__path="image.jpg", save__directory="output")
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
        
        self.log.info(f"ImageLoader initialized: source={self.policy.source.path}")
    
    # ==========================================================================
    # BaseServiceLoader Abstract Methods Implementation
    # ==========================================================================
    
    def _get_policy_model(self) -> type[ImageLoaderPolicy]:
        """Policy 모델 클래스 반환."""
        return ImageLoaderPolicy
    
    def _get_config_loader_path(self) -> Path:
        """config_loader_image.yaml 경로 반환."""
        return Path(__file__).parent.parent / "configs" / "config_loader_image.yaml"
    
    def _get_default_section(self) -> str:
        """기본 section 이름: 'image'."""
        return "image"
    
    def _get_config_path(self) -> Path:
        """마지막 안전 장치용 기본 설정 파일: image.yaml."""
        return Path(__file__).parent.parent / "configs" / "image.yaml"
    
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
    ) -> Dict[str, Any]:
        """이미지 로드, 처리 및 저장.
        
        정책에 따라:
        - save.save_copy=True: 이미지 복사본 저장
        - meta.save_meta=True: 메타데이터 JSON 저장
        
        Args:
            source_override: 소스 경로 오버라이드 (policy.source.path 대신 사용)
        
        Returns:
            결과 딕셔너리 (ImageTextRecognizer과 일관성 유지):
            {
                "success": bool,
                "image": PIL.Image.Image,  # 처리된 단일 이미지
                "metadata": Dict[str, Any],  # 단일 메타데이터
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
            "image": None,  # 단일 이미지 객체 (ImageTextRecognizer과 일관성)
            "metadata": None,  # 단일 메타데이터
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
            
            # 4. 메타데이터 준비
            meta_data = {
                "original_path": str(source_path),
                "original_size": result["original_size"],
                "original_mode": result.get("original_mode"),
                "original_format": result.get("original_format"),
                "processed_size": result["processed_size"],
                "saved_path": None,  # 저장 후 업데이트
                "processing": {
                    "resize_to": self.policy.process.resize_to,
                    "blur_radius": self.policy.process.blur_radius,
                    "convert_mode": self.policy.process.convert_mode,
                }
            }
            
            # 5. 정책에 따라 이미지 저장 (save_copy=True일 때만)
            if self.policy.save.save_copy:
                self.log.info("Saving processed image...")
                saved_path = self.writer.save_image(processed_img, source_path)
                result["saved_path"] = saved_path
                meta_data["saved_path"] = str(saved_path)
                self.log.success(f"Saved to: {saved_path}")
            else:
                self.log.info("Image save skipped (save_copy=False)")
            
            # 6. 정책에 따라 메타데이터 저장 (save_meta=True일 때만)
            if self.policy.meta.save_meta:
                # 메타 파일명: 저장된 이미지 기준 or 원본 이미지 기준
                meta_source_path = result.get("saved_path") or source_path
                meta_path = self.writer.save_meta(meta_data, meta_source_path)
                if meta_path:
                    result["meta_path"] = meta_path
                    self.log.success(f"Metadata saved to: {meta_path}")
            else:
                self.log.info("Metadata save skipped (save_meta=False)")
            
            # 7. 결과 저장 (단일 값, ImageTextRecognizer과 일관성)
            result["image"] = processed_img
            result["metadata"] = meta_data
            
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
