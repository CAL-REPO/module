# -*- coding: utf-8 -*-

# crawl/manager.py
from __future__ import annotations
from typing import Optional, Dict, Any
from crawl.policy import CrawlPolicy
from crawl.driver import CrawlDriver
from crawl.session import CrawlSessionBuilder
from crawl.normalizer import normalize_groups
from crawl.saver import CrawlSaver
from log_utils import LogManager

class CrawlManager:
    def __init__(self, policy: CrawlPolicy, logger: Optional[LogManager] = None):
        self.policy = policy
        self.log = logger or LogManager("crawl-manager").setup()
        self._driver = CrawlDriver(policy)

    def run(self) -> Dict[str, Any]:
        try:
            self.log.info(f"Starting crawl: {self.policy.extract.url}")
            js_result = self._driver.driver.execute_script(self.policy.extract.js_extract_script or "return []")
            groups = normalize_groups(js_result, schema=self.policy.extract.group_schema)
            sess = CrawlSessionBuilder(self._driver, self.policy.extract.session, logger=self.log).build()
            saver = CrawlSaver(self.policy.download, logger=self.log)
            result = saver.save(sess, groups)
            self.log.info(f\"Crawl complete. Saved {len(result['images'])} images, {len(result['texts'])} text files, {len(result['failed'])} failed.\")\n            return result\n        finally:\n            self._driver.quit()\n\ndef run_crawl(policy: CrawlPolicy, logger: Optional[LoggerManager] = None):\n    return CrawlManager(policy, logger=logger).run()"}
]}
