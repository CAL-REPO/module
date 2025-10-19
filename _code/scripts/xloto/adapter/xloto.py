# -*- coding: utf-8 -*-
"""XLOTO Adapter - Excel + OTO Pipeline Integration.

책임:
1. Excel에서 CAS No 리스트 추출 (DataFrame 필터링)
2. 각 CAS No별 이미지 처리 (Oto adapter 위임)
3. Excel에 처리 결과 기록

Adapter Pattern:
- Policy에 source 없음
- run()에서 config 경로 받음
- Standalone 사용 가능
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
from oto.adapter.oto import Oto

# Services
from xloto.services import CasExtractor, ImageFileManager

# xl_utils는 필요시 lazy import
# from xl_utils import XlController


class XlOto:
    """XLOTO Pipeline Adapter (Standalone).
    
    Excel + OTO 파이프라인 통합:
    1. Excel에서 CAS No 추출
    2. 이미지 OTO 처리
    3. Excel 업데이트
    
    Adapter Pattern:
    - Policy에 source 없음
    - run()에서 config 경로와 Excel controller 받음
    
    Attributes:
        policy: XlOtoPolicy 설정
        log: loguru logger
        oto: Oto adapter (lazy-loaded)
    
    Example:
        >>> xloto = XlOto(cfg_like="configs/xloto.yaml")
        >>> result = xloto.run(
        ...     config_path="configs/loader/config_loader_xloto.yaml"
        ... )
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        *,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize XlOto adapter.
        
        Args:
            cfg_like: XlOtoPolicy, YAML 경로, dict, 또는 None
            log_manager: 외부 LogManager (선택사항)
            **overrides: 런타임 오버라이드
        """
        # Load policy
        self.policy = self._load_config(cfg_like, **overrides)
        
        # LogManager 초기화
        if log_manager:
            self.log = log_manager.logger
        elif self.policy.log:
            self.log = LogManager(self.policy.log).logger
        else:
            self.log = LogManager({"enabled": False}).logger
        
        # Oto adapter는 lazy-load
        self._oto: Optional[Oto] = None
        
        # Services 초기화
        self._cas_extractor: Optional[CasExtractor] = None
        self._image_manager: Optional[ImageFileManager] = None
        
        self.log.debug("XlOto adapter initialized")
    
    # ==========================================================================
    # Config Loading
    # ==========================================================================
    
    @staticmethod
    def _load_config(
        cfg_like: Union[BaseModel, Path, str, dict, None],
        **overrides: Any
    ) -> XlOtoPolicy:
        """Load XlOtoPolicy from various sources."""
        from cfg_utils.services.config_like_loader import ConfigLikeLoader
        
        return ConfigLikeLoader.load_with_caller_path(
            cfg_like=cfg_like,
            policy_class=XlOtoPolicy,
            caller_file=__file__,
            default_config_filename="xloto.yaml",
            **overrides
        )
    
    # ==========================================================================
    # Service Lazy Loading
    # ==========================================================================
    
    def get_cas_extractor(self, excel_config: Dict[str, Any]) -> CasExtractor:
        """CasExtractor service lazy-loading.
        
        Args:
            excel_config: Excel 설정 (aliases 포함)
        
        Returns:
            CasExtractor 인스턴스
        """
        if self._cas_extractor is None:
            self._cas_extractor = CasExtractor(
                aliases=excel_config.get("aliases", {}),
                cas_column=self.policy.filter.cas_column,
                download_column=self.policy.filter.download_column,
                translation_column=self.policy.filter.translation_column
            )
        return self._cas_extractor
    
    def get_image_manager(self) -> ImageFileManager:
        """ImageFileManager service lazy-loading.
        
        Returns:
            ImageFileManager 인스턴스
        """
        if self._image_manager is None:
            self._image_manager = ImageFileManager(
                public_img_dir=self.policy.paths.public_img_dir,
                origin_dirname=self.policy.paths.origin_dirname,
                translated_dirname=self.policy.paths.translated_dirname
            )
        return self._image_manager
    
    # ==========================================================================
    # Oto Adapter Lazy Loading
    # ==========================================================================
    
    def get_oto(self, config_path: Union[Path, str]) -> Oto:
        """Oto adapter lazy-loading with config.
        
        Args:
            config_path: ConfigLoader 설정 파일 경로 (config_loader_xloto.yaml)
        
        Returns:
            Oto adapter 인스턴스
        """
        if self._oto is None:
            # ConfigLoader로 OTO 설정 로드
            # env_os: CASHOP_PATHS 환경변수 → paths.local.yaml 참조 해석
            config = ConfigLoader(config_loader_cfg_path=str(config_path))
            oto_config = config.to_dict()  # 전체 통합 설정
            
            # Oto adapter 생성 (image_load, text_recognize, translate, overlay 포함)
            self._oto = Oto(
                cfg_like=oto_config,
                log_manager=None,  # Oto가 자체 LogManager 생성
            )
            
            self.log.debug("Oto adapter created")
        
        return self._oto
    
    # ==========================================================================
    # Core Pipeline Methods
    # ==========================================================================
    
    def run(
        self,
        config_path: Union[Path, str],
        *,
        excel_controller = None,  # Type: Optional[XlController] (lazy import)
        cas_list_override: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """XLOTO Pipeline 실행.
        
        Pipeline Flow:
            1. Excel에서 CAS No 추출 (download=날짜, translation≠날짜)
            2. 각 CAS No별 이미지 OTO 처리
            3. Excel translation 셀에 날짜 기록
        
        Args:
            config_path: ConfigLoader 설정 파일 경로 (config_loader_xloto.yaml)
            excel_controller: 외부 XlController (선택사항, 없으면 생성)
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
            self.log.info("🚀 XLOTO Pipeline Starting")
            self.log.info("="*80)
            
            # ConfigLoader로 통합 설정 로드
            # CASHOP_PATHS 환경변수 → paths.local.yaml → 참조 해석
            config = ConfigLoader(config_loader_cfg_path=str(config_path))
            excel_config = config.to_dict(section="excel")
            
            # ================================================================
            # Step 1: Excel에서 CAS No 추출
            # ================================================================
            self.log.info("\n[1/3] Extracting CAS No from Excel...")
            
            if cas_list_override:
                cas_list = cas_list_override
                self.log.info(f"  Using override CAS list: {len(cas_list)} items")
            else:
                if excel_controller:
                    xl = excel_controller
                    close_excel = False
                else:
                    xl = XlController(cfg_like=excel_config)
                    xl.__enter__()
                    close_excel = True
                
                try:
                    # DataFrame 추출
                    ws = xl.get_worksheet()
                    df = ws.to_dataframe(anchor="A1", header=True, index=False)
                    
                    self.log.info(f"  Loaded DataFrame: {len(df)} rows")
                    
                    # CAS No 추출 (Service 사용)
                    cas_extractor = self.get_cas_extractor(excel_config)
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
            oto = self.get_oto(config_path)
            
            # ImageFileManager 생성
            image_manager = self.get_image_manager()
            
            processed_count = 0
            cas_results = []
            
            for idx, cas_item in enumerate(cas_list, 1):
                cas_no = cas_item["cas_no"]
                
                self.log.info(f"\n{'='*80}")
                self.log.info(f"[{idx}/{len(cas_list)}] Processing: {cas_no}")
                self.log.info(f"{'='*80}")
                
                # 미처리 이미지 찾기 (Service 사용)
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
                            # 번역된 이미지 저장 (Service 사용)
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
                    xl = XlController(cfg_like=excel_config)
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
        return f"XlOto(policy={self.policy.__class__.__name__})"
