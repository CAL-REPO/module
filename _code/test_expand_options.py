# -*- coding: utf-8 -*-
"""xlwings expand 옵션 테스트"""

import xlwings as xw
import pandas as pd

excel_path = "M:/CALife/CAShop - 구매대행/01.SALES/01.All Product List.xlsx"
sheet_name = "Purchase"

print("="*80)
print("🔍 xlwings expand 옵션 테스트")
print("="*80)
print(f"File: {excel_path}")
print(f"Sheet: {sheet_name}")

# xlwings로 열기
app = xw.App(visible=False)
try:
    wb = app.books.open(excel_path)
    ws = wb.sheets[sheet_name]
    
    # 1. used_range 확인
    used_range = ws.used_range
    print(f"\n📌 Used Range: {used_range.address}")
    print(f"   Rows: {used_range.rows.count}, Columns: {used_range.columns.count}")
    
    # 2. expand 옵션 테스트
    expand_options = ["table", "down", "right"]
    
    for expand in expand_options:
        print(f"\n{'='*80}")
        print(f"🧪 Testing expand='{expand}'")
        print(f"{'='*80}")
        
        try:
            df = ws.range("A1").options(
                pd.DataFrame,
                header=True,
                index=False,
                expand=expand
            ).value
            
            if df is not None and isinstance(df, pd.DataFrame):
                print(f"✅ Success: {len(df)} rows x {len(df.columns)} columns")
                print(f"   Columns: {list(df.columns)[:10]}")  # 처음 10개만
                if len(df) > 0:
                    print(f"   First row: {df.iloc[0].to_dict()}")
            else:
                print(f"❌ Result is None or not DataFrame: {type(df)}")
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # 3. 수동으로 범위 지정 테스트
    print(f"\n{'='*80}")
    print(f"🧪 Testing manual range (A1:Z1000)")
    print(f"{'='*80}")
    
    try:
        df = ws.range("A1:Z1000").options(
            pd.DataFrame,
            header=True,
            index=False
        ).value
        
        if df is not None and isinstance(df, pd.DataFrame):
            # 빈 행 제거
            df = df.dropna(how="all").dropna(axis=1, how="all")
            print(f"✅ Success: {len(df)} rows x {len(df.columns)} columns")
            print(f"   Columns: {list(df.columns)}")
            if len(df) > 0:
                print(f"   First row sample: {dict(list(df.iloc[0].items())[:5])}")
        else:
            print(f"❌ Result is None or not DataFrame: {type(df)}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
finally:
    wb.close()
    app.quit()

print("\n" + "="*80)
print("✅ Test Complete")
print("="*80)
