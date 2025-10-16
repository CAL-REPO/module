"""Placeholder 해석 테스트"""
import os
from pathlib import Path
from modules.cfg_utils.services.config_loader import ConfigLoader

# 환경변수 확인
paths_env = os.getenv("CASHOP_PATHS")
print(f"CASHOP_PATHS: {paths_env}\n")

if paths_env:
    paths_yaml = Path(paths_env)
    
    # paths.local.yaml 로드
    print("="*80)
    print("ConfigLoader.load() 결과:")
    print("="*80)
    paths_dict = ConfigLoader.load(paths_yaml)
    
    # 주요 경로 출력
    print(f"\nroot: {paths_dict.get('root')}")
    print(f"code_dir: {paths_dict.get('code_dir')}")
    print(f"configs_dir: {paths_dict.get('configs_dir')}")
    print(f"configs_loader_dir: {paths_dict.get('configs_loader_dir')}")
    
    print("\nconfigs_loader_file_path:")
    loader_paths = paths_dict.get("configs_loader_file_path", {})
    for key, val in loader_paths.items():
        exists = Path(val).exists() if val else False
        status = "✅" if exists else "❌"
        print(f"  {status} {key}: {val}")
