"""
crawl.py
---------
CrawlRunner
 - URL만 초기화 시 주입
 - run(cfg_like | yamlPath) 시점에 정책 로드 및 병합 수행
"""

import asyncio
from pathlib import Path
from cfg_utils import PolicyLoader
from logs_utils import get_session_logger

from crawl_refactor.policy import CrawlPolicy
from crawl_refactor.pipeline import CrawlPipeline
from crawl_refactor.navigator import SeleniumNavigator
from crawl_refactor.fetcher import HTTPFetcher
from crawl_refactor.normalizer import DataNormalizer
from crawl_refactor.saver import StorageDispatcher


class CrawlRunner:
    """
    CrawlPipeline 엔트리포인트
    firefox.yaml (기본) + 사용자 정책(cfg_like 또는 yamlPath)을 병합 후 실행
    """

    def __init__(self, url: str, firefox_yaml: str = "firefox.yaml"):
        self.url = url
        self.firefox_yaml = firefox_yaml
        self.logger = get_session_logger(Path(url).stem or "crawl_session")

    async def run(self, cfg_like: dict | None = None, yamlPath: str | None = None):
        """
        cfg_like: dict 형태의 정책 (예: API 호출 등에서 전달)
        yamlPath: 사용자 지정 YAML 경로 (예: crawl.yaml)
        둘 중 하나만 입력하면 된다.
        """
        # -------------------
        # 1. 정책 로드 및 병합
        # -------------------
        if cfg_like and yamlPath:
            raise ValueError("cfg_like와 yamlPath는 동시에 지정할 수 없습니다.")

        if cfg_like:
            self.logger.info("🧩 merging firefox.yaml with dict override")
            merged_policy = PolicyLoader.load(
                base=self.firefox_yaml, override_dict=cfg_like, model=CrawlPolicy
            )
        elif yamlPath:
            self.logger.info("🧩 merging firefox.yaml with YAML override: {}", yamlPath)
            merged_policy = PolicyLoader.load(
                base=self.firefox_yaml, override=yamlPath, model=CrawlPolicy
            )
        else:
            self.logger.info("🧩 loading firefox.yaml only (no override)")
            merged_policy = PolicyLoader.load(base=self.firefox_yaml, model=CrawlPolicy)

        # URL override (최종 정책에 URL 주입)
        merged_policy.navigation.base_url = self.url
        self.policy = merged_policy

        # -------------------
        # 2. 구성 요소 초기화
        # -------------------
        self.logger.info("🚀 Starting CrawlPipeline for {}", self.url)
        navigator = SeleniumNavigator(policy=self.policy)
        fetcher = HTTPFetcher(policy=self.policy)
        normalizer = DataNormalizer(policy=self.policy)
        saver = StorageDispatcher(policy=self.policy)

        pipeline = CrawlPipeline(
            policy=self.policy,
            navigator=navigator,
            fetcher=fetcher,
            normalizer=normalizer,
            saver=saver,
        )

        # -------------------
        # 3. 실행
        # -------------------
        try:
            await pipeline.run()
            self.logger.info("✅ CrawlPipeline completed successfully.")
        except Exception as e:
            self.logger.exception("❌ CrawlPipeline failed: {}", e)
        finally:
            self.logger.info("📦 Output saved in: {}", self.policy.storage.base_dir)


# ----------------------------
# CLI
# ----------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run a single crawl task (cfg_like or YAML override).")
    parser.add_argument("--url", required=True, help="Target URL to crawl")
    parser.add_argument("--yaml", help="Path to crawl YAML config (optional)")
    parser.add_argument("--firefox", default="firefox.yaml", help="Path to firefox.yaml")

    args = parser.parse_args()

    runner = CrawlRunner(args.url, firefox_yaml=args.firefox)
    asyncio.run(runner.run(yamlPath=args.yaml))
