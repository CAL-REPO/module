# -*- coding: utf-8 -*-
"""OTO EntryPoint - OCR → Translate → Overlay Pipeline Runner.

책임:
1. ConfigLoader 실행 (CASHOP_PATHS 환경변수 기반)
2. Oto Adapter 생성 및 실행
3. 파일 I/O 처리 (이미지 로딩 및 저장)
4. 결과 출력

Usage:
    python scripts/oto/entry_point/oto.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# PYTHONPATH 설정 (modules 디렉토리)
project_root = Path(__file__).resolve().parents[3]  # _code 디렉토리
sys.path.insert(0, str(project_root / "modules"))

from cfg_utils import ConfigLoader
from logs_utils import LogManager
from scripts.oto.adapter.oto import Oto


def main():
    """OTO Pipeline 메인 실행 함수."""
    
    print("="*80)
    print("🚀 OTO Pipeline EntryPoint")
    print("="*80)
    
    # ========================================
    # Step 1: ConfigLoader 실행
    # ========================================
    print("\n[1/4] Loading configuration...")
    
    config_path = project_root / "scripts" / "oto" / "configs" / "oto_config_loader.yaml"
    
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
    # Step 2: LogManager 생성
    # ========================================
    print("\n[2/4] Initializing LogManager...")
    
    try:
        # OTO 통합 로그 정책 사용
        log_config = merged_config.get("log", {"enabled": True})
        log_manager = LogManager(log_config)
        print(f"  ✅ LogManager initialized")
        
    except Exception as e:
        print(f"  ❌ LogManager failed: {e}")
        log_manager = LogManager({"enabled": False})
    
    # ========================================
    # Step 3: Oto Adapter 생성
    # ========================================
    print("\n[3/4] Creating Oto Adapter...")
    
    try:
        oto = Oto(
            cfg_like=merged_config,
            log_manager=log_manager
        )
        print(f"  ✅ Oto Adapter created")
        print(f"     Policy: {oto.policy.__class__.__name__}")
        
    except Exception as e:
        print(f"  ❌ Oto Adapter creation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # ========================================
    # Step 4: 이미지 처리 실행
    # ========================================
    print("\n[4/4] Running OTO Pipeline...")
    
    # 테스트 이미지 경로 (사용자가 변경 가능)
    test_image_path = project_root / "scripts" / "oto" / "test" / "images" / "01.jpg"
    
    if not test_image_path.exists():
        print(f"  ⚠️  Test image not found: {test_image_path}")
        print(f"     Please update the image path in this script.")
        return 1
    
    print(f"  📸 Input: {test_image_path.name}")
    
    try:
        # OTO 파이프라인 실행
        result = oto.run(source_path=str(test_image_path))
        
        if result.get("success"):
            print(f"\n  ✅ Pipeline completed successfully!")
            
            # 결과 정보 출력
            if "ocr_items" in result:
                print(f"     OCR items detected: {len(result['ocr_items'])}")
            
            if "translated_texts" in result:
                print(f"     Texts translated: {len(result['translated_texts'])}")
            
            if "output_path" in result:
                print(f"     Output saved: {result['output_path']}")
            
            # 이미지 정보
            if "image" in result:
                img = result["image"]
                print(f"     Image size: {img.size}")
        else:
            print(f"\n  ❌ Pipeline failed:")
            print(f"     Error: {result.get('error', 'Unknown error')}")
            return 1
    
    except Exception as e:
        print(f"\n  ❌ Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # ========================================
    # Complete
    # ========================================
    print("\n" + "="*80)
    print("✅ OTO Pipeline EntryPoint Completed")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)