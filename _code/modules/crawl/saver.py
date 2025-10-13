# -*- coding: utf-8 -*-
# crawl/saver.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from log_utils import LogManager
from requests import Session

# 정책/유틸
from .policy import SavePolicy, DownloadPolicy
from .fetcher import ResourceFetcher
from unify_utils import value_normalizer
from pillow_utils import (
    ImagePolicy,
    ImageFilePolicy,
    ImageSavePolicy,
    ImageProcessor,
    ImageSaver,
)

# ---------------------------
# Helpers
# ---------------------------
_URL_RE = re.compile(r"^https?://", re.I)
def is_url(s: Any) -> bool:
    return bool(isinstance(s, str) and _URL_RE.match(s))

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

# ---------------------------
# Image Save Worker
# ---------------------------
class ImageSaveWorker:
    """이미지 저장 전용(바이트→디코드→전처리→저장)"""
    def __init__(self, policy: SavePolicy, logger: Optional[LogManager] = None):
        if not policy.image:
            raise ValueError("ImageSaveWorker requires SavePolicy.image")
        self.cfg = policy.image
        self.log = logger or LogManager("image-saver").setup()

        # Pillow 정책 구성(기존 유틸 재사용)
        self.image_policy = ImagePolicy(
            file=ImageFilePolicy(path=ensure_dir(self.cfg.save_dir)),
            save=ImageSavePolicy(
                save_dir=self.cfg.save_dir,
                format=self.cfg.format,
                quality=self.cfg.quality,
                exif=self.cfg.exif,
            ),
        )
        self.processor = ImageProcessor(self.image_policy)
        self.saver = ImageSaver(self.image_policy)

    def save_bytes(self, data: bytes, *, section: str, key: Optional[str], idx: int) -> Path:
        # 1) bytes → Pillow.Image 디코딩
        img = self.processor.load_from_bytes(data) if hasattr(self.processor, "load_from_bytes") \
              else self._bytes_to_image(data)

        # 2) 전처리(Pillow 파이프라인)
        processed = self.processor.process_pipeline(img)

        # 3) 파일명 템플릿 적용
        name = self.cfg.name_template.format(section=section, key=(key or idx), idx=idx)

        # 4) 저장
        out_path = self.saver.save_image(processed, name=name)
        self.log.info(f"Image saved: {out_path}")
        return out_path

    # Pillow 유틸에 load_from_bytes가 없다면 최소 구현
    @staticmethod
    def _bytes_to_image(data: bytes):
        from io import BytesIO
        from PIL import Image
        return Image.open(BytesIO(data))

# ---------------------------
# Text Save Worker
# ---------------------------
class TextSaveWorker:
    """텍스트 저장 전용(단일/리스트/딕트 그대로 출력)"""
    def __init__(self, policy: SavePolicy, logger: Optional[LogManager] = None):
        if not policy.text:
            raise ValueError("TextSaveWorker requires SavePolicy.text")
        self.cfg = policy.text
        self.log = logger or LogManager("text-saver").setup()
        ensure_dir(self.cfg.save_dir)

    def save_texts(self, section: str, pairs: List[Tuple[Optional[str], Any]]) -> Path:
        # 출력 파일 결정
        fname = self.cfg.filename_template.format(section=section)
        path = self.cfg.save_dir / fname

        # 원본 구조를 그대로 덤프(간단 txt; 필요시 yaml/json로 확장)
        lines: List[str] = []
        for k, v in pairs:
            if isinstance(v, (dict, list, tuple)):
                lines.append(f"{k}: {v}")
            else:
                lines.append(f"{k}: {v}")

        text = "\n".join(lines)
        if self.cfg.mode == "append" and path.exists():
            cur = path.read_text(encoding=self.cfg.encoding)
            path.write_text(cur + ("\n" if cur else "") + text, encoding=self.cfg.encoding)
        else:
            path.write_text(text, encoding=self.cfg.encoding)

        self.log.info(f"Text saved: {path}")
        return path

# ---------------------------
# Orchestrator
# ---------------------------
class CrawlSaver:
    """grouped_pairs 단위 분기 오케스트레이터
    grouped_pairs: Dict[str|None, List[Tuple[str|None, Any]]]
    """
    def __init__(
        self,
        download: DownloadPolicy,
        save: SavePolicy,
        logger: Optional[LogManager] = None,
    ):
        self.download = download
        self.save = save
        self.log = logger or LogManager("crawl-saver").setup()

        self.fetcher = ResourceFetcher(download, logger=self.log)
        self.vnorm = value_normalizer()

        self.img_worker = ImageSaveWorker(save, logger=self.log) if save.image else None
        self.txt_worker = TextSaveWorker(save, logger=self.log) if save.text else None

    def save(self, session: Optional[Session], grouped_pairs: Dict[str | None, List[Tuple[str | None, Any]]]):
        saved_images: List[Path] = []
        saved_texts: List[Path] = []

        for section, pairs in grouped_pairs.items():
            section_name = str(section or "default")

            # 1) 이미지/텍스트 분리
            image_pairs: List[Tuple[Optional[str], str]] = []
            text_pairs: List[Tuple[Optional[str], Any]] = []
            for k, v in pairs:
                if is_url(v):
                    image_pairs.append((k, str(v)))
                else:
                    text_pairs.append((k, v))

            # 2) 이미지 저장
            if image_pairs and self.img_worker:
                for idx, (k, url) in enumerate(image_pairs, start=1):
                    try:
                        buf = self.fetcher.fetch_bytes(url, session=session)
                        out = self.img_worker.save_bytes(buf, section=section_name, key=k, idx=idx)
                        saved_images.append(out)
                    except Exception as e:
                        self.log.warning(f"Image save failed: {url} - {e}")

            # 3) 텍스트 저장
            if text_pairs and self.txt_worker:
                try:
                    out = self.txt_worker.save_texts(section_name, text_pairs)
                    saved_texts.append(out)
                except Exception as e:
                    self.log.warning(f"Text save failed: section={section_name} - {e}")

        self.log.info(f"Saved {len(saved_images)} images, {len(saved_texts)} texts.")
        return {"images": saved_images, "texts": saved_texts}
