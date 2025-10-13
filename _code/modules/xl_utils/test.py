# -*- coding: utf-8 -*-
"""
YAML 설정 기반 xl_utils 제어 테스트
- config/xlwings_test.yaml 파일을 불러와
  Excel을 App → Workbook → Worksheet 계층으로 제어
"""

from xl_utils.xw_app import XwApp
from xl_utils.xw_wb import XwWb
from xl_utils.xw_ws import XwWs
from xl_utils.policy import XwAppPolicy, XwWbPolicy
from datetime import datetime
import pandas as pd
import yaml
from pathlib import Path


def load_yaml_config(path: str | Path) -> dict:
    """YAML 파일을 읽어 dict로 반환"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_xlwings_from_yaml(cfg_path: Path = Path("./config/xlwings_test.yaml")):
    """YAML 기반 Excel 제어 테스트"""
    cfg = load_yaml_config(cfg_path)
    app_policy = XwAppPolicy(**cfg.get("xw_app", {}))
    wb_policy = XwWbPolicy(**cfg.get("xw_wb", {}))

    excel_path = Path(cfg["target"]["excel_path"]).resolve()
    sheet_name = cfg["target"]["sheet_name"]

    print(f"[CONFIG] Excel 파일: {excel_path}")
    print(f"[CONFIG] Sheet: {sheet_name}")

    # -------------------------------
    # App → Workbook → Worksheet 제어
    # -------------------------------
    with XwApp(path=excel_path, policy=app_policy) as app_ctrl:
        wb_ctrl = XwWb(app_ctrl.app, path=excel_path, policy=wb_policy)
        wb = wb_ctrl.open()

        ws_ctrl = XwWs(wb, sheet_name, create_if_missing=True)
        ws_ctrl.write_cell(1, 1, "YAML 기반 Excel 자동화", save=True)
        ws_ctrl.write_cell(2, 1, datetime.now(), number_format="yyyy-mm-dd hh:mm:ss", save=True)

        # DataFrame 기록
        df = pd.DataFrame({
            "Product": ["A", "B", "C"],
            "Qty": [12, 45, 8],
            "Price": [1200, 3100, 450],
        })
        ws_ctrl.from_dataframe(df, anchor="A4")
        ws_ctrl.autofit()

        # 결과 확인
        print("[INFO] 시트 DataFrame 읽기:")
        print(ws_ctrl.to_dataframe(anchor="A4"))

        # wb_ctrl.save
        # wb_ctrl.close(save=wb_policy.auto_save)

    print("[DONE] Excel 자동화 완료 ✅")


if __name__ == "__main__":
    test_xlwings_from_yaml()
