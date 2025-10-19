# -*- coding: utf-8 -*-
"""ImageLoad - Core image processing logic (Adapter).

translate_utils의 Translate adapter 패턴을 정확히 따릅니다:
- source 관련 코드 완전 제거
- Image 객체만 받아서 처리
- EntryPoint(ImageLoader)에서 파일 로딩

책임:
1. PIL Image 객체 처리 (리사이즈, 블러, 모드 변환)
2. process(image) API 제공

EntryPoint(ImageLoader)와의 역할 분담:
- Adapter (이 파일): 순수 이미지 처리 로직, Image 객체 처리
- EntryPoint: YAML 로딩, 파일 I/O (로드/저장), 메타데이터 저장
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from PIL import Image, ImageFilter

from logs_utils import LogManager

from ..core.policy import ImageLoadPolicy


class ImageLoad:
    """Core image processing service (Adapter).
    
    translate_utils.Translate와 동일한 패턴:
    - source를 받지 않음
    - Image 객체를 받아서 처리
    - EntryPoint에서 파일 로딩 후 전달
    
    Attributes:
        policy: ImageLoadPolicy 설정 (source 없음)
        log: loguru logger 인스턴스
    """
    
    def __init__(
        self,
        cfg_like: Union[Path, str, dict, ImageLoadPolicy, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize ImageLoad with policy.
        
        Args:
            cfg_like: ImageLoadPolicy, YAML 경로, dict, 또는 None
            log_manager: 외부 LogManager (선택사항)
            **overrides: 런타임 오버라이드
        
        Example:
            >>> # YAML에서 로드
            >>> img_load = ImageLoad("configs/image_load.yaml")
            
            >>> # dict로 직접 설정
            >>> img_load = ImageLoad({"process": {"resize_to": [800, 600]}})
            
            >>> # Policy 인스턴스로
            >>> policy = ImageLoadPolicy(...)
            >>> img_load = ImageLoad(policy)
        """
        # Load policy
        self.policy = self._load_config(cfg_like, **overrides)
        
        # LogManager 생성 (우선순위: 외부 log_manager > policy.log > 기본)
        if log_manager:
            self.log = log_manager.logger
        elif self.policy.log:
            self.log = LogManager(self.policy.log).logger
        else:
            self.log = LogManager({"enabled": False}).logger
        
        self.log.debug("ImageLoad adapter initialized")
    
    # ==========================================================================
    # Config Loading (ConfigLikeLoader pattern)
    # ==========================================================================
    
    @staticmethod
    def _load_config(cfg_like, **overrides) -> ImageLoadPolicy:
        """Load ImageLoadPolicy from various sources.
        
        Args:
            cfg_like: ImageLoadPolicy instance, YAML path, dict, or None
            **overrides: Runtime overrides
        
        Returns:
            ImageLoadPolicy instance (source 없음)
        """
        from cfg_utils.services.config_like_loader import ConfigLikeLoader
        
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=ImageLoadPolicy,
            caller_file=__file__,
            default_config_filename="image.yaml",
            **overrides
        )
    
    # ==========================================================================
    # Main API (translate_utils.Translate.run() 패턴)
    # ==========================================================================
    
    def process(
        self,
        image: Image.Image
    ) -> Image.Image:
        """이미지 처리 (순수 로직).
        
        translate_utils의 Translate.run(texts)와 동일한 패턴:
        - Image 객체를 받아서 처리
        - 처리된 Image 객체 반환
        - 파일 I/O는 EntryPoint에서 처리
        
        처리 순서:
        1. 리사이즈 (resize_to)
        2. 블러 (blur_radius)
        3. 모드 변환 (convert_mode)
        
        Args:
            image: PIL Image 객체
        
        Returns:
            처리된 PIL Image 객체
        
        Example:
            >>> img_load = ImageLoad(policy)
            >>> img = Image.open("test.jpg")
            >>> processed_img = img_load.process(img)
        """
        self.log.debug(f"Processing image: {image.size} {image.mode}")
        
        processed_img = image
        
        # 1. 리사이즈
        if self.policy.process.resize_to:
            target_size = self.policy.process.resize_to
            self.log.debug(f"Resizing: {image.size} -> {target_size}")
            processed_img = processed_img.resize(
                target_size,
                Image.Resampling.LANCZOS,
            )
        
        # 2. 블러
        if self.policy.process.blur_radius:
            radius = self.policy.process.blur_radius
            self.log.debug(f"Applying blur: radius={radius}")
            processed_img = processed_img.filter(
                ImageFilter.GaussianBlur(radius=radius)
            )
        
        # 3. 모드 변환
        if self.policy.process.convert_mode:
            mode = self.policy.process.convert_mode
            self.log.debug(f"Converting mode: {processed_img.mode} -> {mode}")
            processed_img = processed_img.convert(mode)
        
        self.log.success(f"Processing completed: {processed_img.size} {processed_img.mode}")
        
        return processed_img
    
    def __repr__(self) -> str:
        return f"ImageLoad(process={self.policy.process})"
