# CAShop 프로젝트 문서 인덱스

## 🚀 시작하기

- **[QUICKSTART.md](./QUICKSTART.md)** - 프로젝트 실행 전 필수 체크리스트
  - 환경변수 설정
  - Python 환경 설정
  - 주요 스크립트 실행 방법

## 🔧 설정 및 환경

- **[ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)** - 필수 환경변수 설정 가이드
  - CASHOP_PATHS 환경변수 상세 설명
  - ConfigLoader 동작 원리
  - 설정 방법 및 문제 해결

## 📋 개발 가이드

- **[.github/copilot-instructions.md](../.github/copilot-instructions.md)** - 개발 가이드라인
  - SRP 기준 설계
  - ConfigLoader 사용 패턴
  - 구분자 사용 규칙

## 🔨 추후 작업

- **[TODO_XLOTO_REFACTORING.md](./TODO_XLOTO_REFACTORING.md)** - XLOTO 리팩토링 계획 ⚠️
  - 모듈화 및 Service 분리 계획
  - 우선순위별 작업 목록
  - 최종 구조 설계

## 📦 모듈 문서

- **[modules/README.md](./modules/README.md)** - 모듈 구조 설명
  - 공통 모듈 소개
  - 각 모듈 역할 및 사용법

## 🎯 프로젝트 구조

```
CAShop - 구매대행/
├── _code/
│   ├── configs/          # 설정 파일
│   ├── modules/          # 공통 모듈
│   ├── scripts/          # 실행 스크립트
│   │   ├── xloto/       # Excel + OTO 통합
│   │   ├── oto/         # 이미지 OCR/번역/오버레이
│   │   └── ...
│   ├── input/           # 입력 파일
│   ├── output/          # 출력 파일
│   └── logs/            # 로그 파일
└── _public/
    └── 01.IMAGE/        # 이미지 저장소
```

## 📝 주요 스크립트

### XLOTO (Excel + OTO)
```bash
python scripts/xloto.py
```
- Excel에서 CAS No 추출
- 이미지 OCR/번역/오버레이 처리
- Excel 업데이트

### OTO (이미지 처리)
```bash
python scripts/oto.py
```
- 이미지 OCR
- 중국어 → 한국어 번역
- 번역 텍스트 오버레이

## 🔗 빠른 링크

| 문서 | 설명 |
|------|------|
| [QUICKSTART.md](./QUICKSTART.md) | 프로젝트 실행 가이드 |
| [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) | 환경변수 설정 |
| [TODO_XLOTO_REFACTORING.md](./TODO_XLOTO_REFACTORING.md) | XLOTO 추후 작업 |
| [copilot-instructions.md](../.github/copilot-instructions.md) | 개발 가이드라인 |

---

**최종 업데이트:** 2025-10-19
