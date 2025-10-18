# -*- coding: utf-8 -*-
"""Placeholder 해석 테스트"""

import os
from pathlib import Path

# PYTHONPATH 설정
import sys
sys.path.insert(0, str(Path(__file__).parent / "modules"))

from cfg_utils import ConfigLoader

def test_placeholder_resolution():
    """Placeholder 해석 테스트"""
    
    # OS 환경 변수 설정
    os.environ["CASHOP_PATHS"] = str(Path(__file__).parent / "configs" / "paths.local.yaml")
    
    print("=" * 80)
    print("Placeholder Resolution Test")
    print("=" * 80)
    
    # ConfigLoader 생성
    loader = ConfigLoader(
        config_loader_cfg_path=Path(__file__).parent / "configs" / "loader" / "config_loader_oto.yaml",
        env_os=["CASHOP_PATHS"]
    )
    
    # State 확인
    state = loader.get_state()
    
    print("\n1. ENV Section:")
    print("-" * 80)
    env_data = state.get("env", {})
    if "CASHOP_PATHS" in env_data:
        cashop_paths = env_data["CASHOP_PATHS"]
        print(f"CASHOP_PATHS keys: {list(cashop_paths.keys())}")
        print(f"  base_path: {cashop_paths.get('base_path')}")
        print(f"  configs_dir: {cashop_paths.get('configs_dir')}")
        print(f"  configs_oto_dir: {cashop_paths.get('configs_oto_dir')}")
    
    print("\n2. Image Section:")
    print("-" * 80)
    image_data = state.get("image", {})
    if image_data:
        print(f"Image keys: {list(image_data.keys())[:5]}...")
        print(f"  temp_input_dir: {image_data.get('temp_input_dir')}")
        print(f"  max_width: {image_data.get('max_width')}")
    
    print("\n3. OCR Section:")
    print("-" * 80)
    ocr_data = state.get("ocr", {})
    if ocr_data:
        print(f"OCR keys: {list(ocr_data.keys())[:5]}...")
        print(f"  temp_input_dir: {ocr_data.get('temp_input_dir')}")
    
    print("\n" + "=" * 80)
    print("✅ Test completed!")
    print("=" * 80)

if __name__ == "__main__":
    test_placeholder_resolution()
