# -*- coding: utf-8 -*-
"""Runtime Override 적용 여부 디버깅"""

import sys
from pathlib import Path

# PYTHONPATH 설정
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "scripts"))

from cfg_utils import ConfigLoader
from modules.crawl_utils.adapter.sync_crawl import SyncCrawl

def test_override_only():
    """Runtime Override만 테스트 (크롤링 없이)"""
    
    cfg_loader_path = "M:/CALife/CAShop - 구매대행/_code/modules/crawl_utils/configs/sync_crawl_config_loader.yaml"
    config = ConfigLoader(config_loader_cfg_path=str(cfg_loader_path), env_os=["CASHOP_PATHS"])
    merged_config = config.to_dict()
    
    print("\n" + "="*80)
    print("Original Config")
    print("="*80)
    print(f"sync_crawl.items[0].dir_path: {merged_config.get('sync_crawl', {}).get('items', [{}])[0].get('dir_path', 'N/A')}")
    
    # Runtime Override 적용
    test_directory = "M:/CALife/CAShop - 구매대행/_code/output/test/TEST_RUNTIME_OVERRIDE"
    merged_config["sync_crawl"]["items"][0]["dir_path"] = test_directory
    
    print("\n" + "="*80)
    print("After Override (before SyncCrawl)")
    print("="*80)
    print(f"sync_crawl.items[0].dir_path: {merged_config['sync_crawl']['items'][0]['dir_path']}")
    
    # SyncCrawl 초기화
    sync_crawl = SyncCrawl(cfg_like=merged_config)
    
    # Policy 확인 (preset 적용 전)
    print("\n" + "="*80)
    print("SyncCrawl Policy (after __init__)")
    print("="*80)
    print(f"policy.items[0].dir_path: {sync_crawl.policy.items[0].dir_path if sync_crawl.policy.items else 'N/A'}")
    
    print("\n" + "="*80)
    print("Test Complete")
    print("="*80)

if __name__ == "__main__":
    test_override_only()
