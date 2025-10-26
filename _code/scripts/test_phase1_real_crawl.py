"""
Phase 1: 실전 WebDriver 크롤링 테스트

테스트 목적:
1. WebDriver 연결 + URL 자동 분석
2. 실제 페이지 로드 및 스크롤
3. Extractor 데이터 추출
4. ItemPostProcessor v7.0 처리
5. 실제 파일 저장 확인
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, r"m:\CALife\CAShop - 구매대행\_code\modules")

# 환경변수 설정 (ConfigLoader용)
os.environ["CASHOP_PATHS"] = r"M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml"

from crawl_utils.adapter import SyncCrawl
from crawl_utils.presets import analyze_url, get_preset
from logs_utils import LogManager
from cfg_utils import ConfigLoader


def test_step1_webdriver_init():
    """Step 1: WebDriver 초기화 테스트"""
    print("\n" + "=" * 80)
    print("Step 1: WebDriver 초기화 테스트")
    print("=" * 80 + "\n")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service
        
        # Firefox 경로 설정
        options = Options()
        options.binary_location = r"C:\Program Files\Mozilla Firefox\firefox.exe"
        # Headless 모드 (백그라운드 실행)
        # options.add_argument("--headless")
        
        # geckodriver 경로 설정
        service = Service(executable_path=r"M:\WebDriver\geckodriver_win32.exe")
        
        driver = webdriver.Firefox(service=service, options=options)
        print("✅ WebDriver 초기화 성공 (Firefox)")
        
        # 간단한 테스트
        driver.get("https://www.aliexpress.com")
        print(f"✅ 페이지 로드 성공: {driver.title[:50]}...")
        
        driver.quit()
        print("✅ WebDriver 종료 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ WebDriver 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_step2_config_loader():
    """Step 2: ConfigLoader 설정 로드"""
    print("\n" + "=" * 80)
    print("Step 2: ConfigLoader 설정 로드")
    print("=" * 80 + "\n")
    
    try:
        # ConfigLoader 초기화
        config_path = Path(r"M:\CALife\CAShop - 구매대행\_code\configs\loader\config_loader_xloto.yaml")
        
        if not config_path.exists():
            print(f"⚠️  Config 파일 없음: {config_path}")
            print("   → cfg_like=None으로 진행 (Pydantic 기본값)")
            return None
        
        config = ConfigLoader(
            config_loader_cfg_path=str(config_path),
            env_os=["CASHOP_PATHS"]
        )
        
        print(f"✅ ConfigLoader 초기화 성공")
        
        # 설정 확인
        config_dict = config.to_dict()
        print(f"   Loaded sections: {list(config_dict.keys())}")
        
        return config_dict
        
    except Exception as e:
        print(f"⚠️  ConfigLoader 실패: {e}")
        print("   → cfg_like=None으로 진행")
        return None


def test_step3_url_analysis_with_preset():
    """Step 3: URL 분석 및 Preset 검증"""
    print("\n" + "=" * 80)
    print("Step 3: URL 분석 및 Preset 검증")
    print("=" * 80 + "\n")
    
    # 테스트 URL (실제 존재하는 상품)
    test_url = "https://www.aliexpress.com/item/1005006150568354.html"
    
    print(f"URL: {test_url}\n")
    
    # 1. URL 분석
    site, method, region = analyze_url(test_url)
    print(f"✅ URL 분석:")
    print(f"   site   = {site}")
    print(f"   method = {method}")
    print(f"   region = {region}")
    
    # 2. Preset 로드
    preset = get_preset(site, method)
    if preset:
        print(f"\n✅ Preset 로드 성공:")
        print(f"   Scroll: {preset['scroll']['strategy']} (max {preset['scroll']['max_scrolls']})")
        print(f"   Save Rules: {len(preset['save'])} rules")
        
        for i, rule in enumerate(preset['save'], 1):
            print(f"      {i}. {rule['kind']:6s} - {rule['source']}")
        
        return test_url, site, method, preset
    else:
        print(f"❌ Preset 없음")
        return None, None, None, None


def test_step4_sync_crawl_dry_run():
    """Step 4: SyncCrawl Dry Run (WebDriver 없이 Policy 생성)"""
    print("\n" + "=" * 80)
    print("Step 4: SyncCrawl Dry Run (Policy 생성 테스트)")
    print("=" * 80 + "\n")
    
    try:
        # LogManager 초기화
        log_mgr = LogManager(
            name="phase1_test",
            level="INFO",
            log_dir=Path("logs/phase1")
        )
        
        # ConfigLoader (선택적)
        cfg_dict = test_step2_config_loader()
        
        # SyncCrawl 초기화
        crawl = SyncCrawl(
            cfg_like=cfg_dict,
            log_manager=log_mgr
        )
        
        print("✅ SyncCrawl 초기화 성공")
        print(f"   Policy: {crawl.policy.__class__.__name__}")
        
        return crawl
        
    except Exception as e:
        print(f"❌ SyncCrawl 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_step5_real_crawl_minimal():
    """Step 5: 실전 크롤링 (최소 설정)"""
    print("\n" + "=" * 80)
    print("Step 5: 실전 크롤링 테스트 (WebDriver + URL 자동 분석)")
    print("=" * 80 + "\n")
    
    # WebDriver 경로 정보 출력
    print("🔧 WebDriver 설정:")
    print(f"   Firefox: C:\\Program Files\\Mozilla Firefox\\firefox.exe")
    print(f"   geckodriver: M:\\WebDriver\\geckodriver_win32.exe\n")
    
    try:
        # URL 준비
        test_url = "https://www.aliexpress.com/item/1005006150568354.html"
        
        # LogManager
        log_mgr = LogManager(
            name="phase1_crawl",
            level="DEBUG",
            log_dir=Path("logs/phase1")
        )
        
        # ConfigLoader 사용 (WebDriver 설정 포함)
        cfg_dict = None
        try:
            config_path = Path(r"M:\CALife\CAShop - 구매대행\_code\configs\loader\config_loader_xloto.yaml")
            if config_path.exists():
                config = ConfigLoader(
                    config_loader_cfg_path=str(config_path),
                    env_os=["CASHOP_PATHS"]
                )
                cfg_dict = config.to_dict()
                print("✅ ConfigLoader 로드 성공")
            else:
                print("⚠️  ConfigLoader 없음 → 기본 설정 사용")
        except Exception as e:
            print(f"⚠️  ConfigLoader 실패: {e}")
            print("   → 기본 설정 사용")
        
        # SyncCrawl 초기화
        crawl = SyncCrawl(cfg_like=cfg_dict, log_manager=log_mgr)
        
        print(f"📍 Target URL: {test_url}")
        print(f"📦 Output Dir: output/test_phase1\n")
        
        # Runtime Override (출력 디렉토리만 지정)
        output_base = Path("output/test_phase1")
        output_base.mkdir(parents=True, exist_ok=True)
        
        # 크롤링 실행
        print("🚀 크롤링 시작...\n")
        
        results = crawl.run(
            urls=[test_url],
            # URL 자동 분석 → site/method 자동 추출 → Preset 자동 로드
            # Override만 지정
            crawl__save__0__directory=str(output_base / "images"),
            crawl__save__1__directory=str(output_base / "texts"),
            crawl__save__2__directory=str(output_base / "sku"),
            crawl__save__3__directory=str(output_base / "sku_images"),
        )
        
        print("\n✅ 크롤링 완료!")
        
        # 결과 확인
        for i, result in enumerate(results, 1):
            print(f"\n📊 Result {i}:")
            print(f"   URL: {result.get('url', 'N/A')}")
            print(f"   Success: {result.get('success', False)}")
            
            if result.get('success'):
                saved_files = result.get('saved_files', [])
                print(f"   Saved Files: {len(saved_files)}")
                
                # 처음 5개만 출력
                for j, file_path in enumerate(saved_files[:5], 1):
                    print(f"      {j}. {file_path}")
                
                if len(saved_files) > 5:
                    print(f"      ... and {len(saved_files) - 5} more")
                
                # 파일 실제 존재 확인
                existing_count = sum(1 for f in saved_files if Path(f).exists())
                print(f"   ✅ 실제 저장된 파일: {existing_count}/{len(saved_files)}")
            else:
                print(f"   ❌ Error: {result.get('error', 'Unknown')}")
        
        return results
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자 중단 (Ctrl+C)")
        return None
        
    except Exception as e:
        print(f"\n❌ 크롤링 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_step6_validation():
    """Step 6: 최종 검증"""
    print("\n" + "=" * 80)
    print("Step 6: 최종 검증 체크리스트")
    print("=" * 80 + "\n")
    
    checks = []
    
    # 1. Output 디렉토리 확인
    output_base = Path("output/test_phase1")
    if output_base.exists():
        checks.append(("✅", "Output 디렉토리 생성됨"))
        
        # 하위 디렉토리 확인
        subdirs = ["images", "texts", "sku", "sku_images"]
        for subdir in subdirs:
            path = output_base / subdir
            if path.exists():
                file_count = len(list(path.glob("*")))
                checks.append(("✅", f"  {subdir}: {file_count} files"))
            else:
                checks.append(("⚠️ ", f"  {subdir}: 없음"))
    else:
        checks.append(("❌", "Output 디렉토리 없음"))
    
    # 2. 로그 확인
    log_dir = Path("logs/phase1")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        checks.append(("✅", f"로그 파일: {len(log_files)}개"))
    else:
        checks.append(("⚠️ ", "로그 디렉토리 없음"))
    
    # 출력
    for status, message in checks:
        print(f"{status} {message}")
    
    # 종합 판정
    print("\n" + "=" * 80)
    if all(status == "✅" for status, _ in checks):
        print("🎉 Phase 1 완전 성공!")
    else:
        print("⚠️  Phase 1 부분 성공 (일부 항목 확인 필요)")
    print("=" * 80)


if __name__ == "__main__":
    print("\n")
    print("=" * 80)
    print(" " * 20 + "Phase 1: 실전 WebDriver 크롤링 테스트")
    print("=" * 80)
    
    try:
        # Step 1: WebDriver 초기화 체크
        if not test_step1_webdriver_init():
            print("\n❌ WebDriver 사용 불가. Firefox 및 geckodriver 설치 확인 필요")
            print("   → pip install selenium")
            print("   → geckodriver 다운로드: https://github.com/mozilla/geckodriver/releases")
            sys.exit(1)
        
        # Step 3: URL 분석 및 Preset
        test_url, site, method, preset = test_step3_url_analysis_with_preset()
        
        if not preset:
            print("\n❌ Preset 로드 실패. v2.0 Preset이 등록되지 않았을 수 있음")
            sys.exit(1)
        
        # Step 4: SyncCrawl Dry Run
        crawl = test_step4_sync_crawl_dry_run()
        
        if not crawl:
            print("\n❌ SyncCrawl 초기화 실패")
            sys.exit(1)
        
        # Step 5: 실전 크롤링
        print("\n⚠️  실제 웹 페이지에 접속합니다. 계속하시겠습니까?")
        print("   (WebDriver 창이 열립니다. 중단하려면 Ctrl+C)")
        input("\n▶ Enter를 눌러 계속...")
        
        results = test_step5_real_crawl_minimal()
        
        if results:
            # Step 6: 검증
            test_step6_validation()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  테스트 중단됨")
    
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
