# -*- coding: utf-8 -*-
"""Test XLOTO EntryPoint - 한 줄 실행.

사용자 친화적 인터페이스 테스트.
"""

import sys
from pathlib import Path

# PYTHONPATH 설정
root = Path(__file__).parent
modules_dir = root / "modules"
scripts_dir = root / "scripts"

if str(modules_dir) not in sys.path:
    sys.path.insert(0, str(modules_dir))
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

print(f"Root: {root}")
print(f"Modules: {modules_dir}")
print(f"Scripts: {scripts_dir}\n")

# ============================================================================
# 한 줄 사용 테스트
# ============================================================================

from xloto import Xloto

print("="*80)
print("🔬 Test: XLOTO EntryPoint (One-Liner)")
print("="*80)

try:
    # ConfigLoader 설정 파일 경로
    config_loader_cfg_path = "configs/loader/config_loader_xloto.yaml"
    
    # EntryPoint 생성 (config_loader_cfg_path 전달)
    xloto = Xloto(config_loader_cfg_path=config_loader_cfg_path)
    
    print(f"\n✅ Xloto EntryPoint created: {xloto}")
    print(f"   Excel config loaded: {'target' in xloto.excel_config}")
    print(f"   Image config loaded: {'name' in xloto.image_load_config}")
    print(f"   OCR config loaded: {'name' in xloto.text_recognize_config}")
    print(f"   Translate config loaded: {'name' in xloto.translate_config}")
    print(f"   Overlay config loaded: {'name' in xloto.overlay_config}")
    
    # Dry-run 테스트
    print("\n" + "="*80)
    print("🧪 Running dry-run with test CAS...")
    print("="*80)
    
    test_cas_list = [
        {"cas_no": "CAPFB-001"},
        {"cas_no": "CAPFB-002"},
    ]
    
    result = xloto.run(cas_list_override=test_cas_list)
    
    print("\n" + "="*80)
    print("📊 Test Results")
    print("="*80)
    print(f"Success: {result['success']}")
    print(f"Total CAS: {result['total_cas']}")
    print(f"Processed CAS: {result['processed_cas']}")
    
    if result.get("cas_results"):
        print(f"\nCAS Results:")
        for cas_result in result["cas_results"]:
            print(f"  - {cas_result['cas_no']}: {cas_result.get('processed_count', 0)} images")
    
    if result.get("error"):
        print(f"\nError: {result['error']}")
    
    print("="*80)
    
    if result["success"]:
        print("\n✅ EntryPoint Test PASSED")
    else:
        print("\n❌ EntryPoint Test FAILED")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("💡 Usage Example:")
print("="*80)
print("""
from xloto import Xloto

# config_loader_cfg_path 전달하여 실행
xloto = Xloto(config_loader_cfg_path="configs/loader/config_loader_xloto.yaml")
result = xloto.run()

# 또는 커스텀 설정
xloto = Xloto(
    config_loader_cfg_path="configs/loader/config_loader_xloto.yaml",
    xloto_cfg="custom_xloto.yaml"
)
result = xloto.run(cas_list_override=["CAPFB-001"])
""")
print("="*80)
