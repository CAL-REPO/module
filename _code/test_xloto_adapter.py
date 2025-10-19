# -*- coding: utf-8 -*-
"""Test XlOto Adapter.

테스트 시나리오:
1. ConfigLoader로 config_loader_xloto.yaml 로드
2. Excel에서 CAS No 추출 검증
3. Oto adapter 통합 확인
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
print(f"Scripts: {scripts_dir}")
print(f"sys.path: {sys.path[:3]}\n")

from xloto.adapter.xloto import XlOto


def test_xloto_dry_run():
    """XlOto Adapter dry-run 테스트 (CAS override)."""
    print("\n" + "="*80)
    print("🔬 Test: XlOto Adapter (Dry Run)")
    print("="*80)
    
    # XlOto adapter 생성
    xloto = XlOto(cfg_like="configs/xloto.yaml")
    
    print(f"✅ Adapter created: {xloto}")
    
    # ConfigLoader 설정 경로
    config_path = root / "configs" / "loader" / "config_loader_xloto.yaml"
    
    print(f"\n📄 Config: {config_path.name}")
    
    # Dry-run: CAS No 리스트 강제 지정 (Excel 무시)
    test_cas_list = [
        {"cas_no": "CAPFB-001"},
        {"cas_no": "CAPFB-002"},
    ]
    
    print(f"\n🧪 Running dry-run with {len(test_cas_list)} test CAS...")
    
    try:
        result = xloto.run(
            config_path=config_path,
            cas_list_override=test_cas_list,
        )
        
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
        
        return result["success"]
    
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_xloto_excel_extraction():
    """XlOto Adapter Excel CAS 추출 테스트."""
    print("\n" + "="*80)
    print("🔬 Test: Excel CAS Extraction (No Processing)")
    print("="*80)
    
    xloto = XlOto(cfg_like="configs/xloto.yaml")
    
    config_path = root / "configs" / "loader" / "config_loader_xloto.yaml"
    
    print(f"\n📄 Config: {config_path.name}")
    print("\nℹ️  This test will extract CAS No from Excel but skip processing")
    print("   (Use test_cas_list = [] to skip processing)")
    
    try:
        # Excel에서 CAS 추출만 하고 처리는 스킵
        result = xloto.run(
            config_path=config_path,
            cas_list_override=[],  # 빈 리스트로 처리 스킵
        )
        
        print("\n" + "="*80)
        print("📊 Test Results")
        print("="*80)
        print(f"Success: {result['success']}")
        print(f"Total CAS: {result['total_cas']}")
        print("="*80)
        
        return result["success"]
    
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "🚀 XlOto Adapter Tests" + "\n")
    
    # Test 1: Dry-run (CAS override)
    test1_pass = test_xloto_dry_run()
    
    # Test 2: Excel extraction (optional, 실제 Excel 파일 필요)
    # test2_pass = test_xloto_excel_extraction()
    
    print("\n" + "="*80)
    print("🏁 Test Summary")
    print("="*80)
    print(f"Test 1 (Dry-run): {'✅ PASS' if test1_pass else '❌ FAIL'}")
    # print(f"Test 2 (Excel): {'✅ PASS' if test2_pass else '❌ FAIL'}")
    print("="*80 + "\n")
