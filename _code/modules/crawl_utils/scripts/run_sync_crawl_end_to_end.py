# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
from pathlib import Path

# Ensure project modules dir on PYTHONPATH if running outside test harness
project_root = Path(__file__).resolve().parents[3]
if str(project_root / "modules") not in sys.path:
    sys.path.insert(0, str(project_root / "modules"))

from cfg_utils import ConfigLoader
from modules.crawl_utils.adapter.sync_crawl import SyncCrawl


def main():
    urls = [
        "https://ko.aliexpress.com/item/1005008483128442.html"
    ]
    cfg_loader_path = str(Path(__file__).resolve().parents[3] / "modules" / "crawl_utils" / "configs" / "sync_crawl_config_loader.yaml")

    config = ConfigLoader(config_loader_cfg_path=cfg_loader_path, env_os=["CASHOP_PATHS"])
    merged_config = config.to_dict()

    crawl = SyncCrawl(cfg_like=merged_config)
    results = crawl.run(urls=urls)
    print("RESULT:", results)
    # Inspect saved files if present
    for r in results:
        sf = r.get("saved_files") if isinstance(r, dict) else None
        print("Saved files:", sf)
    return 0

if __name__ == '__main__':
    sys.exit(main())
