# -*- coding: utf-8 -*-
"""XLOTO Adapter - Excel + OTO 파이프라인

Architecture:
    1. ConfigLoader가 모든 section 병합 (excel, image_load, image_text_recognize, translate, image_overlay, paths, log)
    2. SectionExtractor.extract_batch()로 section 추출 (Policy.name 기반)
    3. ExcelLoad 내부 생성 (Lazy Loading)
    4. Oto에 개별 모듈 cfg_like 전달 (OTO와 동일한 패턴)
    5. CasExtractor/ExcelUpdater Service 사용

Pass-through Pattern (OTO와 동일):
    - cfg_like를 SectionExtractor로 추출
    - 각 모듈에 추출된 cfg_like 전달
    - OTO가 내부에서 필요한 section만 사용

Example:
    >>> # 외부에서 ConfigLoader 실행 (권장)
    >>> from cfg_utils import ConfigLoader
    >>> config = ConfigLoader(
    ...     config_loader_cfg_path="configs/loader/config_loader_xloto.yaml",
    ...     env_os=["CASHOP_PATHS"]
    ... )
    >>> xloto = XlOTO(cfg_like=config.to_dict(), log_manager=log_manager)
    >>> result = xloto.run(excel_path="data.xlsx")
"""

from __future__ import annotations
from csv import excel
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from datetime import datetime

from pydantic import BaseModel

from cfg_utils.services.section_extractor import SectionExtractor
from logs_utils import LogManager

from xl_utils.adapter.excel_load import ExcelLoad
from xl_utils.core.policy import ExcelLoadPolicy

from image_utils.core.policy import ImageLoadPolicy, ImageTextRecognizePolicy, ImageOverlayPolicy
from translate_utils.core.policy import TranslatePolicy

from oto.adapter.oto import OTO

from cashop.core.policy import CashopBasePolicy
from cashop.xloto.services.image_file_manager import ImageFileManager
from cashop.utils import CasExtractor, ExcelUpdater


class XlOTO:
    """Excel + OTO 파이프라인 (OTO와 동일한 패턴)
    
    Architecture:
        1. ConfigLoader가 모든 section 병합
        2. SectionExtractor.extract_batch()로 section 추출
        3. ExcelLoad/Oto 내부 생성 (Lazy Loading)
        4. OTO에 전체 cfg_like 전달 (OTO가 내부에서 필요한 section 추출)
        5. CasExtractor/ExcelUpdater Service로 로직 분리
    
    Pass-through Pattern:
        - XlOto는 cfg_like를 받아서 SectionExtractor로 Excel section만 추출
        - OTO에는 전체 cfg_like 전달 (OTO가 내부에서 4개 모듈 section 추출)
        - 불필요한 section이 OTO에 전달되어도 무시됨 (영향 미미)
    
    Lazy Loading:
        - ExcelLoad, Oto, ImageFileManager 첫 사용 시 초기화
    
    Example:
        >>> # 외부에서 ConfigLoader 실행 (권장)
        >>> from cfg_utils import ConfigLoader
        >>> config = ConfigLoader(
        ...     config_loader_cfg_path="configs/loader/config_loader_xloto.yaml",
        ...     env_os=["CASHOP_PATHS"]
        ... )
        >>> xloto = XlOTO(cfg_like=config.to_dict(), log_manager=log_manager)
        >>> result = xloto.run(excel_path="data.xlsx")
        
        >>> # 개별 cfg_like 우선 (OTO와 동일)
        >>> xloto = XlOTO(
        ...     cfg_like=config.to_dict(),
        ...     cfg_like_excel={"aliases": {...}},
        ...     cfg_like_image_load={"max_size": 2048},
        ...     log_manager=log_manager
        ... )
        
        >>> # Runtime override
        >>> result = xloto.run(
        ...     excel_path="data.xlsx",
        ...     excel__xw_app__visible=True,
        ...     image_overlay__save__directory="output/cas123"
        ... )
    """
    
    def __init__(
        self,
        cfg_like: Union[dict, None] = None,
        *,
        cfg_like_base: Union[BaseModel, Path, str, dict, None] = None,
        cfg_like_excel: Union[BaseModel, Path, str, dict, None] = None,
        cfg_like_image_load: Union[BaseModel, Path, str, dict, None] = None,
        cfg_like_image_text_recognize: Union[BaseModel, Path, str, dict, None] = None,
        cfg_like_translate: Union[BaseModel, Path, str, dict, None] = None,
        cfg_like_image_overlay: Union[BaseModel, Path, str, dict, None] = None,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Pass-through 패턴 초기화 (OTO와 동일)
        
        Architecture:
            1. ConfigLoader가 모든 section 병합
            2. Runtime overrides 병합
            3. SectionExtractor.extract_batch()로 모든 section 추출
            4. OTO에 전체 cfg_like + 개별 cfg_like 전달
        
        Args:
            cfg_like: 병합된 dict (ConfigLoader.to_dict() 결과)
            cfg_like_base: CashopBasePolicy 개별 설정 (우선순위 1)
            cfg_like_excel: ExcelLoadPolicy 개별 설정 (우선순위 1)
            cfg_like_image_load: ImageLoadPolicy 개별 설정
            cfg_like_image_text_recognize: ImageTextRecognizePolicy 개별 설정
            cfg_like_translate: TranslatePolicy 개별 설정
            cfg_like_image_overlay: ImageOverlayPolicy 개별 설정
            log_manager: LogManager 인스턴스
            **overrides: 런타임 오버라이드
        
        Cascading Priority:
            1. cfg_like_base (개별 cfg_like) - 최우선
            2. cfg_like["xloto"] (병합 dict의 section)
            3. None (Pydantic 기본값)
        
        Note:
            ⚠️ OTO는 전체 cfg_like를 받아 내부에서 4개 모듈 section 추출
            ⚠️ 불필요한 section이 OTO에 전달되어도 무시됨 (영향 미미)
        """
        # ========================================
        # Config 준비
        # ========================================
        merged_config = cfg_like or {}
        
        # Runtime overrides 병합
        if overrides:
            from keypath_utils import KeyPathDict
            override_dict = KeyPathDict.to_nested_dict(overrides)
            merged_config = {**merged_config, **override_dict}
        
        # ========================================
        # SectionExtractor.extract_batch() (모든 Policy section 추출)
        # ========================================
        extracted = SectionExtractor.extract_batch(
            merged_config=merged_config,
            individual_cfgs={
                CashopBasePolicy: cfg_like_base,
                ExcelLoadPolicy: cfg_like_excel,
                ImageOverlayPolicy: cfg_like_image_overlay,
            }
        )
        
        # Policy.name으로 추출
        base_policy_data = extracted[
            SectionExtractor.get_policy_name(CashopBasePolicy)
        ]
        self.policy = CashopBasePolicy(**base_policy_data) if isinstance(base_policy_data, dict) else base_policy_data  # type: ignore
        
        self._cfg_excel = extracted[
            SectionExtractor.get_policy_name(ExcelLoadPolicy)
        ]
        overlay_cfg = extracted[
            SectionExtractor.get_policy_name(ImageOverlayPolicy)
        ]
        
        # OTO에 전달할 cfg_like (전체 config + 개별 cfg_like)
        self._cfg_oto = merged_config
        if cfg_like_image_load:
            self._cfg_like_image_load = cfg_like_image_load
        if cfg_like_image_text_recognize:
            self._cfg_like_image_text_recognize = cfg_like_image_text_recognize
        if cfg_like_translate:
            self._cfg_like_translate = cfg_like_translate
        if cfg_like_image_overlay:
            self._cfg_like_image_overlay = cfg_like_image_overlay
        
        # ========================================
        # Logger 초기화
        # ========================================
        if log_manager:
            self.log = log_manager.logger
            self._parent_log_manager = log_manager
        elif self.policy.log:
            self._parent_log_manager = LogManager(self.policy.log)
            self.log = self._parent_log_manager.logger
        else:
            self._parent_log_manager = None
            self.log = LogManager({"enabled": False}).logger
        
        # ========================================
        # Lazy Loading (첫 사용 시 초기화)
        # ========================================
        self.policy: CashopBasePolicy  # Type hint 추가
        self._excel_load: Optional[ExcelLoad] = None
        self._OTO: Optional[OTO] = None
        self._image_manager: Optional[ImageFileManager] = None
        self._cas_extractor: Optional[CasExtractor] = None
        self._excel_updater: Optional[ExcelUpdater] = None
        
        self.log.debug("XLOTO adapter initialized")
    
    # ==========================================================================
    # Lazy Loading Properties
    # ==========================================================================
    
    @property
    def excel_load(self) -> ExcelLoad:
        """ExcelLoad Adapter lazy-loading"""
        if self._excel_load is None:
            pass
        return self._excel_load  # type: ignore
    
    @property
    def OTO(self) -> OTO:
        """OTO Adapter lazy-loading (OTO와 동일한 패턴)
        
        OTO에 전체 cfg_like + 개별 cfg_like 전달
        OTO가 내부에서 4개 모듈 section 추출
        """
        if self._OTO is None:
            self._OTO = OTO(
                cfg_like=self._cfg_oto,  # type: ignore
                log_manager=self._parent_log_manager,
            )
            self.log.debug("OTO adapter created")
        return self._OTO
    
    @property
    def image_manager(self) -> ImageFileManager:
        """ImageFileManager lazy-loading"""
        if self._image_manager is None:
            self._image_manager = ImageFileManager(
                public_img_dir=self.policy.paths.public_img_dir,
                origin_dirname=self.policy.paths.origin_dirname,
                translated_dirname=self.policy.paths.translated_dirname
            )
            self.log.debug("ImageFileManager created")
        return self._image_manager
    
    @property
    def cas_extractor(self) -> CasExtractor:
        """CasExtractor Service lazy-loading"""
        if self._cas_extractor is None:
            self._cas_extractor = CasExtractor()
            self.log.debug("CasExtractor created")
        return self._cas_extractor
    
    @property
    def excel_updater(self) -> ExcelUpdater:
        """ExcelUpdater Service lazy-loading"""
        if self._excel_updater is None:
            self._excel_updater = ExcelUpdater()
            self.log.debug("ExcelUpdater created")
        return self._excel_updater
    
    # ==========================================================================
    # Main Pipeline
    # ==========================================================================
    
    def run(self, **overrides: Any) -> Dict[str, Any]:
        """XLOTO Pipeline 실행 (단일 파일 + 단일 시트)
        
        Pipeline Flow:
            1. Policy에서 파일 경로/시트명 가져오기
            2. open_workbook(policy.excel.file_path)
            3. get_worksheet(policy.excel.sheet.sheet_name, column_aliases)
            4. CasExtractor로 CAS No 추출
            5. OTO 파이프라인 실행
            6. ExcelUpdater로 업데이트
        
        Args:
            **overrides: 런타임 오버라이드
                image_overlay__save__directory="output/cas123"
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "total_cas": int,
                "processed_cas": int,
                "cas_results": List[Dict],
                "error": Optional[str]
            }
        
        Example:
            >>> xloto = XlOTO(cfg_like=config.to_dict())
            >>> result = xloto.run()
            ...     excel_path="data.xlsx",
            ...     image_overlay__save__directory="output"
            ... )
        """
        result = {
            "success": False,
            "total_cas": 0,
            "processed_cas": 0,
            "cas_results": [],
            "error": None
        }
        
        try:
            self.log.info("="*80)
            self.log.info("XLOTO Pipeline Starting")
            self.log.info("="*80)
            
            # ================================================================
            # Step 1: Load Excel (ExcelLoad Adapter)
            # ================================================================
            self.log.info("[1/4] Loading Excel file...")

            # ExcelLoad 생성 (App 단위)
            excel = ExcelLoad(
                cfg_like=self._cfg_excel,  # type: ignore
                log_manager=self._parent_log_manager,
            )
            
            # ExcelLoadPolicy에서 파일 경로 가져오기
            excel_policy = excel.policy
            if not excel_policy.files or len(excel_policy.files) == 0:
                raise ValueError("ExcelLoadPolicy.files is empty. Please configure files in excel config.")
            
            file_config = excel_policy.files[0]  # 첫 번째 파일 사용
            excel_path = file_config.file_path
            if not excel_path:
                raise ValueError("ExcelLoadPolicy.files[0].file_path is None. Please configure file_path.")
            
            self.log.debug(f"  Excel path from ExcelLoadPolicy.files[0]: {excel_path}")
            
            if not file_config.sheets or len(file_config.sheets) == 0:
                raise ValueError("ExcelLoadPolicy.files[0].sheets is empty. Please configure sheets.")
            
            sheet_config = file_config.sheets[0]  # 첫 번째 시트 사용
            sheet_name = sheet_config.sheet_name
            column_aliases = sheet_config.get_column_aliases()
            
            self.log.debug(f"  Sheet: {sheet_name}")
            self.log.debug(f"  Column aliases: {list(column_aliases.keys()) if column_aliases else None}")
            
            with excel:
                # Workbook 열기
                wb = excel.open_workbook(excel_path)
                
                # Worksheet 가져오기
                ws = excel.get_worksheet(
                    wb,
                    sheet_name=sheet_name,
                    column_aliases=column_aliases if column_aliases else None
                )
                df = ws.to_dataframe(used_range=True, header=True, index=False)
                
                self.log.success(f"  Loaded DataFrame: {len(df)} rows")
                
                # ============================================================
                # Step 2: Extract CAS No (CasExtractor Service)
                # ============================================================
                self.log.info("[2/4] Extracting CAS No...")
                
                # ws.column_resolver 확인
                if ws.column_resolver is None:
                    raise ValueError("XwWs.column_resolver is None (preset not configured)")
                
                # download가 채워져있고, translation이 비어있을 때만 추출
                cas_list = self.cas_extractor.extract(
                    df,
                    ws.column_resolver,
                    cas_key="cas",
                    download_key="download",
                    download_must_be_empty=False,
                    translation_key="translation",
                    translation_must_be_empty=True
                )
                
                self.log.success(f"  Extracted {len(cas_list)} CAS No")
                self.log.debug(f"  CAS List: {cas_list}")
                
                if not cas_list:
                    result["success"] = True
                    return result
                
                result["total_cas"] = len(cas_list)
                
                # ============================================================
                # Step 3: Process CAS images (Oto + ImageFileManager)
                # ============================================================
                self.log.info(f"[3/4] Processing {len(cas_list)} CAS No...")
                
                processed_count = 0
                cas_results = []
                
                for idx, cas_item in enumerate(cas_list, 1):
                    cas_no = cas_item["cas_no"]
                    self.log.info(f"  [{idx}/{len(cas_list)}] Processing: {cas_no}")
                    
                    # Find missing images
                    missing_images = self.image_manager.get_missing_images(cas_no)
                    if not missing_images:
                        self.log.info(f"    ⏭️  CAS {cas_no}: Already translated (skipped)")
                        # 이미 번역된 경우도 cas_results에 추가
                        cas_results.append({
                            "cas_no": cas_no,
                            "success": True,
                            "processed_count": 0,
                            "skipped": True,  # ✅ Excel 업데이트를 위한 플래그
                            "translation_row": cas_item.get("cas_row"),  # ✅ CasExtractor 리팩토링 반영
                            "translation_col": cas_item.get("translation_col"),
                            "status": "already_translated"
                        })
                        continue
                    
                    self.log.info(f"    Found {len(missing_images)} images")
                    
                    # Process each image with OTO
                    success_count = 0
                    
                    # Translated 폴더 경로를 overlay save directory로 사용
                    translated_dir = self.image_manager.get_translated_dir(cas_no)
                    
                    for img_idx, img_path in enumerate(missing_images, 1):
                        self.log.info(f"    [{img_idx}/{len(missing_images)}] {img_path.name}")
                        
                        try:
                            # OTO Pipeline (Translated 폴더로 직접 저장)
                            self.log.debug(f"      Override: directory={translated_dir}, filename={img_path.name}")
                            oto_result = self.OTO.run(
                                source_path=img_path,
                                image_overlay__save__directory=translated_dir,
                                **overrides
                            )
                            
                            if oto_result.get("success"):
                                self.log.success(f"      Saved to: {translated_dir / img_path.name}")
                                success_count += 1
                            else:
                                self.log.error(f"      Failed: {oto_result.get('error')}")
                        
                        except Exception as e:
                            self.log.error(f"      Error: {e}")
                    
                    self.log.success(f"    Processed: {success_count}/{len(missing_images)}")
                    
                    # Success 또는 일부 성공한 경우 cas_results에 추가
                    if success_count > 0:
                        processed_count += 1
                        self.log.info(f"    ✅ CAS {cas_no}: Translated {success_count} images")
                        cas_results.append({
                            "cas_no": cas_no,
                            "success": True,
                            "processed_count": success_count,
                            "translation_row": cas_item.get("cas_row"),  # ✅ CasExtractor 리팩토링 반영
                            "translation_col": cas_item.get("translation_col"),
                            "status": "processed"
                        })
                    else:
                        # 모든 이미지 처리 실패
                        self.log.warning(f"    ❌ CAS {cas_no}: Translation failed")
                        cas_results.append({
                            "cas_no": cas_no,
                            "success": False,
                            "processed_count": 0,
                            "translation_row": cas_item.get("cas_row"),  # ✅ CasExtractor 리팩토링 반영
                            "translation_col": cas_item.get("translation_col"),
                            "status": "failed"
                        })
                
                result["processed_cas"] = processed_count
                result["cas_results"] = cas_results
                
                # ============================================================
                # Step 4: Update Excel (ExcelUpdater Service)
                # ============================================================
                if cas_results:
                    self.log.info("[4/4] Updating Excel...")
                    
                    updated_count = self.excel_updater.update(
                        worksheet=ws,
                        cas_results=cas_results,
                        date_value=datetime.now().strftime("%Y-%m-%d")
                    )
                    
                    self.log.success(f"  Updated {updated_count} cells")
                    
                    # 명시적 저장
                    self.log.debug("  Saving workbook...")
                    wb.book.save()
                    self.log.success("  Workbook saved")
                
                result["success"] = True
            
            self.log.info("="*80)
            self.log.success("XLOTO Pipeline Completed")
            self.log.info(f"   Total: {result['total_cas']}")
            self.log.info(f"   Processed: {result['processed_cas']}")
            self.log.info("="*80)
        
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            self.log.error(result["error"])
            
            import traceback
            self.log.error(traceback.format_exc())
        
        return result
