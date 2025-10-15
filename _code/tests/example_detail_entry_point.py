# -*- coding: utf-8 -*-
"""
DetailEntryPoint 사용 예제

이 스크립트는 실제 상황에서 DetailEntryPoint를 사용하는 방법을 보여줍니다.

사용법:
    python scripts/example_detail_entry_point.py

설정:
    - config/detail_crawl_example.yaml에서 정책 설정
"""

import asyncio
from pathlib import Path

from crawl_utils import (
    DetailEntryPoint,
    create_webdriver,
    FirefoxPolicy,
    CrawlPolicy,
    NavigationPolicy,
    WaitPolicy,
    ExtractorPolicy,
    StoragePolicy,
    StorageTargetPolicy,
    WaitHook,
    WaitCondition,
    ExtractorType,
)
from crawl_utils.services import SeleniumBrowserAdapter, SeleniumNavigator


async def example_taobao():
    """타오바오 상품 상세페이지 크롤링 예제"""
    print("=" * 60)
    print("예제 1: 타오바오 상품 상세페이지 크롤링")
    print("=" * 60 + "\n")
    
    # 1. Firefox Policy 설정
    firefox_policy = FirefoxPolicy(
        headless=False,  # 브라우저 화면 보기
        window_size=(1440, 900),
    )
    
    # 2. Crawl Policy 설정
    crawl_policy = CrawlPolicy(
        # Navigation (상세페이지는 URL을 직접 전달하므로 base_url은 더미)
        navigation=NavigationPolicy(
            base_url="https://world.taobao.com",
        ),
        
        # Wait: 상품 이미지가 로드될 때까지 대기
        wait=WaitPolicy(
            hook=WaitHook.CSS,
            selector=".ItemPictures--root--jjVKCp9",  # 타오바오 이미지 컨테이너
            timeout_sec=10.0,
            condition=WaitCondition.PRESENCE,
        ),
        
        # Extractor: JS로 데이터 추출
        extractor=ExtractorPolicy(
            type=ExtractorType.JS,
            js_snippet="""
                // 타오바오 상품 정보 추출
                return {
                    // 메인 이미지
                    main_image: document.querySelector('.ItemPictures--mainPic--rcLNaCv img')?.src || '',
                    
                    // 상세 이미지들
                    detail_images: Array.from(
                        document.querySelectorAll('.ItemPictures--thumbImg--rQ8wHoc img')
                    ).map(img => img.src),
                    
                    // 상품명
                    title: document.querySelector('.ItemTitle--mainTitle--VHqDSLT')?.innerText || '',
                    
                    // 가격
                    price: document.querySelector('.Price--priceText--V8iGdOv')?.innerText || '',
                    
                    // 옵션들
                    options: Array.from(
                        document.querySelectorAll('.SkuItem--skuItemTitle--KNdB6YV')
                    ).map(opt => opt.innerText),
                };
            """,
        ),
        
        # Storage: 이미지와 텍스트 분리 저장
        storage=StoragePolicy(
            image=StorageTargetPolicy(
                base_dir=Path("output/taobao_detail"),
                sub_dir="images",
                extension="jpg",
                ensure_unique=True,
            ),
            text=StorageTargetPolicy(
                base_dir=Path("output/taobao_detail"),
                sub_dir="texts",
                extension="txt",
                ensure_unique=True,
            ),
        ),
    )
    
    # 3. WebDriver 생성
    driver = create_webdriver(firefox_policy)
    
    try:
        # 4. Browser Adapter & Navigator 생성
        async with SeleniumBrowserAdapter(driver) as browser:
            navigator = SeleniumNavigator(browser, crawl_policy)
            
            # 5. DetailEntryPoint 생성
            entry_point = DetailEntryPoint(navigator, crawl_policy)
            
            # 6. 크롤링 실행
            url = "https://world.taobao.com/item/123456.htm"  # 실제 URL로 변경 필요
            print(f"📌 크롤링 대상: {url}\n")
            
            summary = await entry_point.run(
                url=url,
                product_id="taobao_example",
            )
            
            # 7. 결과 출력
            print("\n" + "=" * 60)
            print("크롤링 결과")
            print("=" * 60)
            print(f"총 저장: {len(summary.flatten())}개 파일")
            print(f"  - 이미지: {len(summary['image'])}개")
            print(f"  - 텍스트: {len(summary['text'])}개")
            print(f"  - 파일: {len(summary['file'])}개")
            
            print("\n📁 저장된 파일:")
            for artifact in summary.flatten():
                if artifact.status == "saved":
                    print(f"  ✅ {artifact.path}")
            
    finally:
        driver.quit()


async def example_minimal():
    """최소 설정으로 간단하게 사용하는 예제"""
    print("\n" + "=" * 60)
    print("예제 2: 최소 설정 크롤링")
    print("=" * 60 + "\n")
    
    # 최소 설정
    firefox_policy = FirefoxPolicy()
    
    crawl_policy = CrawlPolicy(
        navigation=NavigationPolicy(base_url="https://example.com"),
        storage=StoragePolicy(
            image=StorageTargetPolicy(base_dir=Path("output/minimal/images")),
            text=StorageTargetPolicy(base_dir=Path("output/minimal/texts")),
        ),
    )
    
    driver = create_webdriver(firefox_policy)
    
    try:
        async with SeleniumBrowserAdapter(driver) as browser:
            navigator = SeleniumNavigator(browser, crawl_policy)
            entry_point = DetailEntryPoint(navigator, crawl_policy)
            
            # 간단한 JS snippet
            crawl_policy.extractor.type = ExtractorType.JS
            crawl_policy.extractor.js_snippet = """
                return {
                    title: document.title,
                    images: Array.from(document.querySelectorAll('img')).map(img => img.src).slice(0, 5),
                };
            """
            
            url = "https://example.com"  # 실제 URL로 변경
            print(f"📌 크롤링 대상: {url}\n")
            
            summary = await entry_point.run(url, product_id="minimal_example")
            
            print(f"\n✅ 저장 완료: {len(summary.flatten())}개 파일")
            
    finally:
        driver.quit()


async def example_with_config_file():
    """YAML 설정 파일 사용 예제"""
    print("\n" + "=" * 60)
    print("예제 3: YAML 설정 파일 사용")
    print("=" * 60 + "\n")
    
    from cfg_utils import ConfigLoader
    
    # YAML 파일에서 정책 로드
    config_path = Path("configs/detail_crawl_example.yaml")
    
    if not config_path.exists():
        print(f"⚠️ 설정 파일이 없습니다: {config_path}")
        print("   스킵합니다.")
        return
    
    loader = ConfigLoader(config_path)
    crawl_policy = loader.as_model(CrawlPolicy)
    
    firefox_policy = FirefoxPolicy()
    driver = create_webdriver(firefox_policy)
    
    try:
        async with SeleniumBrowserAdapter(driver) as browser:
            navigator = SeleniumNavigator(browser, crawl_policy)
            entry_point = DetailEntryPoint(navigator, crawl_policy)
            
            url = "https://example.com"
            summary = await entry_point.run(url)
            
            print(f"✅ 저장 완료: {len(summary.flatten())}개 파일")
            
    finally:
        driver.quit()


async def main():
    """메인 실행"""
    print("\n" + "🚀" * 30)
    print("DetailEntryPoint 사용 예제")
    print("🚀" * 30 + "\n")
    
    # 주의: 실제 URL이 필요합니다
    print("⚠️ 주의: 이 예제는 실제 URL이 필요합니다.")
    print("   example_taobao(), example_minimal()의 URL을 실제 URL로 변경하세요.\n")
    
    # 원하는 예제를 주석 해제하여 실행
    # await example_taobao()
    # await example_minimal()
    # await example_with_config_file()
    
    print("✅ 예제 완료!")
    print("\n💡 사용 팁:")
    print("   1. firefox_policy로 브라우저 설정 (headless, window_size 등)")
    print("   2. crawl_policy.wait로 대기 조건 설정 (CSS/XPath selector)")
    print("   3. crawl_policy.extractor.js_snippet으로 데이터 추출")
    print("   4. SmartNormalizer가 자동으로 타입 추론 및 정규화")
    print("   5. FileSaver가 자동으로 파일 저장 (이미지/텍스트 분리)")


if __name__ == "__main__":
    asyncio.run(main())
