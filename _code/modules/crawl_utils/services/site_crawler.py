"""
사이트별 크롤링 Service

SRP: 사이트별 크롤링 실행만 담당
- 검색 결과 크롤링
- 상세 페이지 크롤링
- 배치 처리

Dependencies:
- CrawlPipeline: 크롤링 파이프라인
- create_webdriver: WebDriver 생성
- ConfigLoader: 설정 로드
"""

from pathlib import Path
from typing import List, Dict, Optional
import logging

from crawl_utils.core.pipeline import CrawlPipeline
from crawl_utils.core.runner import SyncCrawlRunner
from crawl_utils.core.policy import CrawlPolicy
from crawl_utils.provider.factory import create_webdriver
from cfg_utils import ConfigLoader


logger = logging.getLogger(__name__)


class SiteCrawler:
    """
    사이트별 크롤링 Service
    
    Responsibility: 사이트별 검색/상세 크롤링 실행
    
    Example:
        >>> crawler = SiteCrawler("taobao")
        >>> output_dir = crawler.crawl_search("nike shoes", max_pages=2)
        >>> result = crawler.crawl_detail("https://item.taobao.com/...")
    """
    
    def __init__(self, site: str, browser: str = "firefox"):
        """
        Args:
            site: 사이트 이름 ('taobao', 'aliexpress', '1688')
            browser: 브라우저 종류 ('firefox', 'chrome')
        """
        self.site = site
        self.browser = browser
        self.loader = ConfigLoader()
    
    def crawl_search(
        self,
        query: str,
        max_pages: int = 2,
        verbose: bool = True
    ) -> Path:
        """
        검색 결과 크롤링 (Step 1)
        
        Args:
            query: 검색어
            max_pages: 최대 페이지 수
            verbose: 로그 출력 여부
            
        Returns:
            출력 디렉토리 경로
            
        Raises:
            FileNotFoundError: 설정 파일이 없는 경우
            RuntimeError: 크롤링 실패 시
        """
        if verbose:
            logger.info(f"[{self.site.upper()}] 검색 크롤링 시작")
            logger.info(f"검색어: {query} | 최대 페이지: {max_pages}")
        
        # 설정 로드
        crawl_config = Path(f"configs/crawl_{self.site}_search.yaml")
        driver_config = Path(f"configs/firefox_{self.site}.yaml")
        
        if not crawl_config.exists():
            raise FileNotFoundError(f"설정 파일 없음: {crawl_config}")
        if not driver_config.exists():
            raise FileNotFoundError(f"설정 파일 없음: {driver_config}")
        
        # Policy 로드 및 설정
        policy = self._load_crawl_policy(crawl_config)
        policy.navigation.params["query"] = query
        policy.navigation.max_pages = max_pages
        
        # 크롤링 실행
        summary = self._execute_crawl(policy, driver_config)
        
        if verbose:
            logger.info(f"✅ 완료: {summary.total_records}개 상품")
        
        return Path(f"_output/{self.site}/search")
    
    def crawl_detail(
        self,
        url: str,
        verbose: bool = True
    ) -> Dict[str, int]:
        """
        상세 페이지 크롤링 (Step 2)
        
        Args:
            url: 상품 상세 URL
            verbose: 로그 출력 여부
            
        Returns:
            크롤링 결과 {'images': 개수, 'texts': 개수}
            
        Raises:
            FileNotFoundError: 설정 파일이 없는 경우
            RuntimeError: 크롤링 실패 시
        """
        # 설정 로드
        crawl_config = Path(f"configs/crawl_{self.site}_detail.yaml")
        driver_config = Path(f"configs/firefox_{self.site}.yaml")
        
        if not crawl_config.exists():
            raise FileNotFoundError(f"설정 파일 없음: {crawl_config}")
        if not driver_config.exists():
            raise FileNotFoundError(f"설정 파일 없음: {driver_config}")
        
        # Policy 로드 및 설정
        policy = self._load_crawl_policy(crawl_config)
        policy.navigation.url_template = url
        
        # 크롤링 실행
        summary = self._execute_crawl(policy, driver_config)
        
        result = {
            'images': len(summary.artifacts.get('image', [])),
            'texts': len(summary.artifacts.get('text', []))
        }
        
        if verbose:
            logger.info(f"이미지: {result['images']}, 텍스트: {result['texts']}")
        
        return result
    
    def crawl_detail_batch(
        self,
        urls: List[str],
        verbose: bool = True
    ) -> Dict[str, int]:
        """
        상세 페이지 배치 크롤링
        
        Args:
            urls: 상품 URL 리스트
            verbose: 로그 출력 여부
            
        Returns:
            전체 결과 {'total_images': 개수, 'total_texts': 개수, 'processed': 개수}
        """
        if verbose:
            logger.info(f"[{self.site.upper()}] 배치 크롤링 시작: {len(urls)}개")
        
        total_images = 0
        total_texts = 0
        processed = 0
        
        for idx, url in enumerate(urls, 1):
            try:
                if verbose:
                    logger.info(f"[{idx}/{len(urls)}] {url[:50]}...")
                
                result = self.crawl_detail(url, verbose=False)
                
                total_images += result['images']
                total_texts += result['texts']
                processed += 1
                
                if verbose:
                    logger.info(f"  ✓ 이미지: {result['images']}, 텍스트: {result['texts']}")
                
            except Exception as e:
                logger.error(f"  ✗ 실패: {e}")
                continue
        
        result = {
            'total_images': total_images,
            'total_texts': total_texts,
            'processed': processed,
            'failed': len(urls) - processed
        }
        
        if verbose:
            logger.info(f"✅ 완료: 이미지 {total_images}개, 텍스트 {total_texts}개")
            logger.info(f"처리: {processed}/{len(urls)}개")
        
        return result
    
    # ========== Private Methods ==========
    
    def _load_crawl_policy(self, config_path: Path) -> CrawlPolicy:
        """크롤링 Policy 로드"""
        return self.loader.load_as_model(str(config_path), CrawlPolicy)
    
    def _execute_crawl(self, policy: CrawlPolicy, driver_config: Path):
        """크롤링 실행 (WebDriver 생성 → Pipeline 실행 → 종료)"""
        driver = create_webdriver(self.browser, str(driver_config))
        
        try:
            pipeline = CrawlPipeline(navigator=driver, policy=policy)
            runner = SyncCrawlRunner(pipeline)
            summary = runner.run()
            return summary
            
        finally:
            driver.close()
            logger.debug("세션 저장 완료")
