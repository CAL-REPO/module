# -*- coding: utf-8 -*-
"""
YAML 설정 기반 xl_utils 제어 테스트 (리팩토링 버전)
- 정책 기반 Excel 제어 (SRP 준수)
- 책임 분리된 컴포넌트 활용
"""

from xl_utils.xw_app import XwApp
from xl_utils.xw_wb import XwWb
from xl_utils.xw_ws import XwWs
from xl_utils.policy import XlPolicyManager
from datetime import datetime
import pandas as pd
import yaml
from pathlib import Path


def load_yaml_config(path: str | Path) -> dict:
    """YAML 파일을 읽어 dict로 반환"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_xlwings_from_yaml(cfg_path: Path = Path("./config/xlwings_test.yaml")):
    """YAML 기반 Excel 제어 테스트 (리팩토링 버전)"""
    cfg = load_yaml_config(cfg_path)
    
    # 정책 통합 로드
    policy_mgr = XlPolicyManager.from_dict(cfg)
    
    excel_path = Path(cfg["target"]["excel_path"]).resolve()
    sheet_name = cfg["target"]["sheet_name"]
    
    print(f"[CONFIG] Excel 파일: {excel_path}")
    print(f"[CONFIG] Sheet: {sheet_name}")
    print(f"[POLICY] quit_on_exit: {policy_mgr.lifecycle.quit_on_exit}")
    print(f"[POLICY] save_on_exit: {policy_mgr.lifecycle.save_on_exit}")
    
    # -------------------------------
    # App → Workbook → Worksheet 제어
    # -------------------------------
    with XwApp(
        path=excel_path,
        app_policy=policy_mgr.app,
        lifecycle_policy=policy_mgr.lifecycle
    ) as app_ctrl:
        
        # Workbook 열기
        wb_ctrl = XwWb(app_ctrl.app, path=excel_path, policy=policy_mgr.wb)
        wb = wb_ctrl.open()
        
        # Worksheet 제어
        ws_ctrl = XwWs(wb, sheet_name, policy=policy_mgr.ws)
        
        # 데이터 쓰기
        ws_ctrl.write_cell(1, 1, "YAML 기반 Excel 자동화 (리팩토링)", save=False)
        ws_ctrl.write_cell(
            2, 1, 
            datetime.now(), 
            number_format="yyyy-mm-dd hh:mm:ss",
            save=False
        )
        
        # DataFrame 기록
        df = pd.DataFrame({
            "Product": ["A", "B", "C"],
            "Qty": [12, 45, 8],
            "Price": [1200, 3100, 450],
        })
        ws_ctrl.from_dataframe(df, anchor="A4")
        ws_ctrl.autofit()
        
        # 결과 확인
        print("\n[INFO] 시트 DataFrame 읽기:")
        result_df = ws_ctrl.to_dataframe(anchor="A4")
        print(result_df)
        
        # 저장은 Context Manager가 처리
        print("\n[INFO] Context Manager가 저장 및 종료 처리 중...")
    
    print("[DONE] Excel 자동화 완료 ✅")


def test_manual_save_control():
    """수동 저장 제어 테스트"""
    from xl_utils.policy import XwAppPolicy, XwLifecyclePolicy, XwWbPolicy
    
    # 자동 저장 비활성화
    lifecycle_policy = XwLifecyclePolicy(
        quit_on_exit=True,
        save_on_exit=False  # 자동 저장 끄기
    )
    
    excel_path = Path("./test_manual.xlsx")
    
    with XwApp(
        path=excel_path,
        app_policy=XwAppPolicy(visible=False),
        lifecycle_policy=lifecycle_policy
    ) as app_ctrl:
        wb_ctrl = XwWb(app_ctrl.app, path=excel_path, policy=XwWbPolicy(create_if_missing=True))
        wb = wb_ctrl.open()
        
        ws_ctrl = XwWs(wb, "TestSheet")
        ws_ctrl.write_cell(1, 1, "Manual Save Test")
        
        # 명시적 저장
        wb_ctrl.save()
        print("[INFO] 수동 저장 완료")
    
    print("[DONE] 수동 저장 테스트 완료 ✅")


def test_attached_excel_instance():
    """기존 Excel 인스턴스 연결 테스트"""
    from xl_utils.policy import XwLifecyclePolicy
    import xlwings as xw
    
    # 먼저 Excel을 수동으로 열어둠
    print("[INFO] Excel을 수동으로 열어주세요...")
    input("준비되면 Enter를 눌러주세요...")
    
    lifecycle_policy = XwLifecyclePolicy(
        quit_on_exit=False,  # 기존 Excel은 종료하지 않음
        save_on_exit=True,
        save_attached_instance=True  # 기존 Excel도 저장
    )
    
    with XwApp(lifecycle_policy=lifecycle_policy) as app_ctrl:
        if app_ctrl.app.books.count > 0:
            wb = app_ctrl.app.books.active
            ws_ctrl = XwWs(wb, wb.sheets[0].name)
            ws_ctrl.write_cell(1, 1, f"연결 테스트: {datetime.now()}")
            print("[INFO] 기존 Excel에 데이터 작성 완료")
        else:
            print("[WARN] 열린 워크북이 없습니다")
    
    print("[DONE] 기존 Excel 인스턴스 테스트 완료 ✅")
    print("[INFO] Excel이 여전히 열려 있어야 합니다")


if __name__ == "__main__":
    print("=" * 60)
    print("1. YAML 기반 테스트")
    print("=" * 60)
    test_xlwings_from_yaml()
    
    print("\n" + "=" * 60)
    print("2. 수동 저장 제어 테스트")
    print("=" * 60)
    test_manual_save_control()
    
    print("\n" + "=" * 60)
    print("3. 기존 Excel 인스턴스 연결 테스트")
    print("=" * 60)
    # test_attached_excel_instance()  # 필요시 주석 해제