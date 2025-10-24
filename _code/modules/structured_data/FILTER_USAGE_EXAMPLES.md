# structured_data FilterMixin - 사용 예시

## 1. 조건에 맞는 행 추출 (행 번호 포함)

### `filter_df_with_indices()` 함수

조건에 맞는 행을 필터링하고, 필터링된 행의 **0-based 정수 인덱스**를 함께 반환합니다.

```python
from structured_data import DataFrameOps
import pandas as pd

# 샘플 데이터
df = pd.DataFrame({
    'cas': ['123-45-6', '789-01-2', '345-67-8', '901-23-4'],
    'download': ['2025-01-15', '2025-01-15', None, '2025-01-16'],
    'translation': [None, '2025-01-16', None, None],
    'price': [1000, 2000, 1500, 3000]
})

# DataFrameOps 초기화
ops = DataFrameOps()

# 예시 1: Query string 사용
filtered_df, row_indices = ops.filter_df_with_indices(
    df, 
    "download.notna() & translation.isna()"
)

print("필터링된 DataFrame:")
print(filtered_df)
# 출력:
#         cas    download translation  price
# 0  123-45-6  2025-01-15        None   1000
# 3  901-23-4  2025-01-16        None   3000

print("\n행 인덱스 (0-based):")
print(row_indices)
# 출력: [0, 3]


# 예시 2: Callable 함수 사용
filtered_df, row_indices = ops.filter_df_with_indices(
    df,
    lambda row: row['price'] > 1500
)

print("\n필터링된 DataFrame:")
print(filtered_df)
# 출력:
#         cas    download  translation  price
# 1  789-01-2  2025-01-15   2025-01-16   2000
# 3  901-23-4  2025-01-16         None   3000

print("\n행 인덱스 (0-based):")
print(row_indices)
# 출력: [1, 3]
```

---

## 2. 특정 열의 값 추출 (행 번호 + 열 번호 포함)

### `filter_df_with_cell_positions()` 함수

조건에 맞는 행을 필터링하고, 특정 열의 **셀 위치 (row, col)**와 **값**을 함께 반환합니다.

```python
from structured_data import DataFrameOps
import pandas as pd

# 샘플 데이터 (XLOTO 시나리오)
df = pd.DataFrame({
    'date': ['2025-01-15', '2025-01-15', '2025-01-16', '2025-01-16'],
    'cas': ['123-45-6', '789-01-2', '345-67-8', '901-23-4'],
    'shop': ['Taobao', 'Coupang', 'Taobao', 'Coupang'],
    'download': ['2025-01-15', '2025-01-15', None, '2025-01-16'],
    'translation': [None, '2025-01-16', None, None],
})

# DataFrameOps 초기화
ops = DataFrameOps()

# 예시 1: CAS No 열 추출 (컬럼명 사용)
filtered_df, positions, values = ops.filter_df_with_cell_positions(
    df,
    "download.notna() & translation.isna()",
    "cas"  # 컬럼명
)

print("필터링된 DataFrame:")
print(filtered_df)
# 출력:
#          date       cas    shop    download translation
# 0  2025-01-15  123-45-6  Taobao  2025-01-15        None
# 3  2025-01-16  901-23-4  Coupang 2025-01-16        None

print("\n셀 위치 (row, col):")
print(positions)
# 출력: [(0, 1), (3, 1)]  # (행 번호, 열 번호) - 0-based

print("\nCAS No 값:")
print(values)
# 출력: ['123-45-6', '901-23-4']


# 예시 2: Translation 열 추출 (컬럼 인덱스 사용)
filtered_df, positions, values = ops.filter_df_with_cell_positions(
    df,
    lambda row: row['download'] is not None and row['translation'] is None,
    4  # translation 컬럼 인덱스
)

print("\n셀 위치 (row, col):")
print(positions)
# 출력: [(0, 4), (3, 4)]

print("\nTranslation 값:")
print(values)
# 출력: [None, None]
```

---

## XLOTO 실전 사용 예시

```python
from structured_data import DataFrameOps
from xl_utils import ExcelLoader
import pandas as pd

# Excel 로드
with ExcelLoader("config.yaml") as xl:
    ws = xl.get_worksheet()
    df = ws.to_dataframe()
    
    # DataFrameOps 초기화
    ops = DataFrameOps()
    
    # 1. 다운로드는 했지만 번역 안 된 행 찾기
    filtered_df, row_indices = ops.filter_df_with_indices(
        df,
        "download.notna() & translation.isna()"
    )
    
    print(f"번역이 필요한 행: {len(row_indices)}개")
    print(f"행 번호: {row_indices}")
    
    # 2. CAS No와 Translation 셀 위치 추출
    # CAS No 추출
    _, cas_positions, cas_values = ops.filter_df_with_cell_positions(
        df,
        "download.notna() & translation.isna()",
        "cas"
    )
    
    # Translation 컬럼 위치 추출
    _, trans_positions, _ = ops.filter_df_with_cell_positions(
        df,
        "download.notna() & translation.isna()",
        "translation"
    )
    
    # 3. 처리 결과를 Excel에 기록
    from datetime import datetime
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    for (row, col) in trans_positions:
        # Excel은 1-based이므로 +1 필요 (헤더도 고려하면 +2)
        ws.write_cell(row + 2, col + 1, current_date)
    
    print(f"✅ {len(trans_positions)}개 셀에 날짜 기록 완료")
```

---

## 함수 시그니처

### 1. `filter_df_with_indices()`
```python
def filter_df_with_indices(
    self,
    df: pd.DataFrame,
    condition: str | Callable[[pd.Series], bool]
) -> tuple[pd.DataFrame, list[int]]
```

**반환값:**
- `tuple[pd.DataFrame, list[int]]`
  - 필터링된 DataFrame
  - 행 인덱스 리스트 (0-based)

---

### 2. `filter_df_with_cell_positions()`
```python
def filter_df_with_cell_positions(
    self,
    df: pd.DataFrame,
    condition: str | Callable[[pd.Series], bool],
    column: str | int
) -> tuple[pd.DataFrame, list[tuple[int, int]], list[Any]]
```

**반환값:**
- `tuple[pd.DataFrame, list[tuple[int, int]], list[Any]]`
  - 필터링된 DataFrame
  - (row, col) 위치 리스트 (0-based)
  - 해당 셀의 값 리스트

---

## 주의사항

1. **인덱스 기준**: 모든 인덱스는 **0-based**입니다.
2. **Excel 변환**: Excel에 쓸 때는 `+1` (또는 헤더 포함 시 `+2`)이 필요합니다.
3. **컬럼 지정**: 
   - 문자열: 컬럼명 (예: `"cas"`)
   - 정수: 컬럼 인덱스 (예: `1`)
4. **조건 문자열**: pandas query 문법 사용 (예: `"age > 30 & city == 'Seoul'"`)
