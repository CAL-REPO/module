# -*- coding: utf-8 -*-
"""
scripts/xlcrawl2.py
Excel 크롤링 자동화 스크립트 (crawl_utils 기존 구조 활용)

워크플로우:
1. 환경변수(CASHOP_PATHS)에서 paths.local.yaml 경로 획득
2. configs/excel.yaml, configs/xlcrawl.yaml 경로를 paths.local.yaml에서 참조
3. excel.yaml 정책에 따라 xl_utils로 Excel 파일 열기
4. DataFrame 추출
5. download 컬럼에서 날짜가 아닌 행 → URL 리스트 추가
6. crawl_utils.CrawlPipeline으로 크롤링 수행
7. download 열에 날짜 기입
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Any
import pandas as pd

# PYTHONPATH 기준 import
from xl_utils import XlController
from cfg_utils import ConfigLoader
from crawl_utils import CrawlPipeline, CrawlPolicy, StoragePolicy, FirefoxPolicy, create_webdriver
from crawl_utils.services.fetcher import HTTPFetcher
from crawl_utils.services.normalizer import DataNormalizer
from crawl_utils.services.saver import FileSaver
from structured_io.core.base_policy import BaseParserPolicy


def load_paths_config() -> dict:
    """환경변수에서 paths.local.yaml 경로 획득 및 로드
    
    Returns:
        paths 설정 dict
    
    Raises:
        ValueError: 환경변수가 설정되지 않은 경우
        FileNotFoundError: paths.local.yaml 파일이 없는 경우
    """
    # 1. 환경변수에서 경로 획득
    paths_env = os.getenv("CASHOP_PATHS")
    
    if not paths_env:
        raise ValueError(
            "환경변수 CASHOP_PATHS가 설정되지 않았습니다.\n"
            "PowerShell: $env:CASHOP_PATHS = 'M:\\CALife\\CAShop - 구매대행\\_code\\configs\\paths.local.yaml'"
        )
    
    paths_file = Path(paths_env)
    
    if not paths_file.exists():
        raise FileNotFoundError(f"paths.local.yaml 파일이 존재하지 않습니다: {paths_file}")
    
    # 2. ConfigLoader로 로드 (placeholder 활성화)
    yaml_policy = BaseParserPolicy(
        file_path=str(paths_file),
        enable_env=True,
        enable_placeholder=True,
        enable_reference=True,
        enable_include=False,
        default_section=None,
        encoding="utf-8",
        on_error="raise",
        safe_mode=True
    )
    loader = ConfigLoader(paths_file, yaml_policy=yaml_policy)
    paths_config = loader.as_dict()
    
    print(f"✅ paths.local.yaml 로드 완료: {paths_file}")
    return paths_config


def get_config_paths(paths_config: dict) -> Tuple[Path, Path]:
    """paths.local.yaml에서 excel.yaml, xlcrawl.yaml 경로 추출
    
    Args:
        paths_config: paths.local.yaml에서 로드된 설정
    
    Returns:
        (excel_config_path, xlcrawl_config_path)
    
    Raises:
        ValueError: configs 섹션이 없거나 필수 키가 없는 경우
        FileNotFoundError: 설정 파일이 존재하지 않는 경우
    """
    # base_path 추출
    base_path = Path(paths_config.get("base_path", "M:/CALife/CAShop - 구매대행/_code"))
    
    # configs 섹션에서 상대 경로 추출
    excel_yaml = base_path / paths_config.get("configs", {}).get("excel", "configs/excel.yaml")
    xlcrawl_yaml = base_path / paths_config.get("configs", {}).get("xlcrawl", "configs/xlcrawl.yaml")
    
    if not excel_yaml.exists():
        raise FileNotFoundError(f"excel.yaml이 존재하지 않습니다: {excel_yaml}")
    
    if not xlcrawl_yaml.exists():
        raise FileNotFoundError(f"xlcrawl.yaml이 존재하지 않습니다: {xlcrawl_yaml}")
    
    print(f"✅ excel.yaml: {excel_yaml}")
    print(f"✅ xlcrawl.yaml: {xlcrawl_yaml}")
    
    return excel_yaml, xlcrawl_yaml


def extract_urls_from_dataframe(df: pd.DataFrame, download_col: str = "download") -> List[Tuple[int, str]]:
    """DataFrame에서 download 컬럼이 날짜가 아닌 행의 URL 추출
    
    Args:
        df: Excel에서 추출한 DataFrame
        download_col: download 컬럼 이름
    
    Returns:
        [(행 인덱스, URL), ...] 리스트
    """
    url_list = []
    
    if download_col not in df.columns:
        print(f"⚠️  '{download_col}' 컬럼이 DataFrame에 없습니다")
        return url_list
    
    for idx, row in df.iterrows():
        value = row[download_col]
        
        # 날짜 형식이 아니고, 문자열이고, http로 시작하면 URL로 간주
        if pd.notna(value) and isinstance(value, str):
            # 날짜 패턴 체크 (YYYY-MM-DD, YYYY/MM/DD 등)
            if not any(sep in value for sep in ['-', '/', '.']):
                # http 또는 https로 시작하면 URL
                if value.startswith(('http://', 'https://')):
                    url_list.append((idx, value))
    
    print(f"✅ {len(url_list)}개의 URL 추출 완료")
    return url_list


def process_crawling(
    urls: List[Tuple[int, str]], 
    crawl_config: dict, 
    output_dir: Path
) -> Dict[int, dict]:
    """crawl_utils와 Firefox WebDriver를 사용한 크롤링 수행
    
    Args:
        urls: [(행 인덱스, URL), ...] 리스트
        crawl_config: xlcrawl.yaml의 xlcrawl 섹션
        output_dir: 이미지 저장 디렉토리
    
    Returns:
        {행 인덱스: 크롤링 결과} 딕셔너리
    """
    from image_utils import ImageDownloader, ImageDownloadPolicy
    
    results = {}
    
    try:
        # Firefox WebDriver 설정 로드
        firefox_config = crawl_config.get("firefox", {})
        
        print(f"🔧 Firefox WebDriver 초기화 중...")
        print(f"  - Headless: {firefox_config.get('headless', False)}")
        print(f"  - Window Size: {firefox_config.get('window_size', [1440, 900])}")
        print(f"  - Session Path: {firefox_config.get('session_path')}")
        
        # WebDriver 생성 (dict로 설정 전달)
        driver = create_webdriver("firefox", firefox_config)
        
        # ImageDownloader 생성
        download_policy = ImageDownloadPolicy(
            timeout=crawl_config.get("crawl", {}).get("timeout", 30),
            max_retries=crawl_config.get("crawl", {}).get("retry", 3),
            user_agent=crawl_config.get("crawl", {}).get("user_agent", "Mozilla/5.0")
        )
        downloader = ImageDownloader(download_policy)
        
        # JS snippet 로드
        extract_config = crawl_config.get("extract", {})
        js_snippet = extract_config.get("js_snippet", "return {};")
        
        print(f"  - JS Extract: {'✅ 설정됨' if js_snippet else '❌ 미설정'}")
        print(f"  - Image Downloader: ✅ 준비 완료")
        
        # 각 URL 크롤링
        for idx, url in urls:
            print(f"\n🌐 크롤링 중 [{idx}]: {url}")
            
            try:
                # 페이지 로드
                driver.driver.get(url)
                
                # 페이지 로딩 대기 (간단한 sleep)
                import time
                time.sleep(2)  # TODO: WebDriverWait 사용
                
                # JS extract 실행
                data = driver.driver.execute_script(js_snippet)
                
                if not isinstance(data, dict):
                    print(f"  ⚠️  JS extract 결과가 dict가 아님: {type(data)}")
                    data = {}
                
                # 추출된 데이터 확인
                title = data.get("title", "")
                price = data.get("price", "")
                images = data.get("images", [])
                
                print(f"  📝 Title: {title[:50]}..." if title else "  📝 Title: (없음)")
                print(f"  💰 Price: {price}")
                print(f"  🖼️  Images: {len(images)}개")
                
                # 이미지 다운로드
                downloaded_images = []
                if images:
                    save_dir = output_dir / f"product_{idx}"
                    download_results = downloader.download_many(
                        images,
                        save_dir,
                        prefix=f"product_{idx}"
                    )
                    
                    # 성공한 이미지만 수집
                    downloaded_images = [
                        r["path"] for r in download_results 
                        if r["status"] == "success"
                    ]
                
                # 결과 저장
                results[idx] = {
                    "url": url,
                    "status": "success",
                    "timestamp": datetime.now().isoformat(),
                    "title": title,
                    "price": price,
                    "images_count": len(downloaded_images),
                    "images_total": len(images),
                    "images": [str(p) for p in downloaded_images],
                    "data": data  # 전체 추출 데이터
                }
                
                print(f"  ✅ 성공: {len(downloaded_images)}/{len(images)}개 이미지 다운로드")
                
            except Exception as e:
                print(f"  ❌ 실패: {e}")
                import traceback
                traceback.print_exc()
                
                results[idx] = {
                    "url": url,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        # WebDriver 종료
        driver.quit()
        downloader.close()
        print(f"\n✅ Firefox WebDriver 종료")
        
    except Exception as e:
        print(f"❌ 크롤링 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    return results


def update_download_column(
    xl_controller: XlController, 
    df: pd.DataFrame,
    download_col: str,
    crawl_results: Dict[int, dict]
) -> None:
    """크롤링 성공한 행의 download 컬럼에 날짜 기입
    
    Args:
        xl_controller: XlController 인스턴스
        df: 원본 DataFrame
        download_col: download 컬럼 이름
        crawl_results: 크롤링 결과 딕셔너리
    """
    ws = xl_controller.get_worksheet()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # download 컬럼의 Excel 컬럼 인덱스 찾기
    col_idx = df.columns.get_loc(download_col) + 1  # Excel은 1-based
    
    updated_count = 0
    
    for row_idx, result in crawl_results.items():
        if result.get("status") == "success":
            # DataFrame의 row_idx를 Excel 행 번호로 변환 (헤더 고려)
            excel_row = row_idx + 2  # 1-based + header row
            
            # 날짜 기입
            ws.write_cell(excel_row, col_idx, today)
            updated_count += 1
    
    print(f"✅ {updated_count}개 행의 download 컬럼 업데이트 완료")


def main():
    """메인 워크플로우"""
    print("=" * 80)
    print("Excel 크롤링 자동화 스크립트 시작")
    print("=" * 80)
    
    try:
        # Step 1: CASHOP_PATHS 환경변수에서 paths.local.yaml 로드
        print("\n[Step 1] paths.local.yaml 로드")
        paths_config = load_paths_config()
        
        # Step 2: paths.local.yaml에서 excel.yaml, xlcrawl.yaml 경로 추출
        print("\n[Step 2] Excel 및 Crawl 설정 파일 경로 추출")
        excel_config_path, xlcrawl_config_path = get_config_paths(paths_config)
        
        # Step 3: xlcrawl.yaml 로드 (paths_config를 컨텍스트로 사용)
        print("\n[Step 3] xlcrawl.yaml 설정 로드")
        yaml_policy = BaseParserPolicy(
            file_path=str(xlcrawl_config_path),
            enable_placeholder=True,
            enable_reference=True,
            enable_env=False,
            enable_include=False,
            default_section=None,
            encoding="utf-8",
            on_error="raise",
            safe_mode=True
        )
        crawl_loader = ConfigLoader(xlcrawl_config_path, yaml_policy=yaml_policy)
        # paths_config를 먼저 로드한 컨텍스트로 사용
        crawl_config = crawl_loader.as_dict().get("xlcrawl", {})
        
        download_col = crawl_config.get("download_column", "download")
        output_dir = Path(crawl_config.get("image_save_dir", "output/images"))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"  - Download 컬럼: {download_col}")
        print(f"  - 이미지 저장 경로: {output_dir}")
        
        # Step 4: xl_utils로 Excel 파일 열기
        print("\n[Step 4] Excel 파일 열기")
        
        # paths_config에서 직접 Excel 파일 경로와 시트 이름 가져오기
        root_dir = paths_config.get("root", "M:/CALife/CAShop - 구매대행")
        excel_file_path = f"{root_dir}/01.All Product List.xlsx"
        sheet_name = paths_config.get("all_product_xl_file_sheet", "Purchase")
        
        print(f"  - Excel 파일: {excel_file_path}")
        print(f"  - 시트 이름: {sheet_name}")
        
        # XlController에 직접 경로 전달 (runtime override)
        with XlController(excel_config_path) as xl:
            ws = xl.get_worksheet(excel_path=excel_file_path, sheet_name=sheet_name)
            
            # Step 5: DataFrame 추출
            print("\n[Step 5] DataFrame 추출")
            df = ws.to_dataframe()
            print(f"  - DataFrame 크기: {df.shape}")
            print(f"  - 컬럼: {list(df.columns)}")
            
            # Step 6: download 컬럼에서 URL 추출
            print("\n[Step 6] URL 추출")
            urls = extract_urls_from_dataframe(df, download_col)
            
            if not urls:
                print("⚠️  크롤링할 URL이 없습니다")
                return
            
            # Step 7: 크롤링 수행
            print("\n[Step 7] 크롤링 수행")
            crawl_results = process_crawling(urls, crawl_config, output_dir)
            
            # Step 8: download 컬럼 업데이트
            print("\n[Step 8] download 컬럼 업데이트")
            update_download_column(xl, df, download_col, crawl_results)
        
        print("\n" + "=" * 80)
        print("✅ 모든 작업 완료")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
