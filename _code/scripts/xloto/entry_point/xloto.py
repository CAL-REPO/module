# -*- coding: utf-8 -*-
"""XLOTO EntryPoint - Excel + OTO Pipeline.

사용자 인터페이스:
- 한 줄로 실행 가능
- ConfigLoader 내부 처리
- 각 adapter에 섹션별 설정 자동 매핑

Example:
    >>> from xloto.entry_point import Xloto
    >>> xloto = Xloto()
    >>> result = xloto.run()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from PIL import Image
from pydantic import BaseModel

from cfg_utils import ConfigLoader
from logs_utils import LogManager

from xloto.policy.xloto_policy import XlOtoPolicy
from xloto.adapter.xloto import XlOto as XlOtoAdapter
from oto.adapter.oto import Oto


class Xloto:
    """XLOTO Pipeline EntryPoint.
    
    사용자 친화적 인터페이스:
    - ConfigLoader 로직 내부화
    - 섹션별 자동 매핑 및 adapter 전달
    
    Attributes:
        policy: XlOtoPolicy (xloto.yaml에서 로드)
        config: ConfigLoader
        log: loguru logger
    
    Example:
        >>> # 기본 사용 (config_loader_cfg_path 필수)
        >>> xloto = Xloto(config_loader_cfg_path="configs/loader/config_loader_xloto.yaml")
        >>> result = xloto.run()
        
        >>> # 커스텀 설정
        >>> xloto = Xloto(
        ...     config_loader_cfg_path="configs/loader/config_loader_xloto.yaml",
        ...     xloto_cfg="custom_xloto.yaml"
        ... )
        >>> result = xloto.run(cas_list_override=["CAPFB-001"])
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
            xloto_cfg: XlOtoPolicy 설정 (기본: configs/xloto.yaml)
            log_manager: 외부 LogManager (선택사항)
            **overrides: 런타임 오버라이드
        """
        # XlOtoPolicy 로드
        self.policy = self._load_xloto_policy(xloto_cfg, **overrides)
        
        # LogManager 초기화
        if log_manager:
            self.log = log_manager.logger
        elif self.policy.log:
            self.log = LogManager(self.policy.log).logger
        else:
            self.log = LogManager({"enabled": False}).logger
        
        # ConfigLoader 초기화 (외부에서 전달받은 경로 사용)
        # env_os: CASHOP_PATHS 환경변수 → paths.local.yaml 참조 해석
        self.log.debug(f"Loading ConfigLoader: {config_loader_cfg_path}")
        self.config = ConfigLoader(
            config_loader_cfg_path=str(self._resolve_path(config_loader_cfg_path)),
            env_os=["CASHOP_PATHS"]  # 🔥 환경변수 명시적 지정
        )
        
        # 섹션별 설정 추출
        self.excel_config = self.config.to_dict(section="excel")
        self.image_load_config = self.config.to_dict(section="image_load")
        self.text_recognize_config = self.config.to_dict(section="text_recognize")
        self.translate_config = self.config.to_dict(section="translate")
        self.overlay_config = self.config.to_dict(section="overlay")
        
        self.log.debug("ConfigLoader sections extracted")
        
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
        
        # 프로젝트 루트 찾기 (entry_point → xloto → scripts → _code)
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
        """XlOto Adapter lazy-loading.
        
        Returns:
            XlOtoAdapter 인스턴스
        """
        if self._xloto_adapter is None:
            self._xloto_adapter = XlOtoAdapter(
                cfg_like=self.policy,
                log_manager=None,  # Adapter가 자체 LogManager 생성
            )
            self.log.debug("XlOto Adapter created")
        
        return self._xloto_adapter
    
    def get_oto_adapter(self) -> Oto:
        """Oto Adapter lazy-loading with mapped config.
        
        Returns:
            Oto 인스턴스
        """
        if self._oto_adapter is None:
            # OTO 통합 설정 생성 (섹션 매핑)
            oto_config = {
                "image_load": self.image_load_config,
                "text_recognize": self.text_recognize_config,
                "translate": self.translate_config,
                "overlay": self.overlay_config,
            }
            
            self._oto_adapter = Oto(
                cfg_like=oto_config,
                log_manager=None,  # Oto가 자체 LogManager 생성
            )
            self.log.debug("Oto Adapter created")
        
        return self._oto_adapter
    
    # ==========================================================================
    # Core Pipeline Methods
    # ==========================================================================
    
    def run(
        self,
        *,
        excel_controller = None,  # Optional[XlController]
        cas_list_override: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """XLOTO Pipeline 실행.
        
        Pipeline Flow:
            1. Excel에서 CAS No 추출
            2. 각 CAS No별 이미지 OTO 처리
            3. Excel translation 셀 업데이트
        
        Args:
            excel_controller: 외부 XlController (선택사항)
            cas_list_override: CAS No 리스트 강제 지정 (테스트용)
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "total_cas": int,
                "processed_cas": int,
                "cas_results": List[Dict],
                "error": Optional[str]
            }
        """
        result = {
            "success": False,
            "total_cas": 0,
            "processed_cas": 0,
            "cas_results": [],
            "error": None,
        }
        
        try:
            self.log.info("="*80)
            self.log.info("🚀 XLOTO Pipeline Starting (EntryPoint)")
            self.log.info("="*80)
            
            # ================================================================
            # Step 1: Excel에서 CAS No 추출
            # ================================================================
            self.log.info("\n[1/3] Extracting CAS No from Excel...")
            
            if cas_list_override:
                cas_list = cas_list_override
                self.log.info(f"  Using override CAS list: {len(cas_list)} items")
            else:
                # XlController 사용하여 CAS 추출
                # (XlOtoAdapter를 사용하지 않고 직접 처리)
                from xloto.services import CasExtractor
                
                if excel_controller:
                    xl = excel_controller
                    close_excel = False
                else:
                    # xl_utils lazy import
                    from xl_utils import XlController
                    
                    # 🔍 DEBUG: excel_config 내용 확인
                    self.log.debug(f"  excel_config keys: {list(self.excel_config.keys())}")
                    self.log.debug(f"  target: {self.excel_config.get('target')}")
                    self.log.debug(f"  xw_app: {self.excel_config.get('xw_app')}")
                    self.log.debug(f"  xw_wb: {self.excel_config.get('xw_wb')}")
                    self.log.debug(f"  xw_ws: {self.excel_config.get('xw_ws')}")
                    
                    xl = XlController(cfg_like=self.excel_config)
                    xl.__enter__()
                    close_excel = True
                
                try:
                    ws = xl.get_worksheet()
                    # 수동 범위 지정: A1:T100 (20개 컬럼, 빈 열 포함)
                    # expand="table"은 빈 열에서 멈추므로 수동 범위 지정 필요
                    df = ws.cell_ops.read_range("A1:T100")
                    
                    # DataFrame으로 변환 (첫 행을 헤더로)
                    if df and len(df) > 0:
                        import pandas as pd
                        headers = df[0]
                        data = df[1:]
                        df = pd.DataFrame(data, columns=headers)
                        # 빈 행만 제거 (빈 열은 유지 - download, translation 등이 필요)
                        df = df.dropna(how='all')
                    else:
                        import pandas as pd
                        df = pd.DataFrame()
                    
                    self.log.info(f"  Loaded DataFrame: {len(df)} rows, {len(df.columns)} columns")
                    self.log.debug(f"  DataFrame columns (all): {list(df.columns)}")
                    
                    # CasExtractor 사용
                    cas_extractor = CasExtractor(
                        aliases=self.excel_config.get("aliases", {}),
                        cas_column=self.policy.filter.cas_column,
                        download_column=self.policy.filter.download_column,
                        translation_column=self.policy.filter.translation_column
                    )
                    cas_list = cas_extractor.extract(df)
                    
                    self.log.success(f"  ✅ Extracted {len(cas_list)} CAS No")
                    
                finally:
                    if close_excel:
                        xl.__exit__(None, None, None)
            
            if not cas_list:
                self.log.warning("No CAS No to process")
                result["success"] = True
                return result
            
            result["total_cas"] = len(cas_list)
            
            # ================================================================
            # Step 2: 각 CAS No별 이미지 OTO 처리
            # ================================================================
            self.log.info(f"\n[2/3] Processing {len(cas_list)} CAS No...")
            
            # Oto adapter 생성
            oto = self.get_oto_adapter()
            
            # ImageFileManager 생성
            from xloto.services import ImageFileManager
            image_manager = ImageFileManager(
                public_img_dir=self.policy.paths.public_img_dir,
                origin_dirname=self.policy.paths.origin_dirname,
                translated_dirname=self.policy.paths.translated_dirname
            )
            
            # 디버깅: ImageFileManager 설정 확인
            self.log.debug(f"  ImageFileManager initialized:")
            self.log.debug(f"    public_img_dir: {self.policy.paths.public_img_dir}")
            self.log.debug(f"    origin_dirname: {self.policy.paths.origin_dirname}")
            self.log.debug(f"    translated_dirname: {self.policy.paths.translated_dirname}")
            self.log.debug(f"    Resolved path: {image_manager.public_img_dir}")
            
            processed_count = 0
            cas_results = []
            
            for idx, cas_item in enumerate(cas_list, 1):
                cas_no = cas_item["cas_no"]
                
                self.log.info(f"\n{'='*80}")
                self.log.info(f"[{idx}/{len(cas_list)}] Processing: {cas_no}")
                self.log.info(f"{'='*80}")
                
                # 미처리 이미지 찾기
                missing_images = image_manager.get_missing_images(cas_no)
                
                if not missing_images:
                    self.log.info(f"  ℹ️  No images to process")
                    cas_results.append({
                        "cas_no": cas_no,
                        "success": True,
                        "processed_count": 0,
                        "message": "No images to process"
                    })
                    continue
                
                self.log.info(f"  📸 Found {len(missing_images)} images")
                
                # 이미지 처리
                success_count = 0
                for img_idx, img_path in enumerate(missing_images, 1):
                    self.log.info(f"\n     [{img_idx}/{len(missing_images)}] {img_path.name}")
                    
                    try:
                        # 이미지 로드
                        image = Image.open(img_path)
                        
                        # Oto adapter 실행
                        oto_result = oto.run(image=image, source_path=img_path)
                        
                        if oto_result.get("success"):
                            # 번역된 이미지 저장
                            final_image = oto_result.get("image")
                            if final_image:
                                output_dir = image_manager.get_translated_dir(cas_no)
                                output_dir.mkdir(parents=True, exist_ok=True)
                                
                                output_path = output_dir / img_path.name
                                final_image.save(output_path, quality=95)
                                
                                self.log.success(f"        ✅ Saved: {output_path.name}")
                                success_count += 1
                        else:
                            error_msg = oto_result.get("error", "Unknown error")
                            self.log.error(f"        ❌ Failed: {error_msg}")
                    
                    except Exception as e:
                        self.log.error(f"        ❌ Error: {e}")
                        import traceback
                        self.log.debug(traceback.format_exc())
                
                self.log.success(f"\n  ✅ Processed: {success_count}/{len(missing_images)}")
                
                if success_count > 0:
                    processed_count += 1
                    cas_results.append({
                        "cas_no": cas_no,
                        "success": True,
                        "processed_count": success_count,
                        "total_count": len(missing_images),
                        **cas_item  # translation_row, translation_col 포함
                    })
                else:
                    cas_results.append({
                        "cas_no": cas_no,
                        "success": False,
                        "processed_count": 0,
                        "message": "All images failed"
                    })
            
            result["processed_cas"] = processed_count
            result["cas_results"] = cas_results
            
            self.log.info(f"\n{'='*80}")
            self.log.success(f"[2/3] ✅ Processed {processed_count}/{len(cas_list)} CAS No")
            self.log.info(f"{'='*80}")
            
            # ================================================================
            # Step 3: Excel translation 셀 업데이트
            # ================================================================
            if processed_count > 0 and not cas_list_override:
                self.log.info("\n[3/3] Updating Excel translation cells...")
                
                current_date = datetime.now().strftime("%Y-%m-%d")
                
                if excel_controller:
                    xl = excel_controller
                    close_excel = False
                else:
                    from xl_utils import XlController
                    xl = XlController(cfg_like=self.excel_config)
                    xl.__enter__()
                    close_excel = True
                
                try:
                    ws = xl.get_worksheet()
                    
                    # 성공한 CAS No만 업데이트
                    successful_cas = [r for r in cas_results if r.get("success") and r.get("processed_count", 0) > 0]
                    
                    for cas_item in successful_cas:
                        row = cas_item.get("translation_row")
                        col = cas_item.get("translation_col")
                        
                        if row and col:
                            # 컬럼명 → 인덱스 변환
                            df = ws.to_dataframe(anchor="A1", header=True, index=False)
                            col_idx = df.columns.get_loc(col)
                            if isinstance(col_idx, int):
                                col_idx += 1  # 1-based
                            else:
                                col_idx = 1  # fallback
                            
                            ws.write_cell(row, col_idx, current_date)
                            self.log.info(f"     ✅ {cas_item['cas_no']}: ({row}, {col_idx}) = {current_date}")
                    
                    self.log.success(f"  ✅ Updated {len(successful_cas)} cells")
                
                finally:
                    if close_excel:
                        xl.__exit__(None, None, None)
            else:
                self.log.info("\n[3/3] Skipping Excel update (no processed items or override mode)")
            
            # ================================================================
            # Complete
            # ================================================================
            result["success"] = True
            
            self.log.info(f"\n{'='*80}")
            self.log.success(f"✅ XLOTO Pipeline Completed")
            self.log.info(f"   Total: {result['total_cas']} CAS No")
            self.log.info(f"   Processed: {result['processed_cas']} CAS No")
            self.log.info(f"{'='*80}\n")
            
        except Exception as e:
            result["error"] = f"Unexpected error: {type(e).__name__}: {e}"
            self.log.error(result["error"])
            
            import traceback
            self.log.error(traceback.format_exc())
        
        return result
    
    def __repr__(self) -> str:
        return f"Xloto(policy={self.policy.__class__.__name__})"


__all__ = ["Xloto"]
