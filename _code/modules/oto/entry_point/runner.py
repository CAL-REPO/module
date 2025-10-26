# -*- coding: utf-8 -*-
"""OTO EntryPoint - OCR → Translate → Overlay Pipeline Runner.

책임:
1. ConfigLoader 실행
2. Oto Adapter 생성 및 실행
3. 이미지 처리 및 결과 출력

Usage:
    python modules/oto/entry_point/oto.py \
        --config "path/to/config.yaml" \
        --sources "img1.jpg" "img2.jpg" \
        --env-os "CASHOP_PATHS" \
        --override "image_overlay__opacity=0.8"
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Union

from modules.cfg_utils import ConfigLoader
from modules.cfg_utils.services import filter_overrides_by_prefix
from modules.logs_utils import LogManager
from modules.oto.adapter.oto import OTO


def main(
    config_loader_cfg_path: Union[str, Path],
    source_file_paths: list[Union[str, Path]],
    env_os: Union[list[str], None] = None,
    **overrides: Any
):
    """OTO Pipeline 메인 실행 함수.
    
    Args:
        config_loader_cfg_path: ConfigLoader 정책 파일 경로
        source_file_paths: 처리할 이미지 파일 경로 리스트
        env_os: OS 환경변수 리스트 (예: ["CASHOP_PATHS"])
        **overrides: Config override (예: image_overlay__opacity=0.8)
    """
    
    print("="*80)
    print("🚀 OTO Pipeline EntryPoint")
    print("="*80)
    
    # ========================================
    # Step 1: ConfigLoader 실행
    # ========================================
    print("\n[1/4] Loading configuration...")
    
    config_loader_cfg_path = Path(config_loader_cfg_path)
    
    try:
        # ConfigLoader에 config__ 접두사 필터링하여 전달
        config_overrides = filter_overrides_by_prefix(overrides, "config__")
        
        config = ConfigLoader(
            config_loader_cfg_path=str(config_loader_cfg_path),
            env_os=env_os,
            **config_overrides
        )
        print(f"  ✅ ConfigLoader initialized")
        print(f"     Config path: {config_loader_cfg_path}")
        
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
        oto = OTO(
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
    
    # Oto에 전달할 override 필터링 (oto__ 접두사)
    oto_overrides = filter_overrides_by_prefix(overrides, "oto__")
    
    if oto_overrides:
        print(f"  🔧 Runtime overrides: {len(oto_overrides)} items")
        for key, value in oto_overrides.items():
            print(f"     {key} = {value}")
    
    source_file_paths = [Path(p) for p in source_file_paths]
    
    print(f"\n  📸 Processing {len(source_file_paths)} image(s)...")
    
    results = []
    for idx, path_item in enumerate(source_file_paths, 1):
        source_path = path_item if isinstance(path_item, Path) else Path(path_item)
        print(f"\n  [{idx}/{len(source_file_paths)}] {source_path.name}")
        
        if not source_path.exists():
            print(f"      ⚠️  Image not found: {source_path}")
            results.append({"success": False, "error": "File not found", "path": str(source_path)})
            continue
        
        try:
            result = oto.run(source_path=str(source_path), **oto_overrides)
            
            if result.get("success"):
                print(f"      ✅ Success!")
                
                if "ocr_items" in result:
                    print(f"         OCR items: {len(result['ocr_items'])}")
                
                if "translated_texts" in result:
                    print(f"         Translated: {len(result['translated_texts'])}")
                
                if "output_path" in result:
                    print(f"         Output: {result['output_path']}")
            else:
                print(f"      ❌ Failed: {result.get('error', 'Unknown error')}")
            
            results.append(result)
        
        except Exception as e:
            print(f"      ❌ Exception: {e}")
            results.append({"success": False, "error": str(e), "path": str(source_path)})
    
    # ========================================
    # Summary
    # ========================================
    success_count = sum(1 for r in results if r.get("success"))
    print(f"\n  📊 Summary: {success_count}/{len(results)} succeeded")
    
    print("\n" + "="*80)
    print("✅ OTO Pipeline EntryPoint Completed")
    print("="*80)
    
    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OTO Pipeline EntryPoint")
    parser.add_argument("--config", required=True, help="ConfigLoader 정책 파일 경로")
    parser.add_argument("--sources", nargs="+", required=True, help="처리할 이미지 파일 경로 리스트")
    parser.add_argument("--env-os", nargs="*", help="OS 환경변수")
    parser.add_argument("--override", nargs="*", help="Config override (key=value)")
    
    args = parser.parse_args()
    
    # Override 파싱
    overrides = {}
    if args.override:
        for item in args.override:
            key, value = item.split("=", 1)
            try:
                value = eval(value)
            except:
                pass
            overrides[key] = value
    
    exit_code = main(
        config_loader_cfg_path=args.config,
        source_file_paths=args.sources,
        env_os=args.env_os,
        **overrides
    )
    sys.exit(exit_code)