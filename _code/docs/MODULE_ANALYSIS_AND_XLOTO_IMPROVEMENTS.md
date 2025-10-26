    # 공통 모듈 분석 및 XLOTO Adapter 개선 방안

**작성일**: 2025-10-25  
**분석 범위**: 모든 공통 모듈 (cfg_utils, oto, data_utils, fso_utils 등) + scripts/xloto/adapter

---

## 📋 목차

1. [공통 모듈 구조 분석](#1-공통-모듈-구조-분석)
2. [모듈별 SRP 준수 여부](#2-모듈별-srp-준수-여부)
3. [모듈 간 의존성 매핑](#3-모듈-간-의존성-매핑)
4. [각 모듈의 존재 의미](#4-각-모듈의-존재-의미)
5. [XLOTO Adapter 구조 분석](#5-xloto-adapter-구조-분석)
6. [XLOTO Adapter 개선 방안](#6-xloto-adapter-개선-방안)

---

## 1. 공통 모듈 구조 분석

### 1.1 모듈 계층 구조

```
modules/
├── 🔵 Infrastructure Layer (기반 유틸리티)
│   ├── path_utils/          # OS 경로 처리
│   ├── type_utils/          # 타입 추론
│   └── logs_utils/          # 로깅 시스템
│
├── 🟢 Data Processing Layer (데이터 처리)
│   ├── unify_utils/         # 정규화/해석 기반
│   ├── keypath_utils/       # KeyPath 접근 (unify_utils 확장)
│   ├── structured_io/       # YAML/JSON 파싱
│   ├── structured_data/     # DataFrame/DB 연산
│   └── data_utils/          # 레거시 dict/list/string 연산
│
├── 🟡 Configuration Layer (설정 관리)
│   └── cfg_utils/           # 통합 설정 로더 (v2 아키텍처)
│
├── 🟠 File System Layer (파일 시스템)
│   └── fso_utils/           # 파일 탐색/I/O/경로 빌드
│
├── 🔴 Domain Layer (도메인 로직)
│   ├── xl_utils/            # Excel 파일 처리
│   ├── image_utils/         # 이미지 처리
│   ├── translate_utils/     # 번역 처리
│   ├── font_utils/          # 폰트 처리
│   ├── color_utils/         # 색상 처리
│   └── crawl_utils/         # 웹 크롤링
│
└── 🟣 Application Layer (복합 파이프라인)
    └── oto/                 # OCR → Translate → Overlay
```

### 1.2 각 모듈 디렉토리 구조 패턴

**표준 패턴 (Adapter/EntryPoint 분리)**
```
module_name/
├── core/                    # 정책(Policy), 인터페이스, 타입
│   ├── policy.py           # Pydantic BaseModel 정책
│   ├── interface.py        # ABC 추상 클래스
│   └── types.py            # 타입 정의
├── adapter/                # 순수 로직 (Standalone)
│   └── {name}.py           # 핵심 비즈니스 로직
├── entry_point/            # YAML 기반 진입점 (선택적)
│   └── {name}.py           # YAML 로더 + Adapter 위임
├── services/               # 재사용 가능한 유틸리티
│   └── *.py                # Helper, Manager, Processor 등
├── configs/                # 기본 YAML 설정 (테스트용)
└── __init__.py             # Public API
```

**적용 모듈**:
- ✅ `cfg_utils`: Config (adapter) + ConfigLoader (entry_point)
- ✅ `oto`: OTO (adapter) - EntryPoint 없음 (외부에서 ConfigLoader 사용)
- ✅ `image_utils`: ImageLoad, ImageTextRecognize, ImageOverlay (adapters)
- ✅ `xl_utils`: ExcelLoad (adapter)
- ✅ `translate_utils`: Translate (adapter)

---

## 2. 모듈별 SRP 준수 여부

### 2.1 ✅ SRP 우수 모듈

#### **cfg_utils** ⭐⭐⭐⭐⭐
**책임**: 설정 로드 및 병합 (YAML/Dict/BaseModel → KeyPathState)

**구조**:
```python
# Adapter (Standalone)
Config:
  - 책임: 설정 소스 로드, env 처리, state 병합
  - 의존: keypath_utils, structured_io

# EntryPoint (YAML 정책)
ConfigLoader:
  - 책임: YAML 정책 파일 로드 + Config 위임
  - 의존: Config (adapter)

# Services (재사용)
UnifiedSource:        # 소스 타입 자동 판단 (BaseModel/Dict/YAML)
StateConverter:       # KeyPathState → dict/BaseModel 변환
SectionExtractor:     # Policy.name 기반 section 추출 (Cascading Priority)
PolicyLoader:         # YAML → Policy 파싱
EnvProcessor:         # env/env_os 처리
```

**SRP 평가**:
- ✅ **단일 책임**: 설정 로드만 담당
- ✅ **명확한 계층**: core → adapter → entry_point → services
- ✅ **재사용성**: Config는 Standalone, ConfigLoader는 YAML 정책용
- ✅ **확장성**: UnifiedSource로 타입 자동 판단

**개선 불필요**: 현재 구조가 이상적

---

#### **oto** ⭐⭐⭐⭐⭐
**책임**: OCR → Translate → Overlay 파이프라인 조합

**구조**:
```python
# Adapter (Standalone)
OTO:
  - 책임: 3개 모듈 조합 (ImageTextRecognize, Translate, ImageOverlay)
  - 의존: cfg_utils.SectionExtractor, logs_utils, image_utils, translate_utils
  - 특징: Pass-through 패턴 (cfg_like를 각 모듈에 전달)

# 파이프라인 흐름
1. ImageLoad.run(source_path)           → PIL.Image
2. ImageTextRecognize.run(image)        → List[OCRItem]
3. Translate.run(texts)                 → Dict[str, str]
4. OCRItem.to_overlay_item()            → List[OverlayItemPolicy]
5. ImageOverlay.run(image, items)       → Final Image
```

**SRP 평가**:
- ✅ **단일 책임**: 파이프라인 조합만 담당 (각 모듈의 세부 로직 위임)
- ✅ **Pass-through**: cfg_like를 SectionExtractor로 추출 후 각 모듈에 전달
- ✅ **Lazy Loading**: 각 Adapter는 첫 사용 시 초기화
- ✅ **Cascading Priority**: 개별 cfg_like > merged section > None

**개선 불필요**: 현재 구조가 이상적

---

#### **keypath_utils** ⭐⭐⭐⭐
**책임**: KeyPath 기반 nested dict 접근 및 상태 관리

**구조**:
```python
# Core
KeyPathAccessor:      # KeyPath 파싱 (a__b__c)
KeyPathStatePolicy:   # State 정책

# Services
KeyPathDict:          # KeyPath 기반 dict 접근 (get/set)
KeyPathState:         # 상태 관리 (merge, track changes)
KeyPathNormalizer:    # KeyPath 정규화
KeyPathVarsResolver:  # 변수 해석 ({{var}}, ${var})
KeyPathMerger:        # Deep/Shallow merge
```

**SRP 평가**:
- ✅ **단일 책임**: KeyPath 접근 및 상태 관리
- ✅ **명확한 분리**: Dict 접근 vs State 관리
- ⚠️ **일부 중첩**: Mixin 구조가 복잡 (core/mixin/services 간 의존성)

**개선 제안**:
- Mixin 구조 단순화 (일부 Mixin을 Service로 이동)

---

#### **structured_io** ⭐⭐⭐⭐⭐
**책임**: YAML/JSON 파싱 및 덤프 (통합 인터페이스)

**구조**:
```python
# Core
BaseParser / BaseDumper:  # 추상 인터페이스
BaseParserPolicy:         # 파싱 정책 (enable_env, enable_include 등)

# Formats
YamlParser / YamlDumper:  # YAML 처리
JsonParser / JsonDumper:  # JSON 처리

# FileIO
StructuredFileIO:         # 파일 I/O 통합 (Parser + Dumper)
```

**SRP 평가**:
- ✅ **단일 책임**: 구조화된 데이터 파싱/덤프
- ✅ **통합 인터페이스**: YAML/JSON 동일 API
- ✅ **정책 기반**: enable_env, enable_placeholder 등 유연한 제어

**개선 불필요**: 현재 구조가 이상적

---

#### **fso_utils** ⭐⭐⭐⭐
**책임**: 파일 시스템 연산 (탐색, I/O, 경로 빌드)

**구조**:
```python
# Core
FSOOps:               # 파일 연산 통합 (exists, read, write)
FSOExplorer:          # 파일 탐색 (find, filter)
FSOPathBuilder:       # 경로 생성 (save 정책 기반)

# Adapters
LocalFileSaver:       # 로컬 파일 저장
FSOPathBuilderAdapter: # 경로 빌드 어댑터

# Policies
FSOOpsPolicy:         # 파일 연산 정책
FSOExplorerPolicy:    # 탐색 정책
FSOIOPolicy:          # I/O 정책
```

**SRP 평가**:
- ✅ **단일 책임**: 파일 시스템 연산
- ✅ **명확한 분리**: Ops (연산) vs Explorer (탐색) vs PathBuilder (경로)
- ✅ **정책 기반**: 각 클래스마다 독립적인 Policy

**개선 불필요**: 현재 구조가 이상적

---

### 2.2 ⚠️ SRP 개선 필요 모듈

#### **data_utils** ⭐⭐⭐
**책임**: Dict/List/String/Geometry 연산

**문제점**:
- ❌ **레거시 의존**: structured_data를 import하지만 자체 DictOps도 보유
- ❌ **역할 중복**: structured_data와 기능 중복
- ❌ **불명확한 경계**: 언제 data_utils를, 언제 structured_data를 사용하는지 불명확

**구조**:
```python
# data_utils/__init__.py
from structured_data import BaseOperationsPolicy, DataFrameOps, SQLiteKVStore  # 외부 의존
from data_utils.services.dict_ops import DictOps       # 자체 구현
from data_utils.services.list_ops import ListOps
from data_utils.services.string_ops import StringOps
from data_utils.services.geometry_ops import GeometryOps
```

**개선 제안**:
1. **DictOps/ListOps 제거**: structured_data로 통합
2. **StringOps/GeometryOps 유지**: 도메인 특화 연산
3. **data_utils 역할 재정의**: "도메인 특화 데이터 연산" (structured_data의 확장)

---

#### **structured_data** ⭐⭐⭐⭐
**책임**: DataFrame/DB/Dict/List 연산 (Mixin 기반)

**문제점**:
- ⚠️ **Mixin 과다**: 9개의 Mixin (Connection, Schema, Cache, Clean, Normalize, Filter, Update, FromDict, KVOperations)
- ⚠️ **역할 혼재**: I/O Mixin + Transform Mixin + Ops Mixin이 한 모듈에

**구조**:
```python
# Role-based Mixins
ConnectionMixin, SchemaMixin, CacheMixin      # I/O
CleanMixin, NormalizeMixin, FilterMixin       # Transform
FromDictMixin                                 # Create
KVOperationsMixin, KeyGenerationMixin         # Ops

# Composites
SQLiteKVStore:    ConnectionMixin + SchemaMixin + KVOperationsMixin
DataFrameOps:     FilterMixin + CleanMixin + NormalizeMixin
```

**개선 제안**:
1. **Mixin 그룹화**: I/O, Transform, Ops를 별도 하위 패키지로 분리
2. **Composite 패턴 강화**: 자주 사용되는 조합을 미리 정의
3. **문서화 강화**: 어떤 Mixin을 조합해야 하는지 가이드

---

#### **xl_utils** ⭐⭐⭐
**책임**: Excel 파일 접근 및 셀 조작

**문제점**:
- ⚠️ **외부 의존**: openpyxl, xlwings (COM 객체)
- ⚠️ **플랫폼 종속**: Windows 전용 (xlwings)
- ⚠️ **복잡한 상태 관리**: XwApp (Excel 인스턴스) 생명주기

**구조**:
```python
# Adapter
ExcelLoad:
  - 책임: Excel 파일 로드, 워크시트 접근, 셀 읽기/쓰기
  - 의존: xlwings (COM), openpyxl (fallback)

# Services
XwApp:            # Excel 애플리케이션 관리
XwWb:             # Workbook 관리
XwWs:             # Worksheet 관리 (cell_ops 포함)
ColumnResolver:   # 컬럼명 해석 (별칭 지원)
```

**개선 제안**:
1. **플랫폼 분리**: XwApp (Windows) vs OpenpyxlAdapter (크로스 플랫폼)
2. **Context Manager 강화**: with ExcelLoad() 패턴 명확화
3. **ColumnResolver 독립**: xl_utils → data_utils로 이동 (범용성)

---

### 2.3 🔄 리팩토링 우선순위

| 순위 | 모듈 | 문제 | 개선 방향 |
|------|------|------|----------|
| 🔥 1 | **data_utils** | structured_data와 기능 중복 | DictOps/ListOps 제거, 역할 재정의 |
| ⚡ 2 | **structured_data** | Mixin 과다, 역할 혼재 | Mixin 그룹화 (I/O/Transform/Ops) |
| ⚡ 3 | **keypath_utils** | Mixin 구조 복잡 | 일부 Mixin을 Service로 이동 |
| ✅ 4 | **xl_utils** | 플랫폼 종속, 외부 의존 | XwApp vs OpenpyxlAdapter 분리 |

---

## 3. 모듈 간 의존성 매핑

### 3.1 의존성 그래프

```
Infrastructure Layer (기반)
    path_utils ─┐
    type_utils ─┼─> 모든 모듈이 사용 가능
    logs_utils ─┘

Data Processing Layer (데이터)
    unify_utils
        ↓
    keypath_utils (unify_utils 확장)
        ↓
    structured_io (keypath_utils 사용)
        ↓
    structured_data (structured_io 사용)
        ↓
    data_utils (structured_data 사용 - 레거시)

Configuration Layer (설정)
    cfg_utils
        ├─> keypath_utils    (KeyPathState 관리)
        ├─> structured_io    (YAML 파싱)
        └─> logs_utils       (로깅)

File System Layer (파일)
    fso_utils
        └─> path_utils       (경로 처리)

Domain Layer (도메인)
    xl_utils, image_utils, translate_utils, font_utils, color_utils
        ├─> cfg_utils        (설정 로드)
        ├─> logs_utils       (로깅)
        └─> fso_utils        (파일 I/O)

Application Layer (복합)
    oto
        ├─> cfg_utils        (설정 병합)
        ├─> image_utils      (ImageLoad, ImageTextRecognize, ImageOverlay)
        └─> translate_utils  (Translate)
```

### 3.2 핵심 의존 관계

#### **cfg_utils의 의존성**
```python
# cfg_utils/adapter/config.py
from modules.keypath_utils import KeyPathState, KeyPathDict  # State 관리
```

#### **oto의 의존성**
```python
# oto/adapter/oto.py
from cfg_utils.services.section_extractor import SectionExtractor  # Section 추출
from logs_utils import LogManager                                  # 로깅
from image_utils.adapter import ImageLoad, ImageTextRecognize, ImageOverlay
from translate_utils.adapter import Translate
```

#### **xloto의 의존성**
```python
# scripts/xloto/adapter/xloto.py
from cfg_utils.services.section_extractor import SectionExtractor  # Section 추출
from xl_utils.services import ColumnResolver                       # 컬럼 해석
from structured_data import FilterMixin                            # DataFrame 필터
from oto.adapter.oto import Oto                                    # OTO 파이프라인
```

### 3.3 순환 참조 검증

✅ **순환 참조 없음** - 모든 의존성이 단방향

```
Infrastructure → Data Processing → Configuration → File System → Domain → Application
```

---

## 4. 각 모듈의 존재 의미

### 4.1 Infrastructure Layer

#### **path_utils**
- **존재 의미**: OS별 경로 처리 통일 (Windows/Linux/macOS)
- **제공 가치**: home(), downloads(), resolve() - 크로스 플랫폼
- **사용처**: 모든 파일 I/O 모듈

#### **type_utils**
- **존재 의미**: URL/파일 타입 자동 추론
- **제공 가치**: infer_type("photo.jpg") → "image"
- **사용처**: crawl_utils, image_utils

#### **logs_utils**
- **존재 의미**: loguru 기반 통합 로깅 시스템
- **제공 가치**: LogPolicy + LogManager (context 주입)
- **사용처**: 모든 모듈 (표준 로깅)

---

### 4.2 Data Processing Layer

#### **unify_utils**
- **존재 의미**: 데이터 정규화 및 변수 해석 (기반)
- **제공 가치**: VarsResolver (${var}, {{context}})
- **차별점**: 단순 참조 해석 (KeyPath 미지원)

#### **keypath_utils**
- **존재 의미**: unify_utils 확장 (KeyPath 지원)
- **제공 가치**: a__b__c 표기법으로 nested dict 접근
- **차별점**: KeyPathState (상태 추적), KeyPathMerger (Deep merge)

#### **structured_io**
- **존재 의미**: YAML/JSON 통합 파싱
- **제공 가치**: enable_env, enable_placeholder 정책
- **차별점**: BaseParser/BaseDumper 인터페이스 (확장 가능)

#### **structured_data**
- **존재 의미**: DataFrame/DB/Dict/List 연산 (Mixin 조합)
- **제공 가치**: SQLiteKVStore, DataFrameOps (Composite 패턴)
- **차별점**: Role-based Mixin (I/O, Transform, Ops)

#### **data_utils**
- **존재 의미**: 레거시 dict/list/string 연산
- **제공 가치**: GeometryOps (도메인 특화)
- **문제점**: structured_data와 역할 중복
- **개선 방향**: "도메인 특화 연산"으로 재정의

---

### 4.3 Configuration Layer

#### **cfg_utils**
- **존재 의미**: 설정 로드 및 병합 (단일 진입점)
- **제공 가치**: ConfigLoader (YAML 정책) + Config (Standalone)
- **차별점**: Cascading Priority, SectionExtractor, Pass-through

**핵심 기능**:
1. **타입 자동 판단**: BaseModel/Dict/YAML → 자동 처리
2. **우선순위 병합**: base → override → env → resolve
3. **Section 추출**: Policy.name 기반 (하드코딩 없음)
4. **Pass-through**: 병합 dict를 각 모듈에 전달

---

### 4.4 File System Layer

#### **fso_utils**
- **존재 의미**: 파일 시스템 연산 통합
- **제공 가치**: FSOOps (연산), FSOExplorer (탐색), FSOPathBuilder (경로)
- **차별점**: 정책 기반 (FSOOpsPolicy, FSOExplorerPolicy)

---

### 4.5 Domain Layer

#### **xl_utils**
- **존재 의미**: Excel 파일 접근 및 셀 조작
- **제공 가치**: ExcelLoad (xlwings 기반), ColumnResolver
- **문제점**: Windows 전용 (xlwings COM)

#### **image_utils**
- **존재 의미**: 이미지 로드, OCR, 오버레이
- **제공 가치**: ImageLoad, ImageTextRecognize, ImageOverlay (adapters)
- **차별점**: EasyOCR/RapidOCR 통합, 폰트/색상 정책

#### **translate_utils**
- **존재 의미**: 번역 API 통합
- **제공 가치**: Translate (Google, DeepL, OpenAI)
- **차별점**: 캐싱 (SQLiteKVStore), 세그먼트 단위

---

### 4.6 Application Layer

#### **oto**
- **존재 의미**: OCR → Translate → Overlay 파이프라인
- **제공 가치**: 3개 모듈 조합 (ImageTextRecognize, Translate, ImageOverlay)
- **차별점**: Pass-through, Lazy Loading, Cascading Priority

---

## 5. XLOTO Adapter 구조 분석

### 5.1 현재 구조

```python
# scripts/xloto/adapter/xloto.py
class XlOto:
    """Excel + OTO 파이프라인
    
    Step 1: Excel에서 CAS No 추출 (FilterMixin + ColumnResolver)
    Step 2: OTO 처리 (Oto.run)
    Step 3: Excel 업데이트
    """
    
    def __init__(self, cfg_like=None, *, log_manager=None, **overrides):
        # Config 준비
        merged_config = cfg_like or {}
        
        # Excel 섹션 추출
        self._cfg_excel = SectionExtractor.extract(
            merged_config=merged_config, 
            section_name='excel'  # ⚠️ 하드코딩
        )
        
        # OTO는 전체 config 전달
        self._cfg_oto = merged_config
        
        # Policy 생성
        self.policy = XlOtoPolicy(**merged_config)
        
        # Logger 초기화
        self.log = ...
        
        # 지연 초기화
        self._oto = None
        self._image_manager = None
        self._df_filter = FilterMixin()
        self._column_resolver = ColumnResolver(aliases)
    
    def run(self, *, excel_load=None, **overrides):
        # Step 1: Extract CAS No from Excel
        df = excel_load.to_dataframe(...)
        filtered_df, positions, values = self._df_filter.filter_df_with_cell_positions(...)
        
        # Step 2: Process CAS images
        oto = self.get_oto()
        for cas_item in cas_list:
            missing_images = image_manager.get_missing_images(cas_no)
            for img_path in missing_images:
                oto_result = oto.run(source_path=img_path, **overrides)
                final_image.save(output_path)
        
        # Step 3: Update Excel
        excel_load.write_cell(row, col_idx, current_date)
```

### 5.2 구조 분석

#### ✅ 잘된 점

1. **Lazy Loading**
   - `_oto`, `_image_manager` 첫 사용 시 초기화
   - 메모리 효율적

2. **SectionExtractor 사용**
   - Excel 섹션 추출 (`self._cfg_excel`)
   - cfg_utils 표준 패턴

3. **ColumnResolver 활용**
   - 별칭 기반 컬럼 해석 (`cas`, `download`, `translation`)
   - 유연한 Excel 스키마

4. **FilterMixin 활용**
   - DataFrame 필터링 + 셀 위치 추출
   - structured_data 재사용

5. **Pass-through 패턴**
   - `overrides`를 OTO에 전달
   - 런타임 오버라이드 지원

#### ❌ 개선 필요 사항

1. **하드코딩된 Section 이름**
   ```python
   self._cfg_excel = SectionExtractor.extract(
       merged_config=merged_config, 
       section_name='excel'  # ⚠️ 하드코딩
   )
   ```
   - **문제**: Policy.name을 사용하지 않음
   - **개선**: `SectionExtractor.extract_batch()` 사용

2. **excel_load 외부 주입**
   ```python
   def run(self, *, excel_load=None, **overrides):
   ```
   - **문제**: XlOto가 ExcelLoad를 생성하지 않음
   - **개선**: XlOto 내부에서 ExcelLoad 관리

3. **ImageFileManager 역할 불명확**
   ```python
   self._image_manager = ImageFileManager(
       public_img_dir=...,
       origin_dirname=...,
       translated_dirname=...
   )
   ```
   - **문제**: ImageFileManager가 scripts/xloto/services에만 존재
   - **개선**: fso_utils 또는 image_utils로 이동 (재사용성)

4. **Excel 업데이트 로직 분리 필요**
   ```python
   # Step 3: Update Excel
   for cas_item in successful_cas:
       excel_load.write_cell(row, col_idx, current_date)
   ```
   - **문제**: 비즈니스 로직이 Adapter에 혼재
   - **개선**: ExcelUpdater Service 분리

5. **OTO 결과 검증 부족**
   ```python
   if oto_result.get('success'):
       final_image = oto_result.get('image')
       if final_image:
           final_image.save(output_path)
   ```
   - **문제**: 에러 처리가 단순 (로그만 출력)
   - **개선**: 재시도 로직, 에러 누적, 부분 성공 처리

6. **설정 병합 로직 중복**
   ```python
   merged_config = cfg_like or {}
   if overrides:
       override_dict = KeyPathDict.to_nested_dict(overrides)
       merged_config = {**merged_config, **override_dict}
   ```
   - **문제**: OTO와 동일한 병합 로직 (중복)
   - **개선**: cfg_utils.services.OverrideProcessor 재사용

---

## 6. XLOTO Adapter 개선 방안

### 6.1 개선된 구조 제안

```python
# scripts/xloto/adapter/xloto.py (개선안)
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime

from cfg_utils.services.section_extractor import SectionExtractor
from cfg_utils.services.override_processor import OverrideProcessor
from logs_utils import LogManager
from xl_utils.adapter.excel_load import ExcelLoad
from xl_utils.core.policy import ExcelLoadPolicy
from structured_data import FilterMixin
from oto.adapter.oto import Oto

from xloto.core.policy import XlOtoPolicy
from xloto.services.image_file_manager import ImageFileManager
from xloto.services.excel_updater import ExcelUpdater  # 신규
from xloto.services.cas_extractor import CasExtractor  # 신규


class XlOto:
    """Excel + OTO 파이프라인 (개선안)
    
    Architecture:
    1. ConfigLoader가 모든 section 병합 (excel, oto, paths, log)
    2. SectionExtractor.extract_batch()로 section 추출 (Policy.name 기반)
    3. ExcelLoad 내부 생성 (외부 주입 불필요)
    4. CasExtractor Service로 CAS No 추출 로직 분리
    5. ExcelUpdater Service로 Excel 업데이트 로직 분리
    
    Pass-through Pattern:
    - cfg_like를 SectionExtractor로 추출
    - 각 모듈에 추출된 cfg_like 전달
    
    Lazy Loading:
    - ExcelLoad, Oto, ImageFileManager 첫 사용 시 초기화
    
    Example:
        >>> # 외부에서 ConfigLoader 실행 (권장)
        >>> from cfg_utils import ConfigLoader
        >>> config = ConfigLoader(
        ...     config_loader_cfg_path="configs/loader/config_loader_xloto.yaml",
        ...     env_os=["CASHOP_PATHS"]
        ... )
        >>> xloto = XlOto(cfg_like=config.to_dict(), log_manager=log_manager)
        >>> result = xloto.run(excel_path="data.xlsx")
        
        >>> # Runtime override
        >>> result = xloto.run(
        ...     excel_path="data.xlsx",
        ...     excel__xw_app__visible=True,
        ...     oto__image_overlay__save__directory="output/cas123"
        ... )
    """
    
    def __init__(
        self,
        cfg_like: Union[dict, None] = None,
        *,
        cfg_like_excel: Union[BaseModel, Path, str, dict, None] = None,
        cfg_like_oto: Union[BaseModel, Path, str, dict, None] = None,
        log_manager: Optional[LogManager] = None,
        **overrides: Any
    ):
        """Pass-through 패턴 초기화 (Zero Hard-coding)
        
        Architecture:
            1. ConfigLoader가 모든 section 병합
            2. OverrideProcessor로 runtime overrides 병합
            3. SectionExtractor.extract_batch()로 section 추출
            4. 각 모듈에 추출된 cfg_like 전달
        
        Args:
            cfg_like: 병합된 dict (ConfigLoader.to_dict() 결과)
            cfg_like_excel: ExcelLoadPolicy 개별 설정 (우선순위 1)
            cfg_like_oto: OTOPolicy 개별 설정 (우선순위 1)
            log_manager: LogManager 인스턴스
            **overrides: 런타임 오버라이드 (excel__xw_app__visible=True 등)
        
        Cascading Priority:
            1. cfg_like_excel (개별 cfg_like) - 최우선
            2. cfg_like["excel"] (병합 dict의 section) - Policy.name으로 추출
            3. None (Pydantic 기본값) - fallback
        """
        # ========================================
        # Config 준비
        # ========================================
        merged_config = cfg_like or {}
        
        # Runtime overrides 병합 (OverrideProcessor 사용)
        if overrides:
            merged_config = OverrideProcessor.merge_overrides(
                base_config=merged_config,
                overrides=overrides
            )
        
        # ========================================
        # SectionExtractor.extract_batch() (Zero Hard-coding)
        # ========================================
        extracted = SectionExtractor.extract_batch(
            merged_config=merged_config,
            individual_cfgs={
                ExcelLoadPolicy: cfg_like_excel,
                # OTO는 전체 config 전달 (Oto 내부에서 section 추출)
            }
        )
        
        # Policy.name으로 추출 (하드코딩 없음)
        self._cfg_excel = extracted[
            SectionExtractor.get_policy_name(ExcelLoadPolicy)
        ]
        
        # OTO는 전체 config 전달 (Oto가 내부에서 section 추출)
        if cfg_like_oto:
            self._cfg_oto = cfg_like_oto
        else:
            self._cfg_oto = merged_config
        
        # ========================================
        # XlOtoPolicy 생성
        # ========================================
        try:
            self.policy = XlOtoPolicy(**merged_config)
        except Exception:
            self.policy = XlOtoPolicy()
        
        # ========================================
        # Logger 초기화
        # ========================================
        if log_manager:
            self.log = log_manager.logger
            self._parent_log_manager = log_manager
        elif self.policy.log:
            self._parent_log_manager = LogManager(self.policy.log)
            self.log = self._parent_log_manager.logger
        else:
            self._parent_log_manager = None
            self.log = LogManager({"enabled": False}).logger
        
        # ========================================
        # Lazy Loading (첫 사용 시 초기화)
        # ========================================
        self._excel_load: Optional[ExcelLoad] = None
        self._oto: Optional[Oto] = None
        self._image_manager: Optional[ImageFileManager] = None
        self._cas_extractor: Optional[CasExtractor] = None
        self._excel_updater: Optional[ExcelUpdater] = None
        
        self.log.debug("XlOto adapter initialized")
    
    # ==========================================================================
    # Lazy Loading Properties
    # ==========================================================================
    
    @property
    def excel_load(self) -> ExcelLoad:
        """ExcelLoad Adapter lazy-loading"""
        if self._excel_load is None:
            self._excel_load = ExcelLoad(
                cfg_like=self._cfg_excel,  # type: ignore
                log_manager=self._parent_log_manager,
            )
        return self._excel_load
    
    @property
    def oto(self) -> Oto:
        """Oto Adapter lazy-loading"""
        if self._oto is None:
            self._oto = Oto(
                cfg_like=self._cfg_oto,  # type: ignore
                log_manager=self._parent_log_manager,
            )
            self.log.debug("Oto adapter created")
        return self._oto
    
    @property
    def image_manager(self) -> ImageFileManager:
        """ImageFileManager lazy-loading"""
        if self._image_manager is None:
            self._image_manager = ImageFileManager(
                public_img_dir=self.policy.paths.public_img_dir,
                origin_dirname=self.policy.paths.origin_dirname,
                translated_dirname=self.policy.paths.translated_dirname
            )
        return self._image_manager
    
    @property
    def cas_extractor(self) -> CasExtractor:
        """CasExtractor Service lazy-loading"""
        if self._cas_extractor is None:
            self._cas_extractor = CasExtractor(
                aliases=self.policy.excel.aliases if hasattr(self.policy, 'excel') else {}
            )
        return self._cas_extractor
    
    @property
    def excel_updater(self) -> ExcelUpdater:
        """ExcelUpdater Service lazy-loading"""
        if self._excel_updater is None:
            self._excel_updater = ExcelUpdater()
        return self._excel_updater
    
    # ==========================================================================
    # Main Pipeline
    # ==========================================================================
    
    def run(
        self,
        excel_path: Union[Path, str],
        sheet_name: Optional[str] = None,
        **overrides: Any
    ) -> Dict[str, Any]:
        """XLOTO Pipeline 실행 (개선안)
        
        Pipeline Flow:
            1. ExcelLoad로 Excel 파일 로드
            2. CasExtractor로 CAS No 추출 (FilterMixin + ColumnResolver)
            3. ImageFileManager로 미번역 이미지 탐색
            4. Oto.run()으로 OTO 파이프라인 실행
            5. ExcelUpdater로 Excel 업데이트
        
        Args:
            excel_path: Excel 파일 경로
            sheet_name: 시트 이름 (None이면 active sheet)
            **overrides: 런타임 오버라이드
                excel__xw_app__visible=True
                oto__image_overlay__save__directory="output/cas123"
        
        Returns:
            결과 딕셔너리:
            {
                "success": bool,
                "total_cas": int,
                "processed_cas": int,
                "cas_results": List[Dict],
                "error": Optional[str]
            }
        
        Example:
            >>> xloto = XlOto(cfg_like=config.to_dict())
            >>> result = xloto.run(
            ...     excel_path="data.xlsx",
            ...     excel__xw_app__visible=True,
            ...     oto__image_overlay__save__directory="output"
            ... )
        """
        result = {
            "success": False,
            "total_cas": 0,
            "processed_cas": 0,
            "cas_results": [],
            "error": None
        }
        
        try:
            self.log.info("="*80)
            self.log.info("XLOTO Pipeline Starting")
            self.log.info("="*80)
            
            # ================================================================
            # Step 1: Load Excel (ExcelLoad Adapter)
            # ================================================================
            self.log.info("[1/4] Loading Excel file...")
            
            with self.excel_load as xl:
                ws = xl.get_worksheet(excel_path, sheet_name)
                df = ws.to_dataframe(anchor="A1", header=True, index=False)
                
                self.log.success(f"  Loaded DataFrame: {len(df)} rows")
                
                # ============================================================
                # Step 2: Extract CAS No (CasExtractor Service)
                # ============================================================
                self.log.info("[2/4] Extracting CAS No from Excel...")
                
                cas_list = self.cas_extractor.extract(df)
                
                self.log.success(f"  Extracted {len(cas_list)} CAS No")
                
                if not cas_list:
                    result["success"] = True
                    return result
                
                result["total_cas"] = len(cas_list)
                
                # ============================================================
                # Step 3: Process CAS images (Oto + ImageFileManager)
                # ============================================================
                self.log.info(f"[3/4] Processing {len(cas_list)} CAS No...")
                
                processed_count = 0
                cas_results = []
                
                for idx, cas_item in enumerate(cas_list, 1):
                    cas_no = cas_item["cas_no"]
                    self.log.info(f"[{idx}/{len(cas_list)}] Processing: {cas_no}")
                    
                    # Find missing images
                    missing_images = self.image_manager.get_missing_images(cas_no)
                    if not missing_images:
                        self.log.info("  No images to process")
                        cas_results.append({
                            "cas_no": cas_no,
                            "success": True,
                            "processed_count": 0
                        })
                        continue
                    
                    self.log.info(f"  Found {len(missing_images)} images")
                    
                    # Process each image with Oto
                    success_count = 0
                    for img_idx, img_path in enumerate(missing_images, 1):
                        self.log.info(f"  [{img_idx}/{len(missing_images)}] {img_path.name}")
                        
                        try:
                            # OTO Pipeline
                            oto_result = self.oto.run(
                                source_path=img_path,
                                **overrides
                            )
                            
                            if oto_result.get("success"):
                                final_image = oto_result.get("image")
                                if final_image:
                                    # Save translated image
                                    output_dir = self.image_manager.get_translated_dir(cas_no)
                                    output_dir.mkdir(parents=True, exist_ok=True)
                                    output_path = output_dir / img_path.name
                                    final_image.save(output_path, quality=95)
                                    self.log.success(f"    Saved: {output_path.name}")
                                    success_count += 1
                            else:
                                self.log.error(f"    Failed: {oto_result.get('error')}")
                        
                        except Exception as e:
                            self.log.error(f"    Error: {e}")
                    
                    self.log.success(f"  Processed: {success_count}/{len(missing_images)}")
                    
                    if success_count > 0:
                        processed_count += 1
                        cas_results.append({
                            "cas_no": cas_no,
                            "success": True,
                            "processed_count": success_count,
                            "translation_row": cas_item.get("translation_row"),
                            "translation_col": cas_item.get("translation_col")
                        })
                
                result["processed_cas"] = processed_count
                result["cas_results"] = cas_results
                
                # ============================================================
                # Step 4: Update Excel (ExcelUpdater Service)
                # ============================================================
                if processed_count > 0:
                    self.log.info("[4/4] Updating Excel...")
                    
                    updated_count = self.excel_updater.update(
                        worksheet=ws,
                        cas_results=cas_results,
                        date_value=datetime.now().strftime("%Y-%m-%d")
                    )
                    
                    self.log.success(f"  Updated {updated_count} cells")
                
                result["success"] = True
                
            self.log.info("="*80)
            self.log.success("XLOTO Pipeline Completed")
            self.log.info(f"   Total: {result['total_cas']}")
            self.log.info(f"   Processed: {result['processed_cas']}")
            self.log.info("="*80)
        
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            self.log.error(result["error"])
            
            import traceback
            self.log.error(traceback.format_exc())
        
        return result
```

### 6.2 신규 Service 클래스

#### **CasExtractor** (xloto/services/cas_extractor.py)
```python
# scripts/xloto/services/cas_extractor.py
"""CAS No 추출 Service (FilterMixin + ColumnResolver)"""

from typing import Dict, List, Tuple
import pandas as pd
from structured_data import FilterMixin
from xl_utils.services import ColumnResolver


class CasExtractor:
    """DataFrame에서 CAS No 추출 (FilterMixin + ColumnResolver)
    
    책임:
    1. ColumnResolver로 컬럼명 해석 (aliases 지원)
    2. FilterMixin으로 조건 필터링
    3. 셀 위치 추출 (translation_row, translation_col)
    
    Example:
        >>> extractor = CasExtractor(aliases={"cas": ["CAS No", "CAS Number"]})
        >>> cas_list = extractor.extract(df)
        >>> # [{"cas_no": "123-45-6", "translation_row": 2, "translation_col": "F"}]
    """
    
    def __init__(self, aliases: Dict[str, List[str]]):
        self.column_resolver = ColumnResolver(aliases) if aliases else None
        self.df_filter = FilterMixin()
    
    def extract(self, df: pd.DataFrame) -> List[Dict[str, any]]:
        """DataFrame에서 CAS No 추출
        
        Filter Condition:
        - CAS column is not null
        - Download column is not null (if exists)
        - Translation column is null (if exists)
        
        Args:
            df: DataFrame
        
        Returns:
            List of {"cas_no": str, "translation_row": int, "translation_col": str}
        """
        if not self.column_resolver:
            raise ValueError("ColumnResolver not initialized")
        
        # Resolve column names
        cas_col = self.column_resolver.resolve(df, "cas")
        download_col = self.column_resolver.resolve(df, "download")
        translation_col = self.column_resolver.resolve(df, "translation")
        
        if not cas_col:
            raise ValueError("CAS column not found")
        
        # Build filter condition
        filter_conditions = [f"`{cas_col}`.notna()"]
        if download_col:
            filter_conditions.append(f"`{download_col}`.notna()")
        if translation_col:
            filter_conditions.append(f"`{translation_col}`.isna()")
        
        query_str = " & ".join(filter_conditions)
        
        # Extract CAS positions
        filtered_df, positions, values = self.df_filter.filter_df_with_cell_positions(
            df=df,
            condition=query_str,
            column=cas_col
        )
        
        # Build result list
        cas_list = []
        for (row_idx, col_idx), cas_value in zip(positions, values):
            cas_list.append({
                "cas_no": str(cas_value).strip(),
                "translation_row": row_idx + 2,  # Excel row (1-based + header)
                "translation_col": translation_col or ""
            })
        
        return cas_list
```

#### **ExcelUpdater** (xloto/services/excel_updater.py)
```python
# scripts/xloto/services/excel_updater.py
"""Excel 업데이트 Service"""

from typing import List, Dict, Any
from xl_utils.services.xw_ws import XwWs


class ExcelUpdater:
    """Excel 업데이트 Service
    
    책임:
    1. CAS 결과 기반 Excel 셀 업데이트
    2. 날짜 값 쓰기
    3. 업데이트 카운트 반환
    
    Example:
        >>> updater = ExcelUpdater()
        >>> updated_count = updater.update(
        ...     worksheet=ws,
        ...     cas_results=[{"cas_no": "123-45-6", "success": True, "translation_row": 2, "translation_col": "F"}],
        ...     date_value="2025-10-25"
        ... )
    """
    
    def update(
        self,
        worksheet: XwWs,
        cas_results: List[Dict[str, Any]],
        date_value: str
    ) -> int:
        """Excel 셀 업데이트
        
        Args:
            worksheet: XwWs 인스턴스
            cas_results: CAS 처리 결과 리스트
            date_value: 쓸 날짜 값
        
        Returns:
            업데이트된 셀 수
        """
        updated_count = 0
        
        successful_cas = [
            r for r in cas_results
            if r.get("success") and r.get("processed_count", 0) > 0
        ]
        
        df = worksheet.to_dataframe(anchor="A1", header=True, index=False)
        
        for cas_item in successful_cas:
            row = cas_item.get("translation_row")
            col = cas_item.get("translation_col")
            
            if row and col:
                # Convert column name to index
                col_idx = df.columns.get_loc(col)
                if isinstance(col_idx, int):
                    col_idx += 1  # Excel column (1-based)
                else:
                    col_idx = 1
                
                # Write cell
                worksheet.cell_ops.write(row, col_idx, date_value)
                updated_count += 1
        
        return updated_count
```

### 6.3 개선 요약

#### ✅ 개선 사항

1. **Zero Hard-coding**
   - `SectionExtractor.extract_batch()` 사용
   - Policy.name 기반 추출

2. **ExcelLoad 내부 생성**
   - 외부 주입 불필요
   - Lazy Loading 패턴

3. **Service 분리**
   - `CasExtractor`: CAS No 추출 로직
   - `ExcelUpdater`: Excel 업데이트 로직
   - SRP 준수

4. **OverrideProcessor 재사용**
   - cfg_utils 표준 패턴
   - 중복 제거

5. **에러 처리 개선**
   - try-except 구조화
   - 에러 누적 (cas_results)

6. **문서화 강화**
   - Docstring 추가
   - Example 코드

#### 📊 Before vs After

| 항목 | Before | After |
|------|--------|-------|
| **Section 추출** | 하드코딩 (`section_name='excel'`) | Policy.name 기반 |
| **ExcelLoad** | 외부 주입 필요 | 내부 생성 (Lazy) |
| **CAS 추출** | run() 내부 로직 | CasExtractor Service |
| **Excel 업데이트** | run() 내부 로직 | ExcelUpdater Service |
| **Override 병합** | 수동 구현 | OverrideProcessor |
| **라인 수** | ~150 lines | ~100 lines (Adapter) + 2 Services |

---

## 7. 종합 결론

### 7.1 공통 모듈 평가

#### 🌟 우수한 모듈 (SRP 준수, 재사용성 높음)
- **cfg_utils**: 설정 로드 표준 (Adapter/EntryPoint 분리)
- **oto**: 파이프라인 조합 표준 (Pass-through 패턴)
- **structured_io**: YAML/JSON 파싱 표준
- **fso_utils**: 파일 시스템 연산 표준
- **keypath_utils**: KeyPath 접근 표준

#### ⚠️ 개선 필요 모듈
- **data_utils**: structured_data와 역할 중복 → 재정의 필요
- **structured_data**: Mixin 과다 → 그룹화 필요
- **xl_utils**: 플랫폼 종속 → XwApp vs OpenpyxlAdapter 분리

### 7.2 XLOTO Adapter 개선 방향

#### 핵심 개선 사항
1. ✅ Zero Hard-coding (SectionExtractor.extract_batch)
2. ✅ Service 분리 (CasExtractor, ExcelUpdater)
3. ✅ ExcelLoad 내부 생성 (Lazy Loading)
4. ✅ OverrideProcessor 재사용

#### 추가 개선 가능 항목
- ImageFileManager → fso_utils or image_utils 이동 (재사용성)
- 재시도 로직 추가 (OTO 실패 시)
- 부분 성공 처리 강화
- 테스트 코드 추가

### 7.3 프로젝트 전체 아키텍처 강점

1. **계층적 설계**
   - Infrastructure → Data → Config → Domain → Application
   - 명확한 의존 방향 (순환 참조 없음)

2. **표준 패턴**
   - Adapter/EntryPoint 분리
   - Policy 기반 설정
   - Pass-through 패턴
   - Lazy Loading

3. **재사용성**
   - 모든 모듈이 독립적으로 사용 가능
   - cfg_utils, structured_io, keypath_utils 등 범용 유틸리티

4. **확장성**
   - 새로운 모듈 추가 용이
   - SectionExtractor로 하드코딩 제거
   - Cascading Priority로 유연한 설정

---

## 📝 다음 단계

### 우선순위 1: XLOTO Adapter 리팩토링
- [ ] CasExtractor Service 구현
- [ ] ExcelUpdater Service 구현
- [ ] XlOto.run() 리팩토링 (개선안 적용)
- [ ] 테스트 코드 작성

### 우선순위 2: data_utils 재정의
- [ ] DictOps/ListOps 제거 (structured_data 사용)
- [ ] StringOps/GeometryOps 유지 (도메인 특화)
- [ ] README 업데이트 (역할 명확화)

### 우선순위 3: structured_data Mixin 그룹화
- [ ] I/O Mixin (Connection, Schema, Cache)
- [ ] Transform Mixin (Clean, Normalize, Filter)
- [ ] Ops Mixin (KVOperations, KeyGeneration)
- [ ] Composite 패턴 강화

### 우선순위 4: xl_utils 플랫폼 분리
- [ ] XwApp (Windows) vs OpenpyxlAdapter (크로스 플랫폼)
- [ ] Context Manager 강화
- [ ] ColumnResolver → data_utils 이동

---

**작성자**: GitHub Copilot  
**검토 필요**: XLOTO Adapter 개선안 (CasExtractor, ExcelUpdater)  
**참고 문서**: 
- `docs/OTO_MODULE_MIGRATION_COMPLETE.md`
- `modules/cfg_utils/README.md`
- `modules/oto/adapter/oto.py`
