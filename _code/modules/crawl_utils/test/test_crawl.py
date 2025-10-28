# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
from pathlib import Path

# PYTHONPATH 설정 (modules 디렉토리)
project_root = Path(__file__).resolve().parents[3]  # _code 디렉토리
sys.path.insert(0, str(project_root / "scripts"))

print(project_root)

from cfg_utils import ConfigLoader
from modules.crawl_utils.adapter.sync_crawl import SyncCrawl

def main():

    urls = [
        "https://ko.aliexpress.com/item/1005008483128442.html?spm=a2g0o.detail.pcDetailBottomMoreOtherSeller.6.533f4uTA4uTAMR&gps-id=pcDetailBottomMoreOtherSeller&scm=1007.40050.354490.0&scm_id=1007.40050.354490.0&scm-url=1007.40050.354490.0&pvid=786eeffd-8924-47c9-9235-d88951d17399&_t=gps-id%3ApcDetailBottomMoreOtherSeller%2Cscm-url%3A1007.40050.354490.0%2Cpvid%3A786eeffd-8924-47c9-9235-d88951d17399%2Ctpp_buckets%3A668%232846%238107%231934&pdp_ext_f=%7B%22order%22%3A%221414%22%2C%22eval%22%3A%221%22%2C%22sceneId%22%3A%2230050%22%7D&pdp_npi=6%40dis%21USD%2167.48%2137.11%21%21%2167.48%2137.11%21%402141115b17577566942155702e4901%2112000045343899055%21rec%21HK%214335231483%21ACX%211%210%21n_tag%3A-29919%3Bd%3A578eec35%3Bm03_new_user%3A-29894&utparam-url=scene%3ApcDetailBottomMoreOtherSeller%7Cquery_from%3A%7Cx_object_id%3A1005008483128442%7C_p_origin_prod%3A&gatewayAdapt=glo2kor",
    ]

    cfg_loader_path = "M:/CALife/CAShop - 구매대행/_code/modules/crawl_utils/configs/sync_crawl_config_loader.yaml"
    config = ConfigLoader(config_loader_cfg_path=str(cfg_loader_path), env_os=["CASHOP_PATHS"])
    merged_config = config.to_dict()
    
    # ========================================
    # 2️⃣ Runtime Override 테스트 (Array Index 형식)
    # ========================================
    print("\n" + "="*80)
    print("2️⃣ Runtime Override 테스트: sync_crawl__items[0]__dir_path (Array Index)")
    print("="*80)
    
    test_directory = "M:/CALife/CAShop - 구매대행/_code/output/test/TEST_RUNTIME_OVERRIDE"
    
    print(f"✅ Attempting override to: '{test_directory}'")
    print("="*80 + "\n")
    
    # ✅ run() 메서드의 **overrides 파라미터 사용 (Array Index 형식)
    syncCrawl = SyncCrawl(cfg_like=merged_config)
    syncCrawl.run(
        urls=urls,
        **{"sync_crawl__items[0]__dir_path": test_directory}  # ✅ Array Index 형식
    )

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)