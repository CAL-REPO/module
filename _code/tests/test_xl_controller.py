# -*- coding: utf-8 -*-
"""
tests/test_xl_controller.py
XlController 전체 워크플로우 테스트

translate_utils.Translator와 동일한 패턴으로 구현된 XlController 검증
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import pytest

# 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from xl_utils import XlController, BaseProcessor, ProcessorChain
from xl_utils.core.policy import XlPolicyManager


# =============================================================================
# Test Processors
# =============================================================================

class DemoCleanProcessor(BaseProcessor):
    """데모: 빈 행 제거 Processor"""
    
    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """빈 행 제거"""
        return df.dropna(how='all').reset_index(drop=True)


class DemoMultiplyProcessor(BaseProcessor):
    """데모: 숫자 컬럼 2배로 만들기"""
    
    def __init__(self, column: str, multiplier: float = 2.0):
        super().__init__()
        self.column = column
        self.multiplier = multiplier
    
    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """지정된 컬럼 값 곱하기"""
        if self.column in df.columns:
            df[self.column] = df[self.column] * self.multiplier
        return df


class DemoAddColumnProcessor(BaseProcessor):
    """데모: 새 컬럼 추가"""
    
    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """처리 시간 컬럼 추가"""
        df['processed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return df


# =============================================================================
# Test Cases
# =============================================================================

def test_policy_loading():
    """Test 1: XlPolicyManager YAML 로딩 테스트"""
    print("\n" + "=" * 70)
    print("TEST 1: XlPolicyManager YAML Loading")
    print("=" * 70)
    
    config_path = Path("configs/excel.yaml")
    
    if not config_path.exists():
        pytest.skip(f"Config file not found: {config_path}")
    
    # load() 메서드로 로딩
    policy_mgr = XlPolicyManager.load(config_path)
    
    assert policy_mgr is not None
    assert policy_mgr.app is not None
    assert policy_mgr.lifecycle is not None
    assert policy_mgr.wb is not None
    assert policy_mgr.ws is not None
    
    print(f"[OK] Policy loaded successfully")
    print(f"  - target_excel_path: {policy_mgr.target_excel_path}")
    print(f"  - target_sheet_name: {policy_mgr.target_sheet_name}")
    print(f"  - xw_app.visible: {policy_mgr.app.visible}")
    print(f"  - xw_lifecycle.quit_on_exit: {policy_mgr.lifecycle.quit_on_exit}")


def test_processor_chain():
    """Test 2: ProcessorChain 기본 동작 테스트"""
    print("\n" + "=" * 70)
    print("TEST 2: ProcessorChain Basic Operations")
    print("=" * 70)
    
    # 샘플 DataFrame
    df = pd.DataFrame({
        'name': ['A', 'B', None, 'D'],
        'value': [10, 20, None, 40]
    })
    
    print(f"[INPUT] DataFrame:\n{df}\n")
    
    # Processor Chain 생성
    chain = ProcessorChain([
        DemoCleanProcessor(),
        DemoMultiplyProcessor('value', multiplier=3.0),
        DemoAddColumnProcessor()
    ])
    
    # 실행
    result_df = chain.run(df)
    
    print(f"[OUTPUT] Processed DataFrame:\n{result_df}\n")
    
    # 검증
    assert len(result_df) < len(df), "Clean processor should remove empty rows"
    assert result_df['value'].iloc[0] == 30, "Multiply processor should multiply by 3"
    assert 'processed_at' in result_df.columns, "AddColumn processor should add timestamp"
    
    print("[OK] ProcessorChain works correctly")


def test_controller_dict_config():
    """Test 3: XlController dict 설정 테스트 (Excel 파일 없이)"""
    print("\n" + "=" * 70)
    print("TEST 3: XlController with Dict Config (No Excel)")
    print("=" * 70)
    
    config = {
        "xw_app": {
            "visible": False,
            "display_alerts": False,
            "screen_updating": False,
            "add_book": False
        },
        "xw_lifecycle": {
            "quit_on_exit": True,
            "save_on_exit": False,
            "save_attached_instance": False
        },
        "xw_wb": {
            "auto_save": False,
            "must_exist": False,
            "create_if_missing": True
        },
        "xw_ws": {
            "create_if_missing": True,
            "auto_save_on_write": False,
            "clear_before_dataframe": True,
            "drop_empty_rows": True
        },
        "target": {
            "excel_path": "./test_output_controller.xlsx",
            "sheet_name": "TestSheet"
        }
    }
    
    # Controller 생성 (Context Manager 없이)
    controller = XlController(config)
    
    assert controller.config is not None
    assert controller.config.app.visible == False
    assert controller.config.target_excel_path == "./test_output_controller.xlsx"
    
    print("[OK] XlController created with dict config")
    print(f"  - Excel path: {controller.config.target_excel_path}")
    print(f"  - Sheet name: {controller.config.target_sheet_name}")


def test_controller_yaml_config():
    """Test 4: XlController YAML 설정 테스트 (Excel 파일 없이)"""
    print("\n" + "=" * 70)
    print("TEST 4: XlController with YAML Config (No Excel)")
    print("=" * 70)
    
    config_path = Path("configs/excel.yaml")
    
    if not config_path.exists():
        pytest.skip(f"Config file not found: {config_path}")
    
    # Controller 생성
    controller = XlController(config_path)
    
    assert controller.config is not None
    assert controller.config.app is not None
    
    print("[OK] XlController created with YAML config")
    print(f"  - Config loaded from: {config_path}")


def test_controller_runtime_override():
    """Test 5: XlController 런타임 오버라이드 테스트"""
    print("\n" + "=" * 70)
    print("TEST 5: XlController Runtime Override")
    print("=" * 70)
    
    config_path = Path("configs/excel.yaml")
    
    if not config_path.exists():
        pytest.skip(f"Config file not found: {config_path}")
    
    # 런타임 오버라이드
    controller = XlController(
        config_path,
        xw_app__visible=False,  # Excel 창 숨기기
        target__excel_path="./override_test.xlsx",  # 경로 오버라이드
        target__sheet_name="OverrideSheet"
    )
    
    # 검증
    assert controller.config.app.visible == False, "Runtime override should work"
    assert controller.config.target_excel_path == "./override_test.xlsx"
    assert controller.config.target_sheet_name == "OverrideSheet"
    
    print("[OK] Runtime override works correctly")
    print(f"  - xw_app.visible: {controller.config.app.visible}")
    print(f"  - target_excel_path: {controller.config.target_excel_path}")


# =============================================================================
# Integration Tests (require actual Excel file)
# =============================================================================

@pytest.mark.skipif(
    not Path("./test_data.xlsx").exists(),
    reason="Requires test_data.xlsx file"
)
def test_full_workflow_with_excel():
    """Test 6: 전체 워크플로우 통합 테스트 (실제 Excel 파일 필요)"""
    print("\n" + "=" * 70)
    print("TEST 6: Full Workflow Integration Test")
    print("=" * 70)
    
    # 테스트 데이터 생성
    test_file = Path("./test_data.xlsx")
    
    # 샘플 데이터
    sample_df = pd.DataFrame({
        'product': ['Apple', 'Banana', 'Orange'],
        'price': [1000, 500, 800],
        'quantity': [5, 10, 7]
    })
    
    # Excel 파일 생성 (xlwings 사용)
    import xlwings as xw
    app = xw.App(visible=False)
    wb = app.books.add()
    ws = wb.sheets[0]
    ws.range('A1').value = sample_df
    wb.save(str(test_file))
    wb.close()
    app.quit()
    
    print(f"[OK] Test Excel file created: {test_file}")
    
    # Processor Chain
    chain = ProcessorChain([
        DemoMultiplyProcessor('price', multiplier=1.1),  # 10% 가격 인상
        DemoAddColumnProcessor()  # 처리 시간 추가
    ])
    
    # Controller로 전체 워크플로우 실행
    config = {
        "xw_app": {"visible": False, "display_alerts": False},
        "xw_lifecycle": {"quit_on_exit": True, "save_on_exit": True},
        "xw_wb": {"auto_save": True, "must_exist": True, "create_if_missing": False},
        "xw_ws": {"create_if_missing": True, "auto_save_on_write": False},
        "target": {"excel_path": str(test_file), "sheet_name": "Sheet1"}
    }
    
    try:
        with XlController(config) as xl:
            # Extract → Process → Write
            result_df = xl.run(chain, extract_anchor="A1", write_anchor="A10")
            
            print(f"\n[RESULT] Processed DataFrame:\n{result_df}\n")
            
            # 검증
            assert len(result_df) == 3
            assert 'processed_at' in result_df.columns
            assert result_df['price'].iloc[0] == 1100  # 1000 * 1.1
            
        print("[OK] Full workflow completed successfully")
        
    finally:
        # 테스트 파일 정리
        if test_file.exists():
            test_file.unlink()
            print(f"[CLEANUP] Test file removed: {test_file}")


# =============================================================================
# Main
# =============================================================================

def main():
    """전체 테스트 실행"""
    print("=" * 70)
    print("xl_utils.XlController Tests")
    print("=" * 70)
    print(f"실행 시간: {datetime.now()}\n")
    
    tests = [
        ("Policy Loading", test_policy_loading),
        ("Processor Chain", test_processor_chain),
        ("Dict Config", test_controller_dict_config),
        ("YAML Config", test_controller_yaml_config),
        ("Runtime Override", test_controller_runtime_override),
        ("Full Workflow", test_full_workflow_with_excel),
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            test_func()
            results[name] = "✅ PASS"
        except pytest.skip.Exception as e:
            results[name] = f"⏭️  SKIP - {e}"
        except Exception as e:
            results[name] = f"❌ FAIL - {e}"
            import traceback
            traceback.print_exc()
    
    # 결과 요약
    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)
    
    for name, result in results.items():
        print(f"{result} - {name}")
    
    passed = sum(1 for r in results.values() if "PASS" in r)
    total = len(results)
    
    print(f"\n총 {total}개 테스트 중 {passed}개 통과")
    
    if passed == total:
        print("\n🎉 모든 테스트 통과!")
        return 0
    else:
        print(f"\n⚠️  일부 테스트 실패")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
