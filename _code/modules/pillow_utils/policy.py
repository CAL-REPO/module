# -*- coding: utf-8 -*-
# pillow_utils/policy.py
"""
모듈 설명: 이미지 입출력 및 오버레이 정책 정의 (Pydantic 기반)
- OverlayPolicy: overlay.py 기반 폴리곤, bbox, 색상, 폰트, 투명도 등 통합 정책
- ImagePolicy: 이미지 로드/저장 정책
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional, Literal, Tuple, List
from pydantic import BaseModel, Field
from log_utils import LogPolicy

# Pillow 지원 확장자 세트 및 포맷 매핑
_IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp",
    ".heic", ".heif", ".avif",
    ".JPG", ".JPEG", ".PNG", ".BMP", ".GIF", ".TIF", ".TIFF", ".WEBP",
    ".HEIC", ".HEIF", ".AVIF",
}

_IMAGE_EXTS_MAP = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".jpe": "JPEG",
    ".jfif": "JPEG",
    ".png": "PNG",
    ".bmp": "BMP",
    ".dib": "BMP",
    ".gif": "GIF",
    ".tif": "TIFF",
    ".tiff": "TIFF",
    ".webp": "WEBP",
    ".heic": "HEIC",
    ".heif": "HEIF",
    ".avif": "AVIF",
    ".ico": "ICO",
    ".eps": "EPS",
    ".pdf": "PDF"
}


# ---------------------------
# 오버레이 정책 정의
# ---------------------------
class OverlayPolicy(BaseModel):
    """기존 overlay.py에서 사용된 시각/위치/텍스트 변수들을 정책화"""

    # 폰트 및 텍스트 관련
    font_path: Optional[Path] = None  # fso_utils에서 시스템 기본 폰트 제공 예정
    font_size: Optional[int] = None  # Auto bbox 기반 크기 결정
    font_color: Optional[str] = "black"  # 기본: Black
    background_color: Optional[str] = "white"  # 기본: White / 마스킹 시 텍스트 가시성 확보용
    line_spacing: Optional[float] = 3  # 줄 간격
    wrap_width: Optional[int] = None  #  기본: Auto bbox 넓이 기반 결정 / 텍스트 줄바꿈 기준 너비 
    align: Optional[Literal["left", "center", "right"]] = "center"  # 정렬 방향

    # 투명도 / 그림자 효과
    opacity: Optional[float] = 0  # 텍스트 또는 마스크 투명도 (0~1)
    mask_opacity: Optional[float] = 0.5  # 배경 마스크 투명도
    text_opacity: Optional[float] = 0  # 텍스트 자체 투명도
    shadow: Optional[bool] = None  # 그림자 표시 여부
    shadow_offset: Optional[Tuple[int, int]] = None  # 그림자 오프셋

    # 위치 및 배치
    position_mode: Optional[Literal["absolute", "relative"]] = None  # 절대/비율 위치
    poly_points: Optional[List[Tuple[int, int]]] = None  # polygon 좌표
    bbox: Optional[Tuple[int, int, int, int]] = None  # bounding box
    rotation: Optional[float] = None  # 텍스트 회전 각도
    anchor: Optional[str] = None  # Pillow 기준점 (center, lt 등)
    padding: Optional[int] = None  # 텍스트 패딩 (픽셀)

    # 외곽선 / 테두리
    outline_color: Optional[str] = None
    outline_width: Optional[int] = None

    # 로깅 정책
    log_dir: Optional[Path] = None # 정책에 log_dir 추가 있으면 logging 진행 없으면 os 다운로드 폴더의 logs/overlay ensure. 파일명은 overlay_날짜시간 -> 재시도 시 최근날짜파일만 확인
    logger: LogPolicy = Field(default_factory=LogPolicy, description="로깅 정책")

# ---------------------------
# 이미지 로드/저장 정책 정의
# ---------------------------
class ImageFilePolicy(BaseModel):
    path: Path
    must_exist: bool = Field(False, description="이미지 파일 존재 여부 확인 (기본 False)")
    convert_mode: Optional[Literal["RGB", "RGBA", "L"]] = "RGB"

class ImageSavePolicy(BaseModel):
    enabled: bool = Field(True, description="이미지 저장 여부")
    directory: Optional[Path] = Field(None, description="저장 디렉터리 (None이면 원본 폴더)")
    suffix: str = Field("_copy", description="저장 파일명 접미사")
    format: Optional[str] = Field(None, description="저장 포맷 (기본값: 원본 포맷)")
    quality: int = Field(95, description="저장 품질 (JPEG/WEBP용)")

class ImageMetaPolicy(BaseModel):
    enabled: bool = Field(False, description="메타데이터 JSON 저장 여부")
    directory: Optional[Path] = Field(None, description="메타데이터 저장 폴더")
    filename: str = Field("meta_image.json", description="메타파일 이름")
    include_exif: bool = Field(True, description="EXIF 정보 포함 여부")

class ImagePolicy(BaseModel):
    file: ImageFilePolicy
    save: ImageSavePolicy = ImageSavePolicy()
    meta: ImageMetaPolicy = ImageMetaPolicy()
    log_dir: Optional[Path] = Field(None, description="로그 저장 경로 (없으면 파일 저장 안 함)")
    logger: LogPolicy = Field(default_factory=LogPolicy, description="로그 정책")
    debug: bool = Field(False, description="디버그 모드")

    def get_logger_args(self) -> dict:
        if self.log_dir:
            log_file = self.log_dir / "pillow_utils.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            return {"log_file": log_file, "policy": self.logger}
        return {"log_file": None, "policy": self.logger}
