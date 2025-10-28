import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules"))

from cfg_utils import ConfigLoader
from modules.crawl_utils.adapter.sync_crawl import SyncCrawl

# Target URL (same as test)
urls = [
    "https://ko.aliexpress.com/item/1005008483128442.html?spm=a2g0o.detail.pcDetailBottomMoreOtherSeller.6.533f4uTA4uTAMR&gps-id=pcDetailBottomMoreOtherSeller&scm=1007.40050.354490.0&scm_id=1007.40050.354490.0&scm-url=1007.40050.354490.0&pvid=786eeffd-8924-47c9-9235-d88951d17399&_t=gps-id%3ApcDetailBottomMoreOtherSeller%2Cscm-url%3A1007.40050.354490.0%2Cpvid%3A786eeffd-8924-47c9-9235-d88951d17399%2Ctpp_buckets%3A668%232846%238107%231934&pdp_ext_f=%7B%22order%22%3A%221414%22%2C%22eval%22%3A%221%22%2C%22sceneId%22%3A%2230050%22%7D&pdp_npi=6%40dis%21USD%2167.48%2137.11%21%21%2167.48%2137.11%21%402141115b17577566942155702e4901%2112000045343899055%21rec%21HK%214335231483%21ACX%211%210%21n_tag%3A-29919%3Bd%3A578eec35%3Bm03_new_user%3A-29894&utparam-url=scene%3ApcDetailBottomMoreOtherSeller%7Cquery_from%3A%7Cx_object_id%3A1005008483128442%7C_p_origin_prod%3A&gatewayAdapt=glo2kor",
]

cfg_loader_path = "M:/CALife/CAShop - 구매대행/_code/modules/crawl_utils/configs/sync_crawl_config_loader.yaml"
config = ConfigLoader(config_loader_cfg_path=str(cfg_loader_path), env_os=["CASHOP_PATHS"])
merged_config = config.to_dict()

# JS snippet probe: extract attributes from images under #product-description
probe_snippet = r"""
    // Return up to 50 images under #product-description with attributes
    return Array.from(document.querySelectorAll('#product-description img'))
      .slice(0,50)
      .map(i => ({
        src: i.getAttribute('src') || i.src || null,
        data_src: i.getAttribute('data-src') || null,
        srcset: i.getAttribute('srcset') || null,
        alt: i.getAttribute('alt') || null,
        outer: i.outerHTML ? i.outerHTML.slice(0,300) : null
      }));
"""

syncCrawl = SyncCrawl(cfg_like=merged_config)
# Run with runtime override to set extractor.js_snippet
results = syncCrawl.run(urls=urls, crawl__extractor__js_snippet=probe_snippet)

import json
print(json.dumps(results, ensure_ascii=False, indent=2))
