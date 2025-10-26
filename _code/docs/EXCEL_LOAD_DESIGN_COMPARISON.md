# ExcelLoad 설계 비교: 파일 단위 vs App 단위

## 📋 Overview

ExcelLoad의 두 가지 설계 접근 방식 비교:
1. **파일 단위 (현재)**: `ExcelLoad(file_path)`
2. **App 단위 (초기)**: `ExcelLoad()` + `open_workbook(file_path)`

---

## 🎯 현재 설계: 파일 단위

### 구조
```python
class ExcelLoad:
    def __init__(self, file_path, cfg_like):
        self.file_path = file_path  # 파일 경로 필수
        
    def open(self):
        # App + Workbook 한번에 열기
        self.app_ctrl = XwApp(...)
        self.wb_ctrl = XwWb(self.app_ctrl.app, self.file_path, ...)
        
    def get_worksheet(self, sheet_name):
        return XwWs(self.wb_ctrl.book, sheet_name, ...)
```

### 사용 패턴
```python
# 단일 파일 처리
excel = ExcelLoad(file_path="data.xlsx", cfg_like="config.yaml")
with excel:
    ws = excel.get_worksheet("Sheet1")
    df = ws.to_dataframe()
```

### 장점
✅ **단순함**: 1파일 = 1객체  
✅ **명확함**: `ExcelLoad("data.xlsx")` - 무엇을 여는지 명확  
✅ **Context Manager**: `with excel:` - 자동 닫기  
✅ **ImageLoad 패턴과 일관성**: 동일한 사용법

### 단점
❌ **App 인스턴스 중복**: 파일마다 Excel.exe 실행  
❌ **리소스 낭비**: 여러 파일 처리 시 메모리/프로세스 중복  
❌ **Workbook 간 작업 불가**: 다른 App 인스턴스라 데이터 이동 불가

---

## 🏗️ 초기 설계: App 단위

### 구조
```python
class ExcelLoad:
    def __init__(self, cfg_like):
        # file_path 없음 - App만 제어
        
    def open(self):
        # App만 열기
        self.app_ctrl = XwApp(...)
        
    def open_workbook(self, file_path):
        # Workbook 열기
        wb_ctrl = XwWb(self.app_ctrl.app, file_path, ...)
        return wb_ctrl
        
    def get_worksheet(self, wb_ctrl, sheet_name):
        return XwWs(wb_ctrl.book, sheet_name, ...)
```

### 사용 패턴
```python
# 여러 파일 처리
excel = ExcelLoad(cfg_like="config.yaml")
with excel:
    wb1 = excel.open_workbook("file1.xlsx")
    wb2 = excel.open_workbook("file2.xlsx")
    
    ws1 = excel.get_worksheet(wb1, "Sheet1")
    ws2 = excel.get_worksheet(wb2, "Sheet1")
    
    df1 = ws1.to_dataframe()
    df2 = ws2.to_dataframe()
```

### 장점
✅ **App 인스턴스 1개**: Excel.exe 1번만 실행  
✅ **리소스 효율**: 프로세스 1개, 메모리 절약  
✅ **Workbook 간 작업 가능**: 시트 복사, 데이터 이동 가능  
✅ **확장성**: 여러 파일 동시 처리 용이

### 단점
❌ **복잡성**: `excel.open_workbook()` + `excel.get_worksheet()` 2단계  
❌ **상태 관리**: Workbook 목록 관리 필요  
❌ **불명확함**: `ExcelLoad()` - 무엇을 여는지 불명확  
❌ **ImageLoad와 불일치**: 패턴 불일치

---

## 📊 시나리오별 비교

### 시나리오 1: 단일 파일 처리 (XLOTO 패턴)

#### 현재 (파일 단위)
```python
excel = ExcelLoad(file_path="purchase.xlsx", cfg_like="config.yaml")
with excel:
    ws = excel.get_worksheet("Purchase")
    df = ws.to_dataframe()
    # 처리...
```
**평가**: ✅ 간단하고 명확

#### 초기 (App 단위)
```python
excel = ExcelLoad(cfg_like="config.yaml")
with excel:
    wb = excel.open_workbook("purchase.xlsx")
    ws = excel.get_worksheet(wb, "Purchase")
    df = ws.to_dataframe()
    # 처리...
```
**평가**: ⚠️ 1단계 더 복잡 (불필요)

---

### 시나리오 2: 여러 파일 비교

#### 현재 (파일 단위)
```python
excel1 = ExcelLoad(file_path="file1.xlsx", cfg_like="config.yaml")
excel2 = ExcelLoad(file_path="file2.xlsx", cfg_like="config.yaml")

with excel1, excel2:  # ⚠️ App 2개 생성
    ws1 = excel1.get_worksheet("Sheet1")
    ws2 = excel2.get_worksheet("Sheet1")
    
    df1 = ws1.to_dataframe()
    df2 = ws2.to_dataframe()
    
    # 데이터 비교
    diff = df1.compare(df2)
```
**평가**: ⚠️ App 중복, 하지만 데이터 비교는 가능

#### 초기 (App 단위)
```python
excel = ExcelLoad(cfg_like="config.yaml")
with excel:
    wb1 = excel.open_workbook("file1.xlsx")
    wb2 = excel.open_workbook("file2.xlsx")
    
    ws1 = excel.get_worksheet(wb1, "Sheet1")
    ws2 = excel.get_worksheet(wb2, "Sheet1")
    
    df1 = ws1.to_dataframe()
    df2 = ws2.to_dataframe()
    
    # 데이터 비교
    diff = df1.compare(df2)
```
**평가**: ✅ App 1개, 리소스 효율적

---

### 시나리오 3: Workbook 간 데이터 복사

#### 현재 (파일 단위)
```python
excel1 = ExcelLoad(file_path="source.xlsx", cfg_like="config.yaml")
excel2 = ExcelLoad(file_path="target.xlsx", cfg_like="config.yaml")

with excel1, excel2:
    ws1 = excel1.get_worksheet("Sheet1")
    ws2 = excel2.get_worksheet("Sheet1")
    
    # ❌ 불가능: 다른 App 인스턴스
    # ws2.range("A1").value = ws1.range("A1").value
    
    # 우회: DataFrame으로 복사
    df = ws1.to_dataframe()
    ws2.from_dataframe(df)
```
**평가**: ⚠️ 직접 복사 불가, DataFrame 경유 필요

#### 초기 (App 단위)
```python
excel = ExcelLoad(cfg_like="config.yaml")
with excel:
    wb1 = excel.open_workbook("source.xlsx")
    wb2 = excel.open_workbook("target.xlsx")
    
    ws1 = excel.get_worksheet(wb1, "Sheet1")
    ws2 = excel.get_worksheet(wb2, "Sheet1")
    
    # ✅ 가능: 동일 App 인스턴스
    ws2.range("A1").value = ws1.range("A1").value
    ws2.range("A1:Z100").value = ws1.range("A1:Z100").value
```
**평가**: ✅ 직접 복사 가능

---

## 🤔 결론

### 현재 설계 (파일 단위)가 적합한 경우
- ✅ **XLOTO 같은 단일 파일 처리**
- ✅ **간단한 스크립트**
- ✅ **DataFrame 중심 작업**
- ✅ **ImageLoad와 일관된 패턴**

### 초기 설계 (App 단위)가 적합한 경우
- ✅ **여러 파일 동시 처리**
- ✅ **Workbook 간 데이터 이동**
- ✅ **리소스 효율이 중요한 경우**
- ✅ **복잡한 Excel 자동화**

---

## 💡 권장사항

### Option 1: 현재 유지 (파일 단위)
**장점**: 단순함, XLOTO에 최적화  
**단점**: 여러 파일 처리 시 비효율

**대응**:
```python
# 여러 파일 처리 시 순차 처리
for file_path in file_paths:
    excel = ExcelLoad(file_path, cfg_like="config.yaml")
    with excel:
        ws = excel.get_worksheet("Sheet1")
        df = ws.to_dataframe()
        # 처리...
```

### Option 2: App 단위로 변경
**장점**: 확장성, 리소스 효율  
**단점**: 복잡성 증가, XLOTO에 오버엔지니어링

**대응**: XLOTO 사용 패턴 변경 필요

### Option 3: 하이브리드 (추천)
**ExcelLoad 2가지 모드 지원**:
```python
# 모드 1: 파일 단위 (기본)
excel = ExcelLoad(file_path="data.xlsx", cfg_like="config.yaml")

# 모드 2: App 단위 (고급)
excel = ExcelLoad(cfg_like="config.yaml")  # file_path 없음
with excel:
    wb1 = excel.open_workbook("file1.xlsx")
    wb2 = excel.open_workbook("file2.xlsx")
```

**구현**:
```python
class ExcelLoad:
    def __init__(
        self,
        file_path: Optional[Union[Path, str]] = None,
        cfg_like: Union[ExcelLoadPolicy, Path, str, dict, None] = None,
        **overrides
    ):
        self.file_path = Path(file_path) if file_path else None
        self.policy = self._load_config(cfg_like, **overrides)
        self._mode = "file" if file_path else "app"
        
    def open(self):
        self.app_ctrl = XwApp(...)
        
        if self._mode == "file":
            # 파일 모드: Workbook도 바로 열기
            self.wb_ctrl = XwWb(self.app_ctrl.app, self.file_path, ...)
        # App 모드: Workbook은 나중에 open_workbook()으로
        
    def open_workbook(self, file_path):
        """App 모드 전용"""
        if self._mode != "app":
            raise RuntimeError("open_workbook() requires app mode")
        wb_ctrl = XwWb(self.app_ctrl.app, file_path, ...)
        return wb_ctrl
        
    def get_worksheet(self, sheet_name_or_wb, sheet_name=None):
        """파일 모드 / App 모드 둘 다 지원"""
        if self._mode == "file":
            # 파일 모드: sheet_name만 받음
            return XwWs(self.wb_ctrl.book, sheet_name_or_wb, ...)
        else:
            # App 모드: wb_ctrl + sheet_name 받음
            wb_ctrl = sheet_name_or_wb
            return XwWs(wb_ctrl.book, sheet_name, ...)
```

---

## 📝 최종 결정 기준

1. **XLOTO만 고려한다면**: 현재 (파일 단위) 유지
2. **다른 스크립트도 고려한다면**: 하이브리드 구현
3. **복잡한 Excel 자동화 예정이라면**: App 단위로 변경

**추천**: 하이브리드 - 기존 XLOTO 코드는 그대로, 확장성도 확보
