# -*- coding: utf-8 -*-
"""
xl_utils 통합 테스트 실행 스크립트
YAML 설정 기반 Excel 자동화 테스트
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import yaml

# 모듈 경로 추가 (필요시)
# sys.path.insert(0, str(Path(__file__).parent.parent))

from xl_utils.xw_app import XwApp
from xl_utils.xw_wb import XwWb
from xl_utils.xw_ws import XwWs
from xl_utils.core.policy import XlPolicyManager, XwAppPolicy, XwLifecyclePolicy, XwWbPolicy


def load_yaml_config(path: Path) -> dict:
    """YAML 설정 파일 로드"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"[ERROR] 설정 파일을 찾을 수 없습니다: {path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"[ERROR] YAML 파싱 오류: {e}")
        sys.exit(1)


def test_yaml_based_excel_control():
    """테스트 1: YAML 기반 Excel 제어"""
    print("\n" + "=" * 70)
    print("TEST 1: YAML 기반 Excel 자동화")
    print("=" * 70)
    
    # YAML 설정 로드
    config_path = Path("./excel.yaml")  # 또는 실제 경로
    if not config_path.exists():
        print(f"[WARN] {config_path}가 없습니다. 기본 설정으로 진행합니다.")
        cfg = {
            "xw_app": {"visible": True, "display_alerts": False, "screen_updating": True, "add_book": False},
            "xw_lifecycle": {"quit_on_exit": True, "save_on_exit": True, "save_attached_instance": False},
            "xw_wb": {"auto_save": False, "must_exist": False, "create_if_missing": True},
            "xw_ws": {"create_if_missing": True, "auto_save_on_write": False, 
                     "clear_before_dataframe": True, "drop_empty_rows": True},
            "target": {
                "excel_path": "./test_output.xlsx",
                "sheet_name": "TestSheet"
            }
        }
    else:
        cfg = load_yaml_config(config_path)
    
    # 정책 매니저 생성
    policy_mgr = XlPolicyManager.from_dict(cfg)
    
    # Excel 경로 설정
    excel_path = Path(cfg.get("target", {}).get("excel_path", "./test_output.xlsx")).resolve()
    sheet_name = cfg.get("target", {}).get("sheet_name", "TestSheet")
    
    print(f"[CONFIG] Excel 파일: {excel_path}")
    print(f"[CONFIG] Sheet: {sheet_name}")
    print(f"[POLICY] quit_on_exit: {policy_mgr.lifecycle.quit_on_exit}")
    print(f"[POLICY] save_on_exit: {policy_mgr.lifecycle.save_on_exit}")
    
    try:
        # Excel 자동화 실행
        with XwApp(
            path=excel_path,
            app_policy=policy_mgr.app,
            lifecycle_policy=policy_mgr.lifecycle
        ) as app_ctrl:
            
            # Workbook 열기
            wb_ctrl = XwWb(app_ctrl.app, path=excel_path, policy=policy_mgr.wb)
            wb = wb_ctrl.open()
            print(f"[OK] Workbook 열림: {wb.name}")
            
            # Worksheet 제어
            ws_ctrl = XwWs(wb, sheet_name, policy=policy_mgr.ws)
            
            # 헤더 작성
            ws_ctrl.write_cell(1, 1, "YAML 기반 Excel 자동화 테스트", save=False)
            ws_ctrl.write_cell(
                2, 1, 
                datetime.now(), 
                number_format="yyyy-mm-dd hh:mm:ss",
                save=False
            )
            
            # 샘플 데이터 작성
            df = pd.DataFrame({
                "제품명": ["제품 A", "제품 B", "제품 C", "제품 D"],
                "수량": [12, 45, 8, 23],
                "단가": [1200, 3100, 450, 2800],
                "합계": [14400, 139500, 3600, 64400]
            })
            
            print("\n[INFO] DataFrame을 Excel에 작성 중...")
            ws_ctrl.from_dataframe(df, anchor="A4")
            ws_ctrl.autofit()
            
            # 작성된 데이터 검증
            print("\n[INFO] 작성된 데이터 읽기:")
            result_df = ws_ctrl.to_dataframe(anchor="A4")
            print(result_df)
            
            print("\n[OK] 데이터 작성 완료")
            print("[INFO] Context Manager가 저장 및 종료 처리 중...")
        
        print("\n[SUCCESS] TEST 1 완료 ✅")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] TEST 1 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_manual_save_control():
    """테스트 2: 수동 저장 제어"""
    print("\n" + "=" * 70)
    print("TEST 2: 수동 저장 제어")
    print("=" * 70)
    
    # 자동 저장 비활성화 정책
    lifecycle_policy = XwLifecyclePolicy(
        quit_on_exit=True,
        save_on_exit=False  # 자동 저장 끄기
    )
    
    excel_path = Path("./test_manual_save.xlsx").resolve()
    print(f"[CONFIG] Excel 파일: {excel_path}")
    print(f"[POLICY] 자동 저장: OFF, 수동 저장 테스트")
    
    try:
        with XwApp(
            path=excel_path,
            app_policy=XwAppPolicy(visible=False),
            lifecycle_policy=lifecycle_policy
        ) as app_ctrl:
            
            wb_ctrl = XwWb(
                app_ctrl.app, 
                path=excel_path, 
                policy=XwWbPolicy(create_if_missing=True, must_exist=False)
            )
            wb = wb_ctrl.open()
            
            ws_ctrl = XwWs(wb, "ManualSaveTest")
            ws_ctrl.write_cell(1, 1, "수동 저장 테스트")
            ws_ctrl.write_cell(2, 1, datetime.now(), number_format="yyyy-mm-dd hh:mm:ss")
            
            # 명시적 저장
            wb_ctrl.save()
            print("[OK] 수동 저장 완료")
        
        print("\n[SUCCESS] TEST 2 완료 ✅")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] TEST 2 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_sheets():
    """테스트 3: 다중 시트 작업"""
    print("\n" + "=" * 70)
    print("TEST 3: 다중 시트 작업")
    print("=" * 70)
    
    excel_path = Path("./test_multi_sheets.xlsx").resolve()
    print(f"[CONFIG] Excel 파일: {excel_path}")
    
    try:
        with XwApp(path=excel_path) as app_ctrl:
            wb_ctrl = XwWb(
                app_ctrl.app, 
                path=excel_path,
                policy=XwWbPolicy(create_if_missing=True, must_exist=False)
            )
            wb = wb_ctrl.open()
            
            # 여러 시트에 데이터 작성
            sheets_data = {
                "Summary": pd.DataFrame({"항목": ["총계", "평균"], "값": [1000, 250]}),
                "Detail": pd.DataFrame({"ID": [1, 2, 3], "이름": ["A", "B", "C"]}),
                "Report": pd.DataFrame({"날짜": [datetime.now()], "상태": ["완료"]})
            }
            
            for sheet_name, data in sheets_data.items():
                print(f"[INFO] 시트 '{sheet_name}' 작성 중...")
                ws_ctrl = XwWs(wb, sheet_name)
                ws_ctrl.from_dataframe(data, anchor="A1")
                ws_ctrl.autofit()
            
            print(f"[OK] {len(sheets_data)}개 시트 작성 완료")
        
        print("\n[SUCCESS] TEST 3 완료 ✅")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] TEST 3 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """전체 테스트 실행"""
    print("=" * 70)
    print("xl_utils 통합 테스트 시작")
    print("=" * 70)
    print(f"실행 시간: {datetime.now()}")
    
    results = {}
    
    # 테스트 실행
    results["TEST 1: YAML 기반"] = test_yaml_based_excel_control()
    results["TEST 2: 수동 저장"] = test_manual_save_control()
    results["TEST 3: 다중 시트"] = test_multiple_sheets()
    
    # 결과 요약
    print("\n" + "=" * 70)
    print("테스트 결과 요약")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\n총 {total}개 테스트 중 {passed}개 통과")
    
    if passed == total:
        print("\n🎉 모든 테스트 통과!")
        return 0
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)