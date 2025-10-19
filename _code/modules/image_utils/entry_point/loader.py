# -*- coding: utf-8 -*-
"""ImageLoader - Image loading entry point (Translator pattern).

책임:
1. source에서 이미지 파일 로드
2. ImageLoad adapter에 위임하여 실제 처리
3. 결과 저장 (정책에 따라)

translate_utils의 Translator와 동일한 패턴:
- Policy: ImageLoaderPolicy (source + image_load)
- source에서 데이터 로드
- adapter.run(data) 호출
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from PIL import Image, ImageOps

from logs_utils import LogManager
from path_utils import resolve

from ..core.policy import ImageLoaderPolicy
from ..adapter.load import ImageLoad


class ImageLoader:
    """이미지 로드 EntryPoint (Translator pattern).
    
    translate_utils의 Translator와 동일한 구조:
    - source에서 이미지 파일 로드
    - ImageLoad adapter에 위임하여 처리
    - 결과 저장
    
    Attributes:
        policy: ImageLoaderPolicy 설정 (source + image_load)
        image_load: ImageLoad 인스턴스
        log: loguru logger
    """
    
    def __init__(
        self,
        cfg_like: Union[Path, str, dict, ImageLoaderPolicy, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize ImageLoader.
        
        Args:
            cfg_like: ImageLoaderPolicy, YAML 경로, dict, 또는 None
            log_manager: 외부 LogManager (선택사항)
            **overrides: 런타임 오버라이드 (source__path 등)
        
        Example:
            >>> loader = ImageLoader("configs/image.yaml")
            >>> loader = ImageLoader({"source": {"path": "test.jpg"}})
            >>> loader = ImageLoader("config.yaml", source__path="test.jpg")
        """
        # Load policy
        self.policy = self._load_config(cfg_like, **overrides)
        
        # ImageLoad adapter 생성 (image_load policy만 전달)
        self.image_load = ImageLoad(
            cfg_like=self.policy.image_load,
            log_manager=log_manager
        )
        
        # Log는 adapter의 log 사용
        self.log = self.image_load.log
        
        self.log.info(f"ImageLoader initialized: source={self.policy.source.path}")
    
    # ==========================================================================
    # Config Loading (ConfigLikeLoader pattern)
    # ==========================================================================
    
    def _load_config(self, cfg_like, **overrides) -> ImageLoaderPolicy:
        """Load ImageLoaderPolicy from various sources.
        
        Args:
            cfg_like: ImageLoaderPolicy instance, YAML path, dict, or None
            **overrides: Runtime overrides
        
        Returns:
            ImageLoaderPolicy instance
        """
        from cfg_utils.services import ConfigLikeLoader
        
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=ImageLoaderPolicy,
            caller_file=__file__,
            default_config_filename="image.yaml",
            **overrides
        )  # type: ignore
    
    # ==========================================================================
    # Main Execution (Translator pattern)
    # ==========================================================================
    
    def run(
        self,
        source_override: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """이미지 로드 및 처리 (Translator.run() pattern).
        
        1. source에서 이미지 파일 로드
        2. ImageLoad adapter의 run()에 Image 객체 전달
        3. 결과 반환
        
        Args:
            source_override: 소스 경로 오버라이드 (None이면 policy.source.path 사용)
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "image": PIL.Image.Image,
                "original_size": Tuple[int, int],
                "processed_size": Tuple[int, int],
                "processing": Dict[str, Any],
                "source_path": Path,
                "error": Optional[str]
            }
        
        Example:
            >>> loader = ImageLoader("config.yaml")
            >>> result = loader.run()
            >>> if result["success"]:
            ...     img = result["image"]
        """
        self.log.info("=" * 70)
        self.log.info("[ImageLoader] Starting image processing")
        
        result = {
            "success": False,
            "image": None,
            "original_size": None,
            "processed_size": None,
            "processing": {},
            "source_path": None,
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
            
            # 4. ImageLoad adapter에 위임 (Image 객체 전달)
            adapter_result = self.image_load.run(img)
            
            # 5. 결과 통합
            result.update(adapter_result)
            
            if result["success"]:
                self.log.success("[ImageLoader] Completed successfully")
            else:
                self.log.error(f"[ImageLoader] Adapter failed: {result.get('error')}")
            
        except FileNotFoundError as e:
            result["error"] = f"File not found: {e}"
            self.log.error(result["error"])
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            self.log.error(result["error"])
        
        self.log.info("=" * 70)
        
        return result
    
    def __repr__(self) -> str:
        return f"ImageLoader(source={self.policy.source.path})"
