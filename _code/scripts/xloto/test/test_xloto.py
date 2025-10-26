# -*- coding: utf-8 -*-
"""xlOTO EntryPoint - OCR → Translate → Overlay Pipeline Runner.

책임:
1. ConfigLoader 실행 (CASHOP_PATHS 환경변수 기반)
2. xlOto Adapter 생성 및 실행
3. 파일 I/O 처리 (이미지 로딩 및 저장)
4. 결과 출력

Usage:
    python modules/xloto/entry_point/xloto.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# PYTHONPATH 설정 (modules 디렉토리)
project_root = Path(__file__).resolve().parents[3]  # _code 디렉토리
sys.path.insert(0, str(project_root / "scripts"))

print(project_root)

from cfg_utils import ConfigLoader
from logs_utils import LogManager
from scripts.xloto.adapter.xloto import XlOTO


def main():
    """xlOto Pipeline 메인 실행 함수."""

    print("="*80)
    print("🚀 xlOto Pipeline EntryPoint")
    print("="*80)
    
    # ========================================
    # Step 1: ConfigLoader 실행
    # ========================================
    print("\n[1/4] Loading configuration...")

    config_path = project_root / "scripts" / "xloto" / "configs" / "xloto_config_loader.yaml"

    try:
        config = ConfigLoader(
            config_loader_cfg_path=str(config_path),
            env_os=["CASHOP_PATHS"]  # paths.local.yaml 참조 해석
        )
        print(f"  ✅ ConfigLoader initialized")
        print(f"     Config path: {config_path}")
        
        # 병합된 설정 확인
        merged_config = config.to_dict()
        print(f"     Sections loaded: {list(merged_config.keys())}")
        
    except Exception as e:
        print(f"  ❌ ConfigLoader failed: {e}")
        return 1

    # ========================================
    # Step 2: XlOTO Pipeline 실행
    # ========================================
    print("\n[2/4] Running XlOTO Pipeline...")
    
    xloto = XlOTO(cfg_like=merged_config)
    xloto.run()  # ← 파일 경로 제거 (Policy에서 가져옴)

    # ========================================
    # Complete
    # ========================================
    print("\n" + "="*80)
    print("✅ XlOTO Pipeline EntryPoint Completed")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)