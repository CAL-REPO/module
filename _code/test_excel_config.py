# -*- coding: utf-8 -*-
"""Excel Config 로드 테스트"""

import os
import sys
from pathlib import Path

# PYTHONPATH 설정
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "modules"))
sys.path.insert(0, str(project_root / "scripts"))

print("="*80)
print("🧪 Excel Config Test")
print("="*80)

# 환경변수 설정
os.environ["CASHOP_PATHS"] = str(project_root / "configs" / "paths.local.yaml")
print(f"CASHOP_PATHS: {os.environ.get('CASHOP_PATHS')}")

from cfg_utils import ConfigLoader

# ConfigLoader 생성
config = ConfigLoader(
    config_loader_cfg_path="configs/loader/config_loader_xloto.yaml",
    env_os=["CASHOP_PATHS"]
)

# excel 섹션 추출
excel_config = config.to_dict(section="excel")

print("\n" + "="*80)
print("📋 Excel Config Structure")
print("="*80)
print(f"Type: {type(excel_config)}")
print(f"Keys: {list(excel_config.keys()) if isinstance(excel_config, dict) else 'N/A'}")

if isinstance(excel_config, dict):
    print("\n" + "="*80)
    print("🔍 Config Details")
    print("="*80)
    
    for key in ["target", "aliases", "xw_app", "log"]:
        if key in excel_config:
            value = excel_config[key]
            if isinstance(value, dict):
                print(f"\n{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"\n{key}: {value}")
    
    # aliases 상세 확인
    if "aliases" in excel_config:
        aliases = excel_config["aliases"]
        print("\n" + "="*80)
        print("📌 Aliases Detail")
        print("="*80)
        print(f"Type: {type(aliases)}")
        print(f"Length: {len(aliases) if isinstance(aliases, dict) else 'N/A'}")
        if isinstance(aliases, dict):
            for key, value in list(aliases.items())[:5]:  # 처음 5개만
                print(f"  {key}: {value}")
    else:
        print("\n❌ 'aliases' key not found in excel_config!")

print("\n" + "="*80)
print("✅ Test Complete")
print("="*80)
