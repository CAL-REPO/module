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
        cfg_like_base: Union[BaseModel, Path, str, dict, None] = None,
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
            3. SectionExtractor.extract_batch()로 모든 section 추출
            4. SyncCrawl에 전체 cfg_like + 개별 cfg_like 전달
        
        Args:
            cfg_like: 병합된 dict (ConfigLoader.to_dict() 결과)
            cfg_like_base: CashopBasePolicy 개별 설정 (우선순위 1)
            cfg_like_excel: ExcelLoadPolicy 개별 설정 (우선순위 1)
            cfg_like_sync_crawl: SyncCrawlPolicy 개별 설정
            cfg_like_webdriver_manager: WebDriverManagerPolicy 개별 설정
            log_manager: LogManager 인스턴스
            **overrides: 런타임 오버라이드
        
        Cascading Priority:
            1. cfg_like_base (개별 cfg_like) - 최우선
            2. cfg_like["xlcrawl"] (병합 dict의 section)
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
        # SectionExtractor.extract_batch() (모든 Policy section 추출)
        # ========================================
        extracted = SectionExtractor.extract_batch(
            merged_config=merged_config,
            individual_cfgs={
                CashopBasePolicy: cfg_like_base,
                ExcelLoadPolicy: cfg_like_excel,
                SyncCrawlPolicy: cfg_like_sync_crawl,
            }
        )
        
        # Policy.name으로 추출
        base_policy_data = extracted[
            SectionExtractor.get_policy_name(CashopBasePolicy)
        ]
        self.policy: CashopBasePolicy = CashopBasePolicy(**base_policy_data) if isinstance(base_policy_data, dict) else base_policy_data  # type: ignore
        
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
        """XLCRAWL Pipeline 실행 (단일 파일 + 단일 시트)
        
        Pipeline Flow:
            1. ExcelLoadPolicy.files에서 파일 경로/시트명 가져오기
            2. open_workbook(files[0].file_path)
            3. get_worksheet(files[0].sheets[0], column_aliases)
            4. CasExtractor로 CAS No + URL 추출 (download 컬럼이 비어있을 때만)
            5. 각 CAS No별로 SyncCrawl 파이프라인 실행 (1개씩 처리)
            6. ExcelUpdater로 download 컬럼에 날짜 기록
        
        Filter Condition:
            ⚠️ download 컬럼이 비어있는 항목만 크롤링 (download.isna())
            ⚠️ 크롤링 완료 후 download 컬럼에 날짜 기록
        
        Crawl Strategy:
            ⚠️ URL을 1개씩 처리 (batch 아님)
            ⚠️ 각 CAS No별 디렉토리 생성: {output_dir}/{cas_no}/original/
            ⚠️ xloto와 동일한 폴더 구조 (CAS No가 상위 폴더명)
        
        Result Structure:
            cas_results = [
                {
                    "cas_no": str,
                    "url": str,
                    "download_row": int,  # Excel row (1-based + header)
                    "download_col": str,  # download 컬럼명
                    "success": bool,
                    "crawl_result": dict,
                    "error": Optional[str]
                },
                ...
            ]
        
        Args:
            **overrides: 런타임 오버라이드
                sync_crawl__items[0]__dir_path="output/cas123"
                (각 CAS별로 자동 설정되므로 일반적으로 불필요)
        
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
            >>> result = xlcrawl.run()
            >>> # CAS별 폴더 생성: output/123-45-6/original/
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
            
            # Context manager를 사용하여 Excel 파일 열기 (전체 파이프라인 포함)
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
                # download가 비어있을 때만 추출 (download_must_be_empty=True)
                cas_results = self.cas_extractor.extract(
                    df=df,
                    column_resolver=worksheet.column_resolver,
                    cas_key="cas",
                    download_key="download",
                    download_must_be_empty=True
                )
                
                # URL 컬럼 추출 (column_resolver 사용)
                url_col = worksheet.column_resolver.resolve(df, "url")
                if not url_col:
                    self.log.warning("   ⚠️ URL column not found. URLs will not be extracted.")
                else:
                    # 각 CAS 결과에 URL 추가
                    for cas_item in cas_results:
                        row_idx = cas_item["cas_row"] - 2  # Excel row to DataFrame index
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
                # 3️⃣ SyncCrawl 파이프라인 실행 (URL 1개씩 처리)
                # =============================================
                self.log.info("\n3️⃣ SyncCrawl Pipeline: Crawling each URL individually")
                
                processed_count = 0
                
                # ✅ 컨텍스트 매니저: 브라우저 재사용
                with self.sync_crawl:
                    # 각 CAS No + URL을 1개씩 처리
                    for idx, cas_item in enumerate(cas_results, start=1):
                        cas_no = cas_item["cas_no"]
                        url = cas_item.get("url")
                        
                        self.log.info(f"\n   [{idx}/{len(cas_results)}] Processing CAS: {cas_no}")
                        
                        if not url:
                            self.log.warning(f"   ⚠️ No URL found for CAS {cas_no}, skipping")
                            cas_item["success"] = False
                            cas_item["error"] = "URL not found"
                            continue
                        
                        self.log.info(f"   📋 URL: {url[:80]}..." if len(url) > 80 else f"   📋 URL: {url}")
                        
                        try:
                            # CAS No별 디렉토리 생성 (xloto와 동일한 구조)
                            cas_download_dir = Path(self.policy.paths.public_img_dir) / cas_no / self.policy.paths.origin_dirname
                            
                            # ⚠️ 이미 파일이 존재하면 Skip (크롤링 안 함)
                            if cas_download_dir.exists() and any(cas_download_dir.iterdir()):
                                self.log.info(f"   ⏭️  Files already exist in {cas_download_dir}, skipping crawl")
                                cas_item["success"] = True
                                cas_item["processed_count"] = 0  # 이미 완료됨
                                cas_item["skipped"] = True
                                processed_count += 1
                                continue
                            
                            # Runtime override: 각 CAS별 디렉토리 설정
                            crawl_overrides = {
                                "sync_crawl__items[0]__dir_path": cas_download_dir
                            }
                            
                            self.log.info(f"   📁 Output Dir: {cas_download_dir}")
                            
                            # SyncCrawl 실행 (단일 URL)
                            crawl_result = self.sync_crawl.run(
                                urls=[url],
                                **crawl_overrides,
                                **overrides
                            )
                            
                            cas_item["crawl_result"] = crawl_result
                            
                            # SyncCrawl.run() 항상 list 반환
                            if isinstance(crawl_result, list) and len(crawl_result) > 0:
                                first_result = crawl_result[0]
                                cas_item["success"] = first_result.get("success", False)
                                
                                if cas_item["success"]:
                                    saved_files = first_result.get("saved_files", [])
                                    cas_item["processed_count"] = len(saved_files)
                                else:
                                    cas_item["processed_count"] = 0
                            else:
                                cas_item["success"] = False
                                cas_item["processed_count"] = 0
                            
                            if cas_item["success"]:
                                processed_count += 1
                                if cas_item["processed_count"] > 0:
                                    self.log.info(f"   ✅ CAS {cas_no}: Crawled {cas_item['processed_count']} files")
                                else:
                                    self.log.info(f"   ✅ CAS {cas_no}: Crawl completed (no new files)")
                            else:
                                self.log.warning(f"   ❌ CAS {cas_no}: Crawl failed")
                        
                        except Exception as e:
                            self.log.error(f"   ❌ CAS {cas_no}: Exception - {e}")
                            cas_item["success"] = False
                            cas_item["processed_count"] = 0
                            cas_item["error"] = str(e)
                
                result["processed_cas"] = processed_count
                result["cas_results"] = cas_results
                
                self.log.info(f"\n   ✅ SyncCrawl completed: {processed_count}/{len(cas_results)} successful")
                
                # =============================================
                # 4️⃣ Excel 업데이트 (download 컬럼만 사용)
                # =============================================
                self.log.info("\n4️⃣ Excel Update: Writing download date to Excel")
                
                current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Download 컬럼명 가져오기
                download_col_name = worksheet.column_resolver.resolve(df, "download")
                
                if not download_col_name:
                    self.log.warning("   ⚠️ Download column not found, skipping Excel update")
                else:
                    # 모든 cas_item에 download_col 정보 설정
                    for cas_item in cas_results:
                        row = cas_item.get("cas_row")
                        if not row:
                            continue
                        
                        # processed_count > 0 또는 skipped=True인 경우만 업데이트
                        if (cas_item.get("success") and cas_item.get("processed_count", 0) > 0) or cas_item.get("skipped"):
                            cas_item["translation_row"] = row
                            cas_item["translation_col"] = download_col_name
                    
                    # ExcelUpdater 사용
                    updated_count = self.excel_updater.update(
                        worksheet=worksheet,
                        cas_results=cas_results,
                        date_value=current_date
                    )
                    
                    self.log.info(f"   ✅ Updated {updated_count} rows in download column")
                
                workbook.book.save()
                self.log.info("   ✅ Workbook saved")
                
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
