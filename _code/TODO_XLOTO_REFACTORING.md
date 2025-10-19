# XLOTO 프로젝트 추후 작업사항

## 📋 Overview

XLOTO (Excel + OTO) 파이프라인의 향후 개선 및 리팩토링 계획

---

## 🔧 추후 작업 목록

### 1. XLOTO 내부 스크립트 모듈화

**현재 상태:**
- `scripts/xloto/entry_point/xloto.py` - EntryPoint 구현
- `scripts/xloto/adapter/xloto.py` - Adapter 구현 (일부 로직 포함)
- `scripts/xloto/services/` - CasExtractor, ImageFileManager (분리 완료)

**개선 필요 사항:**
- [ ] EntryPoint의 복잡한 로직을 adapter로 위임
- [ ] Excel 처리 로직 모듈화
  - XlController 래핑 또는 직접 service 구현
  - DataFrame 조작 로직 분리
- [ ] 파이프라인 실행 로직 분리
  - CAS No별 처리 루프를 service로 추출
  - 이미지 저장 로직 service화

**목표:**
```python
# EntryPoint는 단순히 조립만 담당
class Xloto:
    def run(self):
        # Service 호출만으로 구성
        cas_list = self.cas_service.extract_from_excel()
        results = self.pipeline_service.process_images(cas_list)
        self.excel_service.update_translation_dates(results)
```

---

### 2. Service 계층 강화

**현재 Services:**
- ✅ `CasExtractor` - DataFrame 필터링, CAS No 추출
- ✅ `ImageFileManager` - 이미지 파일 탐색 및 관리

**추가 필요 Services:**

#### 2.1 Excel Service
```python
# scripts/xloto/services/excel_service.py
class ExcelService:
    """Excel 읽기/쓰기 전담 서비스"""
    
    def __init__(self, excel_config):
        self.config = excel_config
        self.xl_controller = None
    
    def load_dataframe(self) -> pd.DataFrame:
        """Excel → DataFrame"""
        pass
    
    def update_translation_dates(self, cas_results: List[Dict]):
        """translation 컬럼 업데이트"""
        pass
    
    def __enter__(self) / __exit__(self):
        """Context manager 지원"""
        pass
```

#### 2.2 Pipeline Service
```python
# scripts/xloto/services/pipeline_service.py
class PipelineService:
    """CAS No별 이미지 처리 파이프라인"""
    
    def __init__(self, oto_adapter, image_manager):
        self.oto = oto_adapter
        self.image_manager = image_manager
    
    def process_cas(self, cas_no: str) -> Dict:
        """단일 CAS No 처리"""
        # 1. 미처리 이미지 찾기
        # 2. 각 이미지 OTO 처리
        # 3. 결과 저장
        pass
    
    def process_batch(self, cas_list: List[Dict]) -> List[Dict]:
        """배치 처리"""
        pass
```

#### 2.3 Image Save Service
```python
# scripts/xloto/services/image_save_service.py
class ImageSaveService:
    """이미지 저장 전담 서비스"""
    
    def save_image(self, image: Image, output_path: Path):
        """이미지 저장 (품질, 포맷 등 관리)"""
        pass
    
    def prepare_output_directory(self, cas_no: str) -> Path:
        """출력 디렉토리 준비"""
        pass
```

---

### 3. Adapter 역할 명확화

**현재:**
- Adapter가 일부 비즈니스 로직 포함

**개선:**
- Adapter는 순수하게 다른 adapter 조합만 담당
- 모든 세부 로직은 service로 위임

```python
# scripts/xloto/adapter/xloto.py (개선 후)
class XlOto:
    """XLOTO Adapter - 순수 조합 담당"""
    
    def __init__(self, cfg_like, ...):
        # Services 초기화만
        self.cas_extractor = None
        self.image_manager = None
        self.excel_service = None
        self.pipeline_service = None
    
    def run(self, config_path):
        # Service 호출 조합만
        pass
```

---

### 4. 테스트 강화

**필요한 테스트:**
- [ ] 각 service별 단위 테스트
- [ ] 통합 테스트 (mocking 활용)
- [ ] Excel 파일 fixture 구성

**테스트 파일 구조:**
```
tests/
├── xloto/
│   ├── services/
│   │   ├── test_cas_extractor.py
│   │   ├── test_image_file_manager.py
│   │   ├── test_excel_service.py
│   │   ├── test_pipeline_service.py
│   │   └── test_image_save_service.py
│   ├── adapter/
│   │   └── test_xloto_adapter.py
│   └── entry_point/
│       └── test_xloto_entrypoint.py
```

---

### 5. 설정 관리 개선

**현재:**
- ConfigLoader로 섹션별 추출
- Policy 클래스 정의

**개선 고려사항:**
- [ ] 설정 검증 로직 강화 (Pydantic validator)
- [ ] 기본값 관리 체계화
- [ ] 설정 파일 템플릿 제공

---

### 6. 에러 처리 및 로깅 개선

**필요 사항:**
- [ ] 커스텀 Exception 클래스 정의
- [ ] 에러 복구 로직 (재시도, 스킵 등)
- [ ] 상세 로깅 (디버깅용)
- [ ] 진행상황 표시 (progress bar)

```python
# scripts/xloto/exceptions.py
class XlOtoException(Exception):
    """XLOTO 기본 예외"""
    pass

class CASExtractionError(XlOtoException):
    """CAS No 추출 실패"""
    pass

class ImageProcessingError(XlOtoException):
    """이미지 처리 실패"""
    pass
```

---

### 7. 성능 최적화

**고려사항:**
- [ ] 병렬 처리 (멀티프로세싱/멀티스레딩)
- [ ] 이미지 처리 배치화
- [ ] 메모리 관리 (대용량 이미지)
- [ ] 캐싱 전략

---

## 📁 최종 구조 (목표)

```
scripts/xloto/
├── __init__.py
├── entry_point/
│   ├── __init__.py
│   └── xloto.py          # 단순 조립만
├── adapter/
│   ├── __init__.py
│   └── xloto.py          # Service 조합
├── services/
│   ├── __init__.py
│   ├── cas_extractor.py       ✅ 완료
│   ├── image_file_manager.py  ✅ 완료
│   ├── excel_service.py       🔧 TODO
│   ├── pipeline_service.py    🔧 TODO
│   └── image_save_service.py  🔧 TODO
├── policy/
│   ├── __init__.py
│   └── xloto_policy.py   ✅ 완료
└── exceptions.py         🔧 TODO
```

---

## 🎯 우선순위

### High Priority
1. ✅ Service 분리 (CasExtractor, ImageFileManager) - 완료
2. 🔧 Excel Service 구현
3. 🔧 Pipeline Service 구현

### Medium Priority
4. Image Save Service 구현
5. EntryPoint/Adapter 리팩토링
6. 에러 처리 강화

### Low Priority
7. 성능 최적화
8. 테스트 강화
9. 문서화

---

## 📝 참고사항

**기존 패턴 준수:**
- Adapter/EntryPoint 패턴 유지
- translate_utils, image_utils와 동일한 구조
- cfg_utils와 통합
- logs_utils 활용

**원칙:**
- SRP (Single Responsibility Principle) 엄격 적용
- Service는 재사용 가능하도록 설계
- Adapter는 조합만, Service는 로직 담당
- EntryPoint는 사용자 인터페이스만

---

## 🔗 관련 문서

- [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)
- [QUICKSTART.md](./QUICKSTART.md)
- [.github/copilot-instructions.md](../.github/copilot-instructions.md)

---

**작성일:** 2025-10-19  
**최종 업데이트:** 2025-10-19
