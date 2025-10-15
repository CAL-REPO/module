# Logs Utils - YAML 설정 파일 가이드

## 📁 제공되는 YAML 파일

### 1. `log.yaml` - 전체 기능 포함 (Comprehensive)
모든 Sink 옵션과 기능을 포함한 참조용 설정
- 파일 로그 (일반)
- 콘솔 출력
- 에러 전용 파일
- JSON 구조화 로그

### 2. `log.simple.yaml` - 간단한 설정 (Recommended)
가장 기본적인 사용 케이스
- 콘솔 + 파일 출력
- 기본 rotation/retention 정책

### 3. `log.console.yaml` - 콘솔 전용
개발/디버깅 시 콘솔 출력만 사용
- DEBUG 레벨
- 색상 출력
- diagnose 활성화

### 4. `log.production.yaml` - 프로덕션
실제 운영 환경용
- 파일 출력만
- INFO/ERROR 분리
- 엄격한 보관 정책 (30일/90일)

### 5. `log.structured.yaml` - JSON 구조화
로그 분석 도구 연동용 (ELK, Splunk, Datadog 등)
- JSON Lines 형식 (`.jsonl`)
- serialize: true
- 압축 비활성화

### 6. `log.debug.yaml` - 디버깅
최대한 상세한 로그
- DEBUG 레벨
- diagnose: true (변수값 포함)
- 파일명/라인/함수명 포함

### 7. `log.time_rotation.yaml` - 시간 기준 회전
크기가 아닌 시간 기준으로 로그 회전
- 일별: `rotation: "00:00"`
- 주별: `rotation: "1 week"`

---

## 🚀 사용 방법

### 기본 사용

```python
from logs_utils import create_logger, LogContextManager

# 방법 1: Factory 함수
manager = create_logger("logs_utils/config/log.simple.yaml")
manager.logger.info("로깅 시작")

# 방법 2: Context Manager (권장)
with LogContextManager("logs_utils/config/log.simple.yaml") as log:
    log.info("작업 시작")
    log.success("작업 완료")
```

### Runtime Override

YAML 파일 + 런타임 오버라이드 조합:

```python
# YAML 로드 + name만 변경
with LogContextManager("log.simple.yaml", name="custom_name") as log:
    log.info("이름이 변경됨")

# 특정 Sink 레벨 변경
manager = create_logger(
    "log.simple.yaml",
    sinks=[
        {"sink_type": "console", "level": "DEBUG"}  # console만 DEBUG로
    ]
)
```

### Dictionary 설정

YAML 없이 코드로 직접 설정:

```python
config = {
    "name": "my_app",
    "sinks": [
        {"sink_type": "console", "level": "INFO"},
        {
            "sink_type": "file",
            "filepath": "output/logs/app.log",
            "rotation": "10 MB",
            "retention": "7 days"
        }
    ]
}

with LogContextManager(config) as log:
    log.info("Dictionary 설정 사용")
```

---

## ⚙️ SinkPolicy 주요 옵션

### `sink_type` (필수)
- `"file"`: 파일 출력
- `"console"`: 콘솔 출력

### `filepath` (file일 때 필수)
```yaml
filepath: "output/logs/app.log"
filepath: "output/logs/{time:YYYY-MM-DD}_app.log"  # 날짜 템플릿
```

### `level`
`"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`

### `rotation` (파일 회전)
```yaml
rotation: "10 MB"      # 크기 기준
rotation: "00:00"      # 매일 자정
rotation: "12:00"      # 매일 정오
rotation: "1 week"     # 주별
rotation: "1 month"    # 월별
```

### `retention` (보관 정책)
```yaml
retention: "7 days"    # 7일 후 삭제
retention: "1 month"   # 1개월 보관
retention: 10          # 최근 10개 파일만
```

### `compression`
```yaml
compression: "zip"     # ZIP 압축
compression: "tar.gz"  # TAR.GZ
compression: "tar.bz2" # TAR.BZ2
compression: null      # 압축 안 함
```

### `format`
```yaml
# 기본 필드
format: "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"

# 상세 필드
format: "{time} | {level} | {name} | {file}:{line} | {function} | {message}"

# 색상 (콘솔 전용)
format: "<green>{time}</green> | <level>{message}</level>"
```

### `serialize`
```yaml
serialize: true   # JSON 형식으로 출력
serialize: false  # 일반 텍스트
```

### `enqueue`
```yaml
enqueue: true   # 비동기 큐 사용 (멀티스레드 안전)
enqueue: false  # 동기 출력 (콘솔 권장)
```

### `backtrace` / `diagnose`
```yaml
backtrace: true   # Exception 시 전체 스택 추적
diagnose: true    # 코드 변수값 포함 (디버깅용, 보안 주의)
```

### `colorize`
```yaml
colorize: true   # ANSI 색상 (콘솔)
colorize: false  # 색상 비활성화 (파일)
```

---

## 📊 로그 레벨 가이드

| Level | 사용 시점 | 예시 |
|-------|---------|------|
| **DEBUG** | 개발 중 상세 정보 | 변수값, 함수 진입/종료 |
| **INFO** | 일반 정보 메시지 | 작업 시작/완료, 상태 변경 |
| **WARNING** | 잠재적 문제 | Deprecated 사용, 임계값 근접 |
| **ERROR** | 오류 발생 (복구 가능) | API 호출 실패, 파일 없음 |
| **CRITICAL** | 치명적 오류 (복구 불가) | DB 연결 실패, 시스템 중단 |

---

## 🎯 시나리오별 추천 설정

### 로컬 개발
→ `log.console.yaml` 또는 `log.debug.yaml`

### 테스트 환경
→ `log.simple.yaml`

### 스테이징/프로덕션
→ `log.production.yaml`

### 로그 분석 필요
→ `log.structured.yaml` (JSON)

### 디버깅 중
→ `log.debug.yaml`

---

## 🧪 테스트

```bash
cd M:\CALife\CAShop - 구매대행\_code
python scripts/test_yaml_configs.py
```

모든 YAML 파일이 정상 동작하는지 확인합니다.

---

## 📝 예제: 크롤링 로거

```yaml
name: "crawl_taobao"

sinks:
  # 크롤링 진행 상황 (콘솔)
  - sink_type: "console"
    level: "INFO"
    format: "<green>{time:HH:mm:ss}</green> | <level>{message}</level>"
    colorize: true
    
  # 상세 로그 (파일)
  - sink_type: "file"
    filepath: "output/logs/crawl/{time:YYYY-MM-DD}_taobao.log"
    level: "DEBUG"
    rotation: "50 MB"
    retention: "14 days"
    compression: "zip"
    format: "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}"
    
  # 에러만 별도 저장
  - sink_type: "file"
    filepath: "output/logs/crawl/errors/{time:YYYY-MM-DD}_error.log"
    level: "ERROR"
    rotation: "20 MB"
    retention: "30 days"
    backtrace: true
    diagnose: true
```

```python
with LogContextManager("crawl_logger.yaml") as log:
    log.info("타오바오 크롤링 시작")
    
    for item in items:
        log.debug(f"상품 {item['id']} 크롤링 중...")
        try:
            crawl_item(item)
            log.success(f"상품 {item['id']} 완료")
        except Exception as e:
            log.error(f"상품 {item['id']} 실패: {e}")
    
    log.info("크롤링 완료")
```

---

## 📚 참고

- [loguru 공식 문서](https://loguru.readthedocs.io/)
- [SinkPolicy 정의](../core/policy.py)
- [LogManager 구현](../services/manager.py)
