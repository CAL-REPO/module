# -*- coding: utf-8 -*-
# pillow_utils/session.py
"""
모듈 설명: 로드→저장 전체 워크플로우 관리 클래스 (FSOOpsPolicy + Logger 연동)
"""
from __future__ import annotations
import time
from typing import Optional
from log_utils import LogManager
from .policy import ImagePolicy
from .model import ImageState
from .loader import ImageLoader
from .saver import ImageSaver

class ImageSession:
    """이미지 로드→저장 전체 세션 관리 클래스.
    - 각 단계별 로깅 수행
    - 처리 시간 및 결과 요약 기록
    """

    def __init__(self, policy: ImagePolicy):
        self.policy = policy
        logger_args = self.policy.get_logger_args()
        self.logger = LogManager("pillow_session", **logger_args).setup()
        self.loader = ImageLoader(policy)
        self.saver = ImageSaver(policy)
        self.state: Optional[ImageState] = None

    def run(self) -> ImageState:
        """전체 이미지 처리 실행 (로드 → 저장 → 메타)"""
        start_time = time.time()
        src = str(self.policy.file.path)

        self.logger.info(f"[ImageSession] 시작: {src}")

        try:
            img, meta = self.loader.load()
        except Exception as e:
            self.logger.error(f"[ImageSession] 로드 실패: {e}")
            raise

        saved_img = None
        saved_meta = None

        try:
            saved_img = self.saver.save_image(img)
            saved_meta = self.saver.save_meta(meta)
        except Exception as e:
            self.logger.error(f"[ImageSession] 저장 중 오류 발생: {e}")
            raise

        elapsed = round((time.time() - start_time) * 1000, 2)
        self.state = ImageState(img, meta, self.policy.file.path, saved_img, saved_meta)

        # 결과 요약 로그
        summary = (
            f"[ImageSession] 완료: src={src}, fmt={meta.format or 'Unknown'}, "
            f"saved={'Y' if saved_img else 'N'}, meta={'Y' if saved_meta else 'N'}, "
            f"time={elapsed}ms"
        )
        self.logger.info(summary)

        return self.state
