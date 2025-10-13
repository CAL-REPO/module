# -*- coding: utf-8 -*-
# pillow_utils/processor.py
"""
모듈 설명: 이미지 후처리/전처리 유틸리티 (Logger + 정책 연동)
"""
from __future__ import annotations
from typing import Tuple
from PIL import Image, ImageFilter
from log_utils import LogManager
from .policy import ImagePolicy

class ImageProcessor:
    """이미지 전처리/후처리 기능 클래스
    - 리사이즈, 블러 등의 Pillow 기반 필터 지원
    - 로그 기록 및 정책 연동
    """

    def __init__(self, policy: ImagePolicy):
        self.policy = policy
        logger_args = self.policy.get_logger_args()
        self.logger = LogManager("pillow_processor", **logger_args).setup()

    def resize(self, img: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
        """이미지를 지정된 크기로 리사이즈"""
        w, h = img.size
        new_img = img.resize(max_size, Image.LANCZOS)
        self.logger.info(f"이미지 리사이즈: {w}x{h} → {max_size[0]}x{max_size[1]}")
        return new_img

    def blur(self, img: Image.Image, radius: int = 2) -> Image.Image:
        """Gaussian Blur 필터 적용"""
        self.logger.info(f"이미지 블러 적용: radius={radius}")
        return img.filter(ImageFilter.GaussianBlur(radius))

    def convert_mode(self, img: Image.Image, mode: str) -> Image.Image:
        """이미지 색상 모드 변환 (RGB, RGBA, L 등)"""
        old_mode = img.mode
        new_img = img.convert(mode)
        self.logger.info(f"이미지 모드 변환: {old_mode} → {mode}")
        return new_img

    def process_pipeline(self, img: Image.Image, resize_to: Tuple[int, int] | None = None, blur_radius: int | None = None) -> Image.Image:
        """리사이즈 및 블러를 순차적으로 수행하는 파이프라인"""
        self.logger.info("[ImageProcessor] 파이프라인 시작")
        processed = img

        if resize_to:
            processed = self.resize(processed, resize_to)
        if blur_radius:
            processed = self.blur(processed, blur_radius)

        self.logger.info("[ImageProcessor] 파이프라인 완료")
        return processed