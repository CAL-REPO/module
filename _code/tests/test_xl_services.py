# -*- coding: utf-8 -*-
"""
tests/test_xl_services.py
xl_utils 셀 조작 서비스 테스트

xl_utils는 Excel 셀 조작만 제공
DataFrame 처리는 비즈니스 단에서 수행
"""

from pathlib import Path
import tempfile
import pytest
import pandas as pd

from xl_utils import XlController, XwWs
from xl_utils.core.policy import XlPolicyManager, XwAppPolicy, XwWbPolicy, XwWsPolicy, XwLifecyclePolicy


@pytest.fixture
def test_excel_path():
    """테스트용 임시 Excel 파일 생성"""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        excel_path = Path(f.name)
    
    # 초기 데이터 생성
    df = pd.DataFrame({
        "제품명": ["사과", "바나나", "딸기"],
        "가격": [1000, 2000, 3000],
        "수량": [10, 20, 30]
    })
    df.to_excel(excel_path, sheet_name="Sheet1", index=False)
    
    yield excel_path
    
    # 테스트 후 정리
    if excel_path.exists():
        excel_path.unlink()


@pytest.fixture
def policy_mgr():
    """테스트용 Policy Manager"""
    return XlPolicyManager(
        app=XwAppPolicy(
            visible=False,
            display_alerts=False,
            screen_updating=False,
            add_book=False
        ),
        lifecycle=XwLifecyclePolicy(
            quit_on_exit=True,
            save_on_exit=False,
            save_attached_instance=False
        ),
        wb=XwWbPolicy(
            auto_save=False,
            must_exist=False,
            create_if_missing=True
        ),
        ws=XwWsPolicy(
            create_if_missing=True,
            auto_save_on_write=False,
            clear_before_dataframe=False,
            drop_empty_rows=False
        )
    )


class TestXwWsCellOps:
    """XwWs 셀 조작 테스트"""
    
    def test_read_write_cell(self, test_excel_path, policy_mgr):
        """단일 셀 읽기/쓰기 테스트"""
        with XlController(policy_mgr) as xl:
            xl.config.target_excel_path = test_excel_path
            ws = xl.get_worksheet()
            
            # 단일 셀 쓰기
            ws.write_cell(1, 1, "제목")
            
            # 단일 셀 읽기
            value = ws.read("A1")
            assert value == "제목"
    
    def test_write_read_range(self, test_excel_path, policy_mgr):
        """범위 읽기/쓰기 테스트"""
        with XlController(policy_mgr) as xl:
            xl.config.target_excel_path = test_excel_path
            ws = xl.get_worksheet()
            
            # 범위 쓰기
            data = [
                [1, 2, 3],
                [4, 5, 6],
                [7, 8, 9]
            ]
            ws.write_range("A1:C3", data)
            
            # 범위 읽기
            result = ws.read_range("A1:C3")
            assert result == data
    
    def test_apply_format(self, test_excel_path, policy_mgr):
        """서식 적용 테스트"""
        with XlController(policy_mgr) as xl:
            xl.config.target_excel_path = test_excel_path
            ws = xl.get_worksheet()
            
            # 셀 쓰기
            ws.write_cell(1, 1, "제목")
            
            # 서식 적용
            ws.apply_format(
                "A1",
                bold=True,
                font_size=14,
                font_color=(255, 0, 0),  # Red
                bg_color=(255, 255, 0),  # Yellow
                horizontal_alignment="center"
            )
            
            # 검증 (xlwings API 사용)
            rng = ws.sheet.range("A1")
            assert rng.font.bold == True
            assert rng.font.size == 14
    
    def test_insert_delete_rows(self, test_excel_path, policy_mgr):
        """행 삽입/삭제 테스트"""
        with XlController(policy_mgr) as xl:
            xl.config.target_excel_path = test_excel_path
            ws = xl.get_worksheet()
            
            # 초기 데이터 작성
            ws.write_range("A1:C3", [
                [1, 2, 3],
                [4, 5, 6],
                [7, 8, 9]
            ])
            
            # 2번 행 삽입
            ws.insert_rows(2, count=1)
            
            # 검증: 삽입 후 원래 2번 행이 3번 행으로 이동
            assert ws.read("A3") == 4.0  # xlwings는 숫자를 float로 반환
            
            # 2번 행 삭제
            ws.delete_rows(2, count=1)
            
            # 검증: 삭제 후 원래 위치로 복구
            assert ws.read("A2") == 4.0
    
    def test_insert_delete_columns(self, test_excel_path, policy_mgr):
        """열 삽입/삭제 테스트"""
        with XlController(policy_mgr) as xl:
            xl.config.target_excel_path = test_excel_path
            ws = xl.get_worksheet()
            
            # 초기 데이터 작성
            ws.write_range("A1:C3", [
                [1, 2, 3],
                [4, 5, 6],
                [7, 8, 9]
            ])
            
            # B열 앞에 삽입
            ws.insert_columns("B", count=1)
            
            # 검증: 삽입 후 원래 B열이 C열로 이동
            assert ws.read("C1") == 2.0
            
            # B열 삭제
            ws.delete_columns("B", count=1)
            
            # 검증: 삭제 후 원래 위치로 복구
            assert ws.read("B1") == 2.0
    
    def test_clear_range(self, test_excel_path, policy_mgr):
        """범위 초기화 테스트"""
        with XlController(policy_mgr) as xl:
            xl.config.target_excel_path = test_excel_path
            ws = xl.get_worksheet()
            
            # 데이터 작성
            ws.write_range("A1:C3", [
                [1, 2, 3],
                [4, 5, 6],
                [7, 8, 9]
            ])
            
            # 범위 초기화
            ws.clear_range("A1:C3")
            
            # 검증
            assert ws.read("A1") is None
            assert ws.read("B2") is None


class TestXlController:
    """XlController 통합 테스트"""
    
    def test_context_manager(self, test_excel_path, policy_mgr):
        """Context Manager 정상 동작 테스트"""
        with XlController(policy_mgr) as xl:
            xl.config.target_excel_path = test_excel_path
            ws = xl.get_worksheet()
            
            # 셀 조작
            ws.write_cell(1, 1, "테스트")
            value = ws.read("A1")
            
            assert value == "테스트"
    
    def test_dataframe_conversion(self, test_excel_path, policy_mgr):
        """DataFrame 변환 테스트 (비즈니스 로직 예시)"""
        with XlController(policy_mgr) as xl:
            xl.config.target_excel_path = test_excel_path
            ws = xl.get_worksheet()
            
            # 1. Excel → DataFrame (xl_utils 제공)
            df = ws.to_dataframe(anchor="A1")
            
            # 2. 비즈니스 로직 (사용자 단에서 수행)
            df["총액"] = df["가격"] * df["수량"]
            df["할인가"] = df["가격"] * 0.9
            
            # 3. DataFrame → Excel (xl_utils 제공)
            ws.from_dataframe(df, anchor="F1", index=False, header=True)
            
            # 4. 검증
            total = ws.read("H2")  # 첫 번째 "총액" 값
            assert total == 10000.0  # 1000 * 10
    
    def test_runtime_override(self, test_excel_path):
        """런타임 설정 오버라이드 테스트"""
        with XlController(
            None,  # 기본 config 사용
            xw_app__visible=False,
            xw_app__display_alerts=False
        ) as xl:
            xl.config.target_excel_path = test_excel_path
            
            # Policy 검증
            assert xl.config.app.visible == False
            assert xl.config.app.display_alerts == False


class TestRealWorldScenario:
    """실제 사용 시나리오 테스트"""
    
    def test_complex_workflow(self, test_excel_path, policy_mgr):
        """복잡한 워크플로우 테스트"""
        with XlController(policy_mgr) as xl:
            xl.config.target_excel_path = test_excel_path
            ws = xl.get_worksheet()
            
            # 1. 헤더 작성 및 서식
            ws.write_range("A1:D1", [["제품명", "가격", "수량", "총액"]])
            ws.apply_format("A1:D1", bold=True, bg_color=(200, 200, 200))
            
            # 2. 데이터 작성
            data = [
                ["사과", 1000, 10, 10000],
                ["바나나", 2000, 20, 40000],
                ["딸기", 3000, 30, 90000]
            ]
            ws.write_range("A2:D4", data)
            
            # 3. 숫자 서식 적용
            ws.apply_format("B2:D4", number_format="#,##0")
            
            # 4. 합계 행 추가
            ws.write_cell(5, 1, "합계")
            ws.apply_format("A5", bold=True)
            
            # 5. 검증
            assert ws.read("A1") == "제품명"
            assert ws.read("B2") == 1000.0
            assert ws.read("D3") == 40000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
