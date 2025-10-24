# -*- coding: utf-8 -*-
"""OTO Pipeline Policy - Logging configuration only.

책임:
1. OTO 파이프라인 로그 정책 관리
2. 서브 모듈 정책은 SectionExtractor로 동적 추출 (Pass-through Pattern)
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from logs_utils.core.policy import LogPolicy


class OTOPolicy(BaseModel):
    """OTO Pipeline 로그 정책 (Pass-through Pattern).
    
    OTO Adapter는 SectionExtractor로 각 모듈 정책을 동적으로 추출하므로,
    OTOPolicy는 로깅 설정만 관리합니다.
    
    서브 모듈 정책 관리 (SectionExtractor 사용):
    - ImageLoadPolicy: Policy.name="image_load"로 자동 추출
    - ImageTextRecognizePolicy: Policy.name="image_text_recognize"로 자동 추출
    - TranslatePolicy: Policy.name="translate"로 자동 추출
    - ImageOverlayPolicy: Policy.name="image_overlay"로 자동 추출
    
    Attributes:
        name: Policy 이름 ("oto")
        log: OTO 파이프라인 로그 정책
    
    Example:
        >>> # OTOPolicy는 로깅만 관리
        >>> from cfg_utils import ConfigLoader
        >>> config = ConfigLoader(
        ...     config_loader_cfg_path="configs/loader/config_loader_oto.yaml",
        ...     env_os=["CASHOP_PATHS"]
        ... )
        >>> oto = Oto(cfg_like=config.to_dict(), log_manager=log_manager)
        
        >>> # 서브 모듈 정책은 SectionExtractor가 자동 추출
        >>> # - merged_config["image_load"] → ImageLoadPolicy
        >>> # - merged_config["translate"] → TranslatePolicy
        >>> # - 등등...
    
    Note:
        ⚠️ 서브 모듈 정책 필드는 없음 (SectionExtractor가 동적 추출).
        ⚠️ ConfigLoader 섹션명과 Policy.name 필드가 일치해야 함.
    """
    name: str = "oto"
    log: LogPolicy = Field(
        default_factory=LogPolicy,  # type: ignore
        description="OTO 파이프라인 로그 정책"
    )


