# -*- coding: utf-8 -*-
"""Purchase 시트 직접 확인"""

import xlwings as xw

excel_path = "M:/CALife/CAShop - 구매대행/01.SALES/01.All Product List.xlsx"
sheet_name = "Sheet1"  # Purchase 대신 Sheet1 확인

print("="*80)
print("🔍 Excel Sheet Inspection")
print("="*80)
print(f"File: {excel_path}")
print(f"Sheet: {sheet_name}")

# xlwings로 열기
app = xw.App(visible=False)
try:
    wb = app.books.open(excel_path)
    ws = wb.sheets[sheet_name]
    
    # 사용된 범위 확인
    used_range = ws.used_range
    print(f"\nUsed range: {used_range.address}")
    print(f"Rows: {used_range.rows.count}")
    print(f"Columns: {used_range.columns.count}")
    
    # 첫 10행 확인
    print("\n" + "="*80)
    print("📋 First 10 rows")
    print("="*80)
    
    if used_range.rows.count > 0:
        # 헤더 (첫 행)
        header_range = ws.range(f"A1:{chr(64 + min(used_range.columns.count, 10))}1")
        headers = header_range.value
        if isinstance(headers, list):
            print(f"Headers: {headers}")
        else:
            print(f"Header: {headers}")
        
        # 데이터 행 (2-10행)
        for row_idx in range(2, min(11, used_range.rows.count + 1)):
            row_data = ws.range(f"A{row_idx}:{chr(64 + min(used_range.columns.count, 5))}{row_idx}").value
            print(f"Row {row_idx}: {row_data}")
    else:
        print("❌ Sheet is empty!")
    
finally:
    wb.close()
    app.quit()

print("\n" + "="*80)
print("✅ Inspection Complete")
print("="*80)
