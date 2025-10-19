# ⚠️ 프로젝트 실행 전 필수 체크리스트

## 1. 환경변수 설정 (최우선!)

### CASHOP_PATHS 환경변수 설정
```powershell
$env:CASHOP_PATHS = "M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml"
```

**영구 설정:** Windows 시스템 환경변수에 등록 권장  
**확인:** `echo $env:CASHOP_PATHS`

📖 상세 내용: [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)

---

## 2. Python 환경 설정

### 가상 환경 활성화
```powershell
# pyenv 사용 시
.pyenv\Scripts\activate
```

### PYTHONPATH 설정 (자동)
- 스크립트 실행 시 자동으로 modules 디렉토리 추가
- `M:\CALife\CAShop - 구매대행\_code\modules`

---

## 3. 필수 디렉토리 구조 확인

```
CAShop - 구매대행/
├── _code/
│   ├── configs/
│   │   ├── paths.local.yaml ⚠️ 필수
│   │   ├── loader/
│   │   ├── xl/
│   │   └── oto/
│   ├── modules/
│   ├── scripts/
│   └── ...
└── _public/
    └── 01.IMAGE/
```

---

## 4. 주요 스크립트 실행

### XLOTO (Excel + OTO 통합)
```powershell
python scripts/xloto.py
```

### OTO (이미지 OCR/번역/오버레이)
```powershell
python scripts/oto.py
```

### Excel Crawl
```powershell
python scripts/xlcrawl.py
```

---

## 🚨 문제 해결

### FileNotFoundError: {{configs_xl_dir}}
→ CASHOP_PATHS 환경변수 미설정

### Import Error: xloto, oto 등
→ PYTHONPATH 확인 (scripts 디렉토리에서 실행)

### ConfigLoader Error
→ enable_env: true 확인
→ paths.local.yaml 존재 여부 확인

---

## 📚 문서

- [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) - 환경변수 상세 설명
- [README.md](./modules/README.md) - 모듈 구조 설명
- [.github/copilot-instructions.md](./.github/copilot-instructions.md) - 개발 가이드라인
- [TODO_XLOTO_REFACTORING.md](./TODO_XLOTO_REFACTORING.md) - XLOTO 추후 작업사항 ⚠️
