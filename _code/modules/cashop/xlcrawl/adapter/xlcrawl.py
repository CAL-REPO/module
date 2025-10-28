# -*- coding: utf-8 -*-
"""XLCRAWL Adapter - Excel + Crawl 파이프라인

Architecture:
    1. ConfigLoader가 모든 section 병합 (excel, sync_crawl, webdriver_manager, paths, log)
    2. SectionExtractor.extract_batch()로 section 추출 (Policy.name 기반)
    3. ExcelLoad 내부 생성 (Lazy Loading)
    4. SyncCrawl에 개별 모듈 cfg_like 전달 (xloto와 동일한 패턴)
    5. CasExtractor/ExcelUpdater Service 사용

Pass-through Pattern (xloto와 동일):
    - cfg_like를 SectionExtractor로 추출
    - 각 모듈에 추출된 cfg_like 전달
    - SyncCrawl이 내부에서 필요한 section만 사용

Example:
    >>> # 외부에서 ConfigLoader 실행 (권장)
    >>> from cfg_utils import ConfigLoader
    >>> config = ConfigLoader(
    ...     config_loader_cfg_path="configs/loader/config_loader_xlcrawl.yaml",
    ...     env_os=["CASHOP_PATHS"]
    ... )
    >>> xlcrawl = XlCrawl(cfg_like=config.to_dict(), log_manager=log_manager)
    >>> result = xlcrawl.run(excel_path="data.xlsx")
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from datetime import datetime

import pandas as pd
from pydantic import BaseModel

from cfg_utils.services.section_extractor import SectionExtractor
from logs_utils import LogManager

from xl_utils.adapter.excel_load import ExcelLoad
from xl_utils.core.policy import ExcelLoadPolicy

from crawl_utils.adapter.sync_crawl import SyncCrawl
from crawl_utils.core.policy import SyncCrawlPolicy

from cashop.core.policy import CashopBasePolicy
from cashop.utils import CasExtractor, ExcelUpdater


class XlCrawl:
    """Excel + Crawl 파이프라인 (xloto와 동일한 패턴)
    
    Architecture:
        1. ConfigLoader가 모든 section 병합
        2. SectionExtractor.extract_batch()로 section 추출
        3. ExcelLoad/SyncCrawl 내부 생성 (Lazy Loading)
        4. SyncCrawl에 전체 cfg_like 전달 (SyncCrawl이 내부에서 필요한 section 추출)
        5. CasExtractor/ExcelUpdater Service로 로직 분리
    
    Pass-through Pattern:
        - XlCrawl은 cfg_like를 받아서 SectionExtractor로 Excel section만 추출
        - SyncCrawl에는 전체 cfg_like 전달 (SyncCrawl이 내부에서 section 추출)
        - 불필요한 section이 SyncCrawl에 전달되어도 무시됨 (영향 미미)
    
    Lazy Loading:
        - ExcelLoad, SyncCrawl 첫 사용 시 초기화
    
    Example:
        >>> # 외부에서 ConfigLoader 실행 (권장)
        >>> from cfg_utils import ConfigLoader
        >>> config = ConfigLoader(
        ...     config_loader_cfg_path="configs/loader/config_loader_xlcrawl.yaml",
        ...     env_os=["CASHOP_PATHS"]
        ... )
        >>> xlcrawl = XlCrawl(cfg_like=config.to_dict(), log_manager=log_manager)
        >>> result = xlcrawl.run(excel_path="data.xlsx")
        
        >>> # 개별 cfg_like 우선 (xloto와 동일)
        >>> xlcrawl = XlCrawl(
        ...     cfg_like=config.to_dict(),
        ...     cfg_like_excel={"aliases": {...}},
        ...     cfg_like_sync_crawl={"browser__headless": True},
        ...     cfg_like_webdriver_manager={"driver_type": "chrome"},
        ...     log_manager=log_manager
        ... )
        
        >>> # Runtime override
        >>> result = xlcrawl.run(
        ...     excel_path="data.xlsx",
        ...     excel__xw_app__visible=True,
        ...     sync_crawl__items[0]__dir_path="output/cas123"
        ... )
    """
    
    def __init__(
        self,
        cfg_like: Union[dict, None] = None,
        *,
        cfg_like_excel: Union[BaseModel, Path, str, dict, None] = None,
        cfg_like_sync_crawl: Union[BaseModel, Path, str, dict, None] = None,
        cfg_like_webdriver_manager: Union[BaseModel, Path, str, dict, None] = None,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Pass-through 패턴 초기화 (xloto와 동일)
        
        Architecture:
            1. ConfigLoader가 모든 section 병합
            2. Runtime overrides 병합
            3. SectionExtractor.extract_batch()로 Excel section 추출
            4. SyncCrawl에 전체 cfg_like + 개별 cfg_like 전달
        
        Args:
            cfg_like: 병합된 dict (ConfigLoader.to_dict() 결과)
            cfg_like_excel: ExcelLoadPolicy 개별 설정 (우선순위 1)
            cfg_like_sync_crawl: SyncCrawlPolicy 개별 설정
            cfg_like_webdriver_manager: WebDriverManagerPolicy 개별 설정
            log_manager: LogManager 인스턴스
            **overrides: 런타임 오버라이드
        
        Cascading Priority:
            1. cfg_like_excel (개별 cfg_like) - 최우선
            2. cfg_like["excel"] (병합 dict의 section)
            3. None (Pydantic 기본값)
        
        Note:
            ⚠️ SyncCrawl은 전체 cfg_like를 받아 내부에서 section 추출
            ⚠️ 불필요한 section이 SyncCrawl에 전달되어도 무시됨 (영향 미미)
            ⚠️ cfg_like_webdriver_manager는 SyncCrawl 내부 WebDriverManager에 전달
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
        # SectionExtractor.extract_batch() (Excel + SyncCrawl section 추출)
        # ========================================
        extracted = SectionExtractor.extract_batch(
            merged_config=merged_config,
            individual_cfgs={
                ExcelLoadPolicy: cfg_like_excel,
                SyncCrawlPolicy: cfg_like_sync_crawl,
            }
        )
        
        # Policy.name으로 추출
        self._cfg_excel = extracted[
            SectionExtractor.get_policy_name(ExcelLoadPolicy)
        ]
        self._cfg_sync_crawl = extracted[
            SectionExtractor.get_policy_name(SyncCrawlPolicy)
        ]
        
        # SyncCrawl에 전달할 cfg_like (전체 config + 개별 cfg_like)
        self._cfg_crawl = merged_config
        if cfg_like_sync_crawl:
            self._cfg_like_sync_crawl = cfg_like_sync_crawl
        if cfg_like_webdriver_manager:
            self._cfg_like_webdriver_manager = cfg_like_webdriver_manager
        
        # ========================================
        # CashopBasePolicy 생성 (xlcrawl)
        # ========================================
        try:
            # merged_config에서 xlcrawl 섹션 추출
            xlcrawl_config = merged_config.get("xlcrawl", {})
            self.policy = CashopBasePolicy(**xlcrawl_config)
        except Exception as e:
            self.log.warning(f"Failed to create CashopBasePolicy from config: {e}")
            self.log.warning("Using default CashopBasePolicy (may cause errors)")
            raise  # ← Required field이므로 에러 발생시켜야 함
        
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
        self._excel_load: Optional[ExcelLoad] = None
        self._sync_crawl: Optional[SyncCrawl] = None
        self._cas_extractor: Optional[CasExtractor] = None
        self._excel_updater: Optional[ExcelUpdater] = None
        
        self.log.debug("XLCRAWL adapter initialized")
    
    # ==========================================================================
    # Lazy Loading Properties
    # ==========================================================================
    
    @property
    def excel_load(self) -> ExcelLoad:
        """ExcelLoad Adapter lazy-loading"""
        if self._excel_load is None:
            # ⚠️ 파일 경로는 run()에서 받음 (여기서는 생성 안 함)
            pass
        return self._excel_load  # type: ignore
    
    @property
    def sync_crawl(self) -> SyncCrawl:
        """SyncCrawl Adapter lazy-loading (xloto와 동일한 패턴)
        
        SyncCrawl에 전체 cfg_like + 개별 cfg_like 전달
        SyncCrawl이 내부에서 필요한 section 추출
        """
        if self._sync_crawl is None:
            self._sync_crawl = SyncCrawl(
                cfg_like=self._cfg_crawl,  # type: ignore
                log_manager=self._parent_log_manager,
            )
            self.log.debug("SyncCrawl adapter created")
        return self._sync_crawl
    
    @property
    def cas_extractor(self) -> CasExtractor:
        """CasExtractor Service lazy-loading
        
        ⚠️ include_download=True + download_empty=True: download 컬럼이 비어있을 때만 추출
        ⚠️ include_translation=False: translation 컬럼 조건 불필요 (crawl 전용)
        """
        if self._cas_extractor is None:
            self._cas_extractor = CasExtractor(
                include_download=True,  # ✅ download 조건 활성화
                download_empty=True,  # ✅ download가 비어있을 때만 추출
                include_translation=False  # ⚠️ Crawl은 translation 불필요
            )
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
        """XLCRAWL Pipeline 실행 (단일 파일 + 단일 시트)
        
        Pipeline Flow:
            1. ExcelLoadPolicy.files에서 파일 경로/시트명 가져오기
            2. open_workbook(files[0].file_path)
            3. get_worksheet(files[0].sheets[0], column_aliases)
            4. CasExtractor로 CAS No + URL 추출 (download 컬럼이 비어있을 때만)
            5. URL 리스트 생성 후 SyncCrawl 파이프라인 실행
            6. ExcelUpdater로 download 컬럼에 날짜 기록
        
        Filter Condition:
            ⚠️ download 컬럼이 비어있는 항목만 크롤링 (download.isna())
            ⚠️ 크롤링 완료 후 download 컬럼에 날짜 기록
        
        Result Structure:
            cas_results = [
                {
                    "cas_no": str,
                    "url": str,
                    "download_row": int,  # Excel row (1-based + header)
                    "download_col": str,  # download 컬럼명
                    "success": bool,
                    "crawl_result": dict
                },
                ...
            ]
        
        Args:
            **overrides: 런타임 오버라이드
                sync_crawl__items[0]__dir_path="output/cas123"
        
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
            >>> xlcrawl = XlCrawl(cfg_like=config.to_dict())
            >>> result = xlcrawl.run(
            ...     sync_crawl__items[0]__dir_path="output/test"
            ... )
        """
        self.log.info("="*80)
        self.log.info("XLCRAWL Pipeline Started")
        self.log.info("="*80)
        
        result = {
            "success": False,
            "total_cas": 0,
            "processed_cas": 0,
            "cas_results": [],
            "error": None
        }
        
        try:
            # =============================================
            # 1️⃣ Excel 파일 열기 + 워크시트 가져오기
            # =============================================
            self.log.info("\n1️⃣ Excel Load: Opening workbook and getting worksheet")
            
            # ExcelLoad 초기화
            self._excel_load = ExcelLoad(
                cfg_like=self._cfg_excel, # type: ignore
                log_manager=self._parent_log_manager
            )
            
            # ExcelLoadPolicy에서 파일 경로 가져오기
            excel_policy = self._excel_load.policy
            if not excel_policy.files or len(excel_policy.files) == 0:
                raise ValueError("ExcelLoadPolicy.files is empty. Please configure files in excel config.")
            
            file_config = excel_policy.files[0]  # 첫 번째 파일 사용
            excel_file_path = file_config.file_path
            if not excel_file_path:
                raise ValueError("ExcelLoadPolicy.files[0].file_path is None. Please configure file_path.")
            
            self.log.info(f"   📁 Excel File: {excel_file_path}")
            
            if not file_config.sheets or len(file_config.sheets) == 0:
                raise ValueError("ExcelLoadPolicy.files[0].sheets is empty. Please configure sheets.")
            
            sheet_config = file_config.sheets[0]  # 첫 번째 시트 사용
            sheet_name = sheet_config.sheet_name
            column_aliases = sheet_config.get_column_aliases()
            
            self.log.info(f"   📊 Sheet: {sheet_name}")
            self.log.info(f"   🔖 Column Aliases: {list(column_aliases.keys()) if column_aliases else 'None'}")
            
            # Context manager를 사용하여 Excel 파일 열기
            with self._excel_load:
                # Workbook 열기
                workbook = self._excel_load.open_workbook(file_path=str(excel_file_path))
                self.log.info(f"   ✅ Workbook opened")
                
                # Worksheet 가져오기
                worksheet = self._excel_load.get_worksheet(
                    workbook,
                    sheet_name=sheet_name,
                    column_aliases=column_aliases if column_aliases else None
                )
                
                df = worksheet.to_dataframe(used_range=True, header=True, index=False)
                self.log.info(f"   ✅ Worksheet loaded: {len(df)} rows, {len(df.columns)} columns")
            
            # =============================================
            # 2️⃣ CAS No + URL 추출 (download 컬럼이 비어있을 때만)
            # =============================================
            self.log.info("\n2️⃣ CAS & URL Extraction: Finding CAS numbers and URLs from DataFrame")
            self.log.info("   ⚠️ Filter: download 컬럼이 비어있는 항목만 추출")
            
            # XwWs의 column_resolver 확인
            if worksheet.column_resolver is None:
                raise ValueError("XwWs.column_resolver is None (preset not configured)")
            
            # CAS No + URL 추출 (CasExtractor 사용)
            cas_results = self.cas_extractor.extract(
                df=df,
                column_resolver=worksheet.column_resolver,
                cas_key="cas",
                download_key="download",
                translation_key="translation"
            )
            
            # CasExtractor는 translation_row/col을 반환하므로 download_row/col로 변경
            for cas_item in cas_results:
                cas_item["download_row"] = cas_item.pop("translation_row")
                cas_item["download_col"] = cas_item.pop("translation_col")
            
            # URL 컬럼 추출 (column_resolver 사용)
            url_col = worksheet.column_resolver.resolve(df, "url")
            if not url_col:
                self.log.warning("   ⚠️ URL column not found. URLs will not be extracted.")
            else:
                # 각 CAS 결과에 URL 추가
                for cas_item in cas_results:
                    row_idx = cas_item["download_row"] - 2  # Excel row to DataFrame index
                    if row_idx < len(df):
                        url_value = df.iloc[row_idx].get(url_col)
                        cas_item["url"] = str(url_value).strip() if pd.notna(url_value) else None
                    else:
                        cas_item["url"] = None
            
            result["total_cas"] = len(cas_results)
            self.log.info(f"   ✅ Extracted {result['total_cas']} CAS numbers (with URLs)")
            
            if result["total_cas"] == 0:
                self.log.warning("   ⚠️ No CAS numbers found. Pipeline stopped.")
                result["success"] = True
                return result
            
            # =============================================
            # 3️⃣ SyncCrawl 파이프라인 실행 (URL 리스트 방식)
            # =============================================
            self.log.info("\n3️⃣ SyncCrawl Pipeline: Crawling data with URL list")
            
            # URL 리스트 생성 (Excel에서 추출한 URL 사용)
            url_list = []
            cas_to_url_map = {}  # CAS No -> URL 매핑
            
            for cas_item in cas_results:
                cas_no = cas_item["cas_no"]
                url = cas_item.get("url")
                
                if url:
                    url_list.append(url)
                    cas_to_url_map[url] = cas_no
                    self.log.debug(f"   Added URL for CAS {cas_no}: {url}")
                else:
                    self.log.warning(f"   ⚠️ No URL found for CAS {cas_no}, skipping")
            
            if not url_list:
                self.log.warning("   ⚠️ No valid URLs found. Pipeline stopped.")
                result["success"] = True
                return result
            
            self.log.info(f"   📋 Total URLs to crawl: {len(url_list)}")
            
            # SyncCrawl 실행 (URL 리스트 전체 전달)
            try:
                # Runtime override: 출력 디렉토리 설정
                crawl_overrides = {
                    "sync_crawl__items[0]__dir_path": str(self.policy.paths.output_dir)
                }
                
                # SyncCrawl 실행 (URL 리스트)
                crawl_result = self.sync_crawl.run(
                    urls=url_list,  # ✅ URL 리스트 전달
                    **crawl_overrides,
                    **overrides  # 외부 override 병합
                )
                
                # 결과를 CAS별로 매핑
                processed_count = 0
                
                # crawl_result가 dict인 경우 (단일 결과)
                if isinstance(crawl_result, dict):
                    success = crawl_result.get("success", False)
                    for cas_item in cas_results:
                        cas_item["crawl_result"] = crawl_result
                        cas_item["success"] = success
                        if success:
                            processed_count += 1
                
                # crawl_result가 list인 경우 (URL별 결과)
                elif isinstance(crawl_result, list):
                    for idx, item_result in enumerate(crawl_result):
                        if idx < len(url_list):
                            url = url_list[idx]
                            cas_no = cas_to_url_map.get(url)
                            
                            # CAS 결과에 크롤링 결과 추가
                            for cas_item in cas_results:
                                if cas_item["cas_no"] == cas_no:
                                    cas_item["crawl_result"] = item_result
                                    cas_item["success"] = item_result.get("success", False)
                                    if cas_item["success"]:
                                        processed_count += 1
                                        self.log.info(f"   ✅ CAS {cas_no} crawled successfully")
                                    else:
                                        self.log.warning(f"   ⚠️ CAS {cas_no} crawl failed")
                                    break
                
                result["processed_cas"] = processed_count
                result["cas_results"] = cas_results
                
                self.log.info(f"\n   ✅ SyncCrawl completed: {processed_count}/{len(url_list)} successful")
                
            except Exception as e:
                self.log.error(f"   ❌ SyncCrawl failed: {e}")
                # 모든 CAS를 실패로 마킹
                for cas_item in cas_results:
                    cas_item["success"] = False
                    cas_item["error"] = str(e)
                result["cas_results"] = cas_results
            
            # =============================================
            # 4️⃣ Excel 업데이트 (download 컬럼에 날짜 채움)
            # =============================================
            self.log.info("\n4️⃣ Excel Update: Writing download date back to Excel")
            
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # ExcelUpdater는 translation_row/col을 사용하므로 매핑
            for cas_item in cas_results:
                if cas_item.get("success"):
                    # download_row/col → translation_row/col (ExcelUpdater API)
                    cas_item["translation_row"] = cas_item["download_row"]
                    cas_item["translation_col"] = cas_item["download_col"]
            
            # ExcelUpdater 사용
            updated_count = self.excel_updater.update(
                worksheet=worksheet,
                cas_results=cas_results,
                date_value=current_date
            )
            
            self.log.info(f"   ✅ Updated {updated_count} rows (download column filled)")
            
            # =============================================
            # 5️⃣ Excel 저장 및 종료
            # =============================================
            # Context manager로 자동 close (with 블록 종료 시)
            
            result["success"] = True
            self.log.info("\n" + "="*80)
            self.log.info("✅ XLCRAWL Pipeline Completed Successfully")
            self.log.info("="*80)
            
        except Exception as e:
            self.log.error(f"\n❌ XLCRAWL Pipeline Failed: {e}")
            result["error"] = str(e)
            # Context manager가 자동으로 close 처리
        
        return result
    
    def __enter__(self):
        """Context Manager: with문 지원"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager: 종료 시 정리"""
        # SyncCrawl cleanup (브라우저 종료 등)
        if self._sync_crawl:
            try:
                pass  # SyncCrawl이 자체적으로 cleanup 처리
            except:
                pass
