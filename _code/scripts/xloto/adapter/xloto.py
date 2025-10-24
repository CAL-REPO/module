# -*- coding: utf-8 -*-
"""XLOTO Adapter - Excel + OTO Pipeline Integration.

Pass-through Pattern (Oto와 동일):
1. ConfigLoader 실행은 EntryPoint/external script 책임
2. XlOto는 cfg_like dict만 받음 (excel + xloto + oto 전체)
3. SectionExtractor로 excel, oto 섹션 동적 추출
4. Lazy-load로 성능 최적화
5. 인스턴스 재사용 가능

Adapter Pattern:
- __init__에서 cfg_like (통합 dict), cfg_like_excel, cfg_like_oto 받음
- SectionExtractor로 개별 섹션 추출 (Cascading Priority)
- run()에 excel_controller, cas_list_override만 전달
- Standalone 사용 가능

Example:
    >>> # EntryPoint에서 ConfigLoader 실행
    >>> from cfg_utils import ConfigLoader
    >>> config = ConfigLoader(
    ...     config_loader_cfg_path="configs/loader/config_loader_xloto.yaml",
    ...     env_os=["CASHOP_PATHS"]
    ... )
    >>> 
    >>> # XlOto는 merged dict만 받음
    >>> xloto = XlOto(cfg_like=config.to_dict())
    >>> result = xloto.run(excel_controller=xl)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from pydantic import BaseModel

from cfg_utils.services.config_like_loader import ConfigLikeLoader
from cfg_utils.services.section_extractor import SectionExtractor
from logs_utils import LogManager

from xloto.policy.xloto_policy import XlOtoPolicy
from oto.adapter.oto import Oto
from oto.policy.oto_policy import OTOPolicy

# Services
from xloto.services import ImageFileManager

# xl_utils는 필요시 lazy import
# from xl_utils import XlController


class XlOto:
    """XLOTO Pipeline Adapter (Pass-through Pattern).
    
    Excel + OTO 파이프라인 통합:
    1. Excel에서 CAS No 추출
    2. 이미지 OTO 처리
    3. Excel 업데이트
    
    Pass-through Pattern (SectionExtractor 사용):
    - ConfigLoader는 EntryPoint에서 실행
    - XlOto는 merged dict만 받음
    - SectionExtractor로 excel, oto 섹션 동적 추출
    - Cascading Priority: individual cfg_like > merged_config[section] > None
    
    Attributes:
        policy: XlOtoPolicy 설정 (paths, log)
        log: loguru logger
        oto: Oto adapter (lazy-loaded)
        _cfg_like_excel: Excel 설정 (extracted)
        _cfg_like_oto: OTO 설정 (extracted)
    
    Example:
        >>> # EntryPoint에서 ConfigLoader 실행
        >>> from cfg_utils import ConfigLoader
        >>> config = ConfigLoader(
        ...     config_loader_cfg_path="configs/loader/config_loader_xloto.yaml",
        ...     env_os=["CASHOP_PATHS"]
        ... )
        >>> 
        >>> # XlOto는 merged dict만 받음
        >>> xloto = XlOto(cfg_like=config.to_dict())
        >>> result = xloto.run(excel_controller=xl)
        
        >>> # Individual cfg_like 우선 (Cascading Priority)
        >>> xloto = XlOto(
        ...     cfg_like=config.to_dict(),
        ...     cfg_like_excel="custom_excel.yaml",  # Override
        ...     cfg_like_oto={"image_load": {...}}   # Override
        ... )
    """
    
    def __init__(
        self,
        cfg_like: Union[BaseModel, Path, str, dict, None] = None,
        *,
        cfg_like_excel: Union[BaseModel, Path, str, dict, None] = None,
        cfg_like_oto: Union[BaseModel, Path, str, dict, None] = None,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Initialize XlOto adapter.
        
        Pass-through Pattern:
        - cfg_like: ConfigLoader merged dict (전체 통합 설정)
        - cfg_like_excel: Excel 개별 설정 (우선순위 높음)
        - cfg_like_oto: OTO 개별 설정 (우선순위 높음)
        - overrides: 런타임 오버라이드
        
        SectionExtractor 동작:
        1. merged_config = cfg_like or {}
        2. overrides 병합 (KeyPathDict)
        3. SectionExtractor.extract_batch()로 섹션 추출
           - excel: "excel" 섹션 (XlController용)
           - oto: "oto" 섹션 (Oto adapter용)
        4. Cascading Priority: individual > merged > None
        
        Args:
            cfg_like: XlOtoPolicy, YAML 경로, dict, 또는 None
            cfg_like_excel: Excel 개별 설정 (ConfigLikeLoader로 로드 가능)
            cfg_like_oto: OTO 개별 설정 (ConfigLikeLoader로 로드 가능)
            log_manager: 외부 LogManager (선택사항)
            **overrides: 런타임 오버라이드 (KeyPathDict 형식, 예: excel__aliases__cas="CAS번호")
        
        Note:
            ⚠️ ConfigLoader 실행은 EntryPoint/external script 책임!
            ⚠️ cfg_like=None이면 빈 dict로 처리 (Pydantic 기본값 사용)
        """
        from data_utils.keypath_dict import KeyPathDict
        
        # Merge overrides into cfg_like
        merged_config = cfg_like or {}
        if overrides:
            override_dict = KeyPathDict.to_nested_dict(overrides)
            merged_config = {**merged_config, **override_dict}
        
        # SectionExtractor로 섹션 추출 (Cascading Priority)
        # - "excel": XlController용 설정
        # - "oto": Oto adapter용 설정 (image_load, translate, overlay 등 포함)
        # Note: excel, oto는 하드코딩이 아닌 섹션명 (ConfigLoader source[1]과 일치)
        extracted = {
            "excel": SectionExtractor.extract(
                merged_config=merged_config,
                individual_cfg=cfg_like_excel,
                policy_class=None,  # Excel은 Policy 없음 (dict만 사용)
                section_name="excel"
            ),
            "oto": SectionExtractor.extract(
                merged_config=merged_config,
                individual_cfg=cfg_like_oto,
                policy_class=OTOPolicy
            )
        }
        
        self._cfg_like_excel = extracted["excel"]
        self._cfg_like_oto = extracted["oto"]
        
        # XlOtoPolicy 생성 (paths, log만 관리)
        try:
            self.policy = XlOtoPolicy(**merged_config)
        except Exception:
            self.policy = XlOtoPolicy()
        
        # LogManager 초기화 (parent logger only)
        if log_manager:
            self.log = log_manager.logger
            self._parent_log_manager = log_manager
        elif self.policy.log:
            self._parent_log_manager = LogManager(self.policy.log)
            self.log = self._parent_log_manager.logger
        else:
            self._parent_log_manager = None
            self.log = LogManager({"enabled": False}).logger
        
        # Oto adapter는 lazy-load
        self._oto: Optional[Oto] = None
        
        # Services 초기화
        self._cas_extractor: Optional[CasExtractor] = None
        self._image_manager: Optional[ImageFileManager] = None
        
        self.log.debug("XlOto adapter initialized")
    
    # ==========================================================================
    # Service Lazy Loading
    # ==========================================================================
    
    def get_cas_extractor(self) -> CasExtractor:
        """CasExtractor service lazy-loading.
        
        Note:
            ⚠️ Excel config는 __init__에서 이미 추출됨 (_cfg_like_excel)
        
        Returns:
            CasExtractor 인스턴스
        """
        if self._cas_extractor is None:
            # __init__에서 추출한 excel config 사용
            excel_config = self._cfg_like_excel or {}
            
            self._cas_extractor = CasExtractor(
                aliases=excel_config.get("aliases", {}),
                cas_column=self.policy.filter.cas_column if hasattr(self.policy, 'filter') else "cas",
                download_column=self.policy.filter.download_column if hasattr(self.policy, 'filter') else "download",
                translation_column=self.policy.filter.translation_column if hasattr(self.policy, 'filter') else "translation"
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
    
    def get_oto(self) -> Oto:
        """Oto adapter lazy-loading.
        
        Pass-through Pattern:
        - __init__에서 이미 추출한 _cfg_like_oto 사용
        - ConfigLoader 실행은 EntryPoint 책임
        
        Returns:
            Oto adapter 인스턴스
        
        Note:
            ⚠️ ConfigLoader 실행 제거 (EntryPoint에서 실행)
            ⚠️ _cfg_like_oto는 __init__에서 SectionExtractor로 추출됨
        """
        if self._oto is None:
            # __init__에서 추출한 oto config 사용
            # - image_load, text_recognize, translate, overlay 섹션 모두 포함
            self._oto = Oto(
                cfg_like=self._cfg_like_oto,
                log_manager=None,  # Oto가 자체 LogManager 생성
            )
            
            self.log.debug("Oto adapter created")
        
        return self._oto
    
    # ==========================================================================
    # Core Pipeline Methods
    # ==========================================================================
    
    def run(
        self,
        *,
        excel_controller = None,  # Type: Optional[XlController] (lazy import)
        cas_list_override: Optional[List[str]] = None,
        **overrides: Any
    ) -> Dict[str, Any]:
        """XLOTO Pipeline 실행.
        
        Pipeline Flow:
            1. Excel에서 CAS No 추출 (download=날짜, translation≠날짜)
            2. 각 CAS No별 이미지 OTO 처리
            3. Excel translation 셀에 날짜 기록
        
        Pass-through Pattern:
            - ConfigLoader 실행 제거 (EntryPoint 책임)
            - __init__에서 추출한 _cfg_like_excel, _cfg_like_oto 사용
        
        Args:
            excel_controller: 외부 XlController (선택사항, 없으면 생성)
            cas_list_override: CAS No 리스트 강제 지정 (테스트용)
            **overrides: Oto Adapter로 전달할 runtime overrides
                예: image_load__save__name__suffix="step1"
                    image_overlay__save__name__suffix="final"
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "total_cas": int,
                "processed_cas": int,
                "cas_results": List[Dict],
                "error": Optional[str]
            }
        
        Note:
            ⚠️ ConfigLoader는 EntryPoint에서 실행 (xloto.py 등)
            ⚠️ Excel config는 __init__에서 추출된 _cfg_like_excel 사용
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
            
            # __init__에서 추출한 excel config 사용
            excel_config = self._cfg_like_excel or {}
            
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
                    from xl_utils import XlController
                    xl = XlController(cfg_like=excel_config)
                    xl.__enter__()
                    close_excel = True
                
                try:
                    # DataFrame 추출
                    ws = xl.get_worksheet()
                    df = ws.to_dataframe(anchor="A1", header=True, index=False)
                    
                    self.log.info(f"  Loaded DataFrame: {len(df)} rows")
                    
                    # CAS No 추출 (Service 사용)
                    cas_extractor = self.get_cas_extractor()
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
            
            # Oto adapter 생성 (lazy-load)
            oto = self.get_oto()
            
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
                        # Oto adapter 실행 (overrides 전달)
                        oto_result = oto.run(
                            source_path=img_path,
                            **overrides
                        )
                        
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
