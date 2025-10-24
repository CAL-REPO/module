# -*- coding: utf-8 -*-
"""XLOTO EntryPoint - Excel + OTO Pipeline.

사용자 인터페이스:
- 한 줄로 실행 가능
- ConfigLoader 내부 처리
- Adapter Policy 표준 섹션 사용

OTO 패턴 Section 매핑 (Adapter Policy 표준):
- xloto: XlOtoPolicy (Filter/Paths/Log)
- image_load: ImageLoadPolicy
- image_text_recognize: ImageTextRecognizePolicy
- translate: TranslatePolicy
- image_overlay: ImageOverlayPolicy

Example:
    >>> from xloto.entry_point import Xloto
    >>> xloto = Xloto(config_loader_cfg_path="configs/loader/config_loader_xloto.yaml")
    >>> result = xloto.run()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from cfg_utils import ConfigLoader
from logs_utils import LogManager

from xloto.policy.xloto_policy import XlOtoPolicy
from xloto.adapter.xloto import XlOto as XlOtoAdapter
from oto.adapter.oto import Oto


class Xloto:
    """XLOTO Pipeline EntryPoint.
    
    OTO 패턴:
    - ConfigLoader 내부화
    - Adapter에 Policy 전달
    - run()에서 Adapter에 위임
    
    Attributes:
        policy: XlOtoPolicy
        config: ConfigLoader
        log: loguru logger
    
    Example:
        >>> xloto = Xloto(config_loader_cfg_path="configs/loader/config_loader_xloto.yaml")
        >>> result = xloto.run()
    """
    
    def __init__(
        self,
        config_loader_cfg_path: Union[str, Path],
        *,
        xloto_cfg: Optional[Union[str, Path, dict, BaseModel]] = None,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize Xloto EntryPoint.
        
        Args:
            config_loader_cfg_path: ConfigLoader 설정 파일 경로 (필수)
            xloto_cfg: XlOtoPolicy 설정 (선택사항, None이면 ConfigLoader에서 'xloto' 섹션 사용)
            log_manager: 외부 LogManager (선택사항)
            **overrides: 런타임 오버라이드
        """
        # ========================================
        # ConfigLoader 먼저 초기화 (xloto 섹션 포함)
        # ========================================
        self.config = ConfigLoader(
            config_loader_cfg_path=str(self._resolve_path(config_loader_cfg_path)),
            env_os=["CASHOP_PATHS"]  #  환경변수 명시적 지정
        )
        
        # xloto_cfg가 None이면 ConfigLoader의 xloto 섹션 사용
        if xloto_cfg is None:
            xloto_cfg = self.config.to_dict(section="xloto")
        
        # XlOtoPolicy 로드
        self.policy = self._load_xloto_policy(xloto_cfg, **overrides)
        
        # ========================================
        # Unified LogManager 초기화 (Dual Logging 지원)
        # ========================================
        if log_manager:
            self._log_manager = log_manager
        elif self.policy.log:
            self._log_manager = LogManager(self.policy.log)
        else:
            self._log_manager = LogManager({"enabled": False})
        
        self.log = self._log_manager.logger
        self.log.debug(f"ConfigLoader loaded from: {config_loader_cfg_path}")
        
        # 섹션별 설정 추출 (Adapter Policy 표준)
        # OTO 패턴: Adapter Policy 이름 사용
        self.image_load_config = self.config.to_dict(section="image_load")
        self.text_recognize_config = self.config.to_dict(section="image_text_recognize")
        self.translate_config = self.config.to_dict(section="translate")
        self.overlay_config = self.config.to_dict(section="image_overlay")
        
        self.log.debug("ConfigLoader sections extracted (Adapter Policy standard)")
        
        # Adapters (lazy-load)
        self._xloto_adapter: Optional[XlOtoAdapter] = None
        self._oto_adapter: Optional[Oto] = None
        
        self.log.info("Xloto EntryPoint initialized")
    
    # ==========================================================================
    # Config Loading
    # ==========================================================================
    
    @staticmethod
    def _load_xloto_policy(
        cfg_like: Union[BaseModel, Path, str, dict, None],
        **overrides: Any
    ) -> XlOtoPolicy:
        """Load XlOtoPolicy from various sources."""
        # cfg_like가 None이면 기본 경로 사용
        if cfg_like is None:
            # __file__ 기준으로 _code/configs/xloto.yaml 찾기
            current = Path(__file__).resolve().parent
            while current.name not in ["_code", "CAShop - 구매대행"] and current.parent != current:
                current = current.parent
            
            if current.name == "_code":
                default_path = current / "configs" / "xloto.yaml"
                if default_path.exists():
                    cfg_like = str(default_path)
        
        from cfg_utils.services.config_like_loader import ConfigLikeLoader
        
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=XlOtoPolicy,
            caller_file=__file__,
            default_config_filename="xloto.yaml",
            **overrides
        )
    
    @staticmethod
    def _resolve_path(path: Union[str, Path]) -> Path:
        """프로젝트 루트 기준 경로 해석."""
        p = Path(path)
        if p.is_absolute() and p.exists():
            return p
        
        # 프로젝트 루트 찾기 (entry_point  xloto  scripts  _code)
        current = Path(__file__).resolve().parent
        
        # scripts/_code 레벨까지 올라가기
        while current.name not in ["_code", "CAShop - 구매대행"] and current.parent != current:
            current = current.parent
        
        # _code 디렉토리를 찾았으면
        if current.name == "_code":
            resolved = current / path
            if resolved.exists():
                return resolved
        
        # 찾지 못하면 원본 반환
        return p
    
    # ==========================================================================
    # Adapter Lazy Loading
    # ==========================================================================
    
    def get_xloto_adapter(self) -> XlOtoAdapter:
        """XlOto Adapter lazy-loading with unified logging.
        
        Returns:
            XlOtoAdapter 인스턴스
        """
        if self._xloto_adapter is None:
            self._xloto_adapter = XlOtoAdapter(
                policy=self.policy,
                log_manager=self._log_manager,  #  통합 LogManager 주입
            )
            self.log.debug("XlOto Adapter created with unified logging")
        
        return self._xloto_adapter
    
    def get_oto_adapter(self) -> Oto:
        """Oto Adapter lazy-loading with unified logging.
        
        Returns:
            Oto 인스턴스
        """
        if self._oto_adapter is None:
            # OTO 통합 설정 생성 (Adapter Policy 직접 사용)
            oto_config = {
                "image": self.image_load_config,
                "text_recognize": self.text_recognize_config,
                "translate": self.translate_config,
                "overlay": self.overlay_config,
            }
            
            self._oto_adapter = Oto(
                cfg_like=oto_config,
                log_manager=self._log_manager,  #  통합 LogManager 주입 (Dual Logging 지원)
            )
            self.log.debug("Oto Adapter created with unified logging")
        
        return self._oto_adapter
    
    # ==========================================================================
    # Core Pipeline Methods
    # ==========================================================================
    
    def run(
        self,
        *,
        excel_loader = None,  # Optional[ExcelLoader]
    ) -> Dict[str, Any]:
        """XLOTO Pipeline 실행 (Adapter 위임).
        
        EntryPoint Pattern:
        - ConfigLoader로 전체 설정 로드 (1회)
        - XlOtoAdapter.run()에 config_dict 전달
        
        Args:
            excel_loader: 외부 ExcelLoader (선택사항)
        
        Returns:
            XlOtoAdapter.run()의 결과 딕셔너리
        """
        self.log.info("="*80)
        self.log.info("🚀 XLOTO Pipeline Starting (EntryPoint → Adapter)")
        self.log.info("="*80)
        
        # ConfigLoader로 전체 통합 설정 로드 (1회만!)
        config_dict = self.config.to_dict()  # excel + oto 모두 포함
        
        # XlOtoAdapter에 위임 (config_dict 전달)
        adapter = self.get_xloto_adapter()
        
        result = adapter.run(
            config_dict=config_dict,
            excel_loader=excel_loader,
        )
        
        self.log.info("="*80)
        self.log.info("✅ XLOTO Pipeline Completed (EntryPoint)")
        self.log.info("="*80)
        
        return result
    
    def __repr__(self) -> str:
        return f"Xloto(policy={self.policy.__class__.__name__})"


__all__ = ["Xloto"]

