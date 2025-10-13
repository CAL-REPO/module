# -*- coding: utf-8 -*-
# pillow_utils/overlay_base.py
"""
모듈 설명: 이미지 오버레이 처리 클래스 (OverlayPolicy 기반)
- poly → bbox 변환
- resize_scale 역배율 적용
- 텍스트 위치, 패딩, 정렬, 투명도 반영
"""
from __future__ import annotations
from typing import Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from log_utils import LogManager
from .policy import OverlayPolicy

class ImageOverlayer:
    """정책 기반 이미지 오버레이 클래스"""

    def __init__(self, policy: OverlayPolicy):
        self.policy = policy
        logger_args = {"log_file": None, "policy": self.policy.logger}
        if self.policy.log_dir:
            log_file = self.policy.log_dir / "pillow_overlay.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            logger_args["log_file"] = log_file
        self.logger = LogManager("pillow_overlayer", **logger_args).setup()

    # ----------------------------
    # 좌표 보정 및 bbox 계산
    # ----------------------------
    def _apply_resize_scale(self, points: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """resize_scale 역배율 적용"""
        if not self.policy.resize_scale:
            return points
        sx, sy = self.policy.resize_scale
        if not (sx and sy):
            return points
        return [(int(x / sx), int(y / sy)) for (x, y) in points]

    def _poly_to_bbox(self, poly: list[tuple[int, int]]) -> tuple[int, int, int, int]:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        pad = self.policy.padding or 0
        return x1 + pad, y1 + pad, x2 - pad, y2 - pad

    # ----------------------------
    # 텍스트 렌더링
    # ----------------------------
    def draw_text(self, img: Image.Image, text: str) -> Image.Image:
        if not self.policy.poly_points:
            self.logger.warning("poly_points가 지정되지 않아 오버레이를 수행할 수 없습니다.")
            return img

        poly = self._apply_resize_scale(self.policy.poly_points)
        bbox = self._poly_to_bbox(poly)
        x1, y1, x2, y2 = bbox

        draw = ImageDraw.Draw(img, "RGBA")

        # 배경 마스크 (optional)
        if self.policy.background_color and self.policy.opacity:
            bg = Image.new("RGBA", (x2 - x1, y2 - y1), self.policy.background_color + f"{int(self.policy.opacity * 255):02x}")
            img.paste(bg, (x1, y1), bg)

        # 폰트 설정
        if self.policy.font_path:
            try:
                font = ImageFont.truetype(str(self.policy.font_path), self.policy.font_size or 24)
            except Exception as e:
                self.logger.warning(f"폰트 로드 실패, 기본 폰트 사용: {e}")
                font = ImageFont.load_default()
        else:
            font = ImageFont.load_default()

        # 텍스트 위치 계산 (center anchor 기본)
        tw, th = draw.textsize(text, font=font)
        tx, ty = (x1 + (x2 - x1 - tw) / 2, y1 + (y2 - y1 - th) / 2)

        # 텍스트 그리기
        draw.text(
            (tx, ty),
            text,
            font=font,
            fill=self.policy.font_color or "black",
            align=self.policy.align or "center",
            anchor=self.policy.anchor or "mm"
        )

        self.logger.info(f"텍스트 오버레이 완료: '{text}' 영역=({x1},{y1},{x2},{y2})")
        return img
