# logs_utils/configs - YAML 설정 가이드

## 📁 파일 구조

```
configs/
├── log.yaml                    # LogPolicy 설정 (단위테스트/예시용)
└── config_loader_log.yaml      # ConfigLoader 주입용 LogPolicy
```

---

## 📄 파일 상세 설명

### 1. log.yaml
**용도**: LogManager 기본 설정 및 다양한 사용 예시

**제공 섹션**:
- `logging`: 기본 설정 (콘솔 로깅, INFO 레벨)
- `example_console`: 콘솔 전용 로깅
- `example_file`: 파일 전용 로깅
- `example_multi_sink`: 콘솔 + 파일 다중 Sink
- `example_production`: 운영 환경 설정
- `example_development`: 개발 환경 설정
- `example_disabled`: 로깅 비활성화
- `example_with_context`: Context 활용 예시

**사용 시나리오**:
```python
from logs_utils import LogManager

# 기본 섹션 (logging) 사용
manager = LogManager("configs/log.yaml")
manager.logger.info("기본 로깅")

# 특정 섹션 사용
manager = LogManager(("configs/log.yaml", "example_production"))
manager.logger.info("운영 환경 로깅")

# 런타임 오버라이드
manager = LogManager("configs/log.yaml", level="DEBUG")
```

---

### 2. config_loader_log.yaml
**용도**: cfg_utils ConfigLoader 정책 파일 (`config_loader_cfg_path` 인자로 주입)

**⚠️ 중요**: 이 파일은 `config_loader_cfg_path` 인자로 전달되는 **ConfigLoader 정책 파일**입니다!
- ConfigLoader 자체의 동작 방식을 정의
- 각 섹션이 ConfigLoaderPolicy를 나타냄
- log 필드를 통해 ConfigLoader 내부 로깅 제어

**제공 섹션**:
- `config_loader`: 기본 정책 (INFO 레벨, 콘솔)
- `config_loader_debug`: 디버그 정책 (DEBUG 레벨, 콘솔+파일)
- `config_loader_trace`: 상세 추적 (TRACE 레벨)
- `config_loader_production`: 운영 정책 (WARNING 레벨, 파일만)
- `config_loader_disabled`: 로깅 비활성화
- `config_loader_test`: 테스트 정책 (메모리 Sink)

**사용 흐름**:
```
ConfigLoader(config_loader_cfg_path=("config_loader_log.yaml", "config_loader_debug"))
    ↓
ConfigLoader가 YAML 파일을 읽음
    ↓
config_loader_debug 섹션에서 log 필드 추출
    ↓
LogPolicy 인스턴스 생성
    ↓
ConfigLoader 내부에서 LogManager 생성
    ↓
ConfigLoader의 모든 동작이 로그로 출력됨
```

**사용 예시**:
```python
from cfg_utils import ConfigLoader

# config_loader_debug 섹션의 log 정책 적용
loader = ConfigLoader(
    config_loader_cfg_path=("config_loader_log.yaml", "config_loader_debug"),
    base_sources=[("config.yaml", "app")]
)

# ConfigLoader 내부 동작이 DEBUG 레벨로 로그 출력됨:
# - 파일 읽기
# - 병합 과정
# - KeyPath 탐색
# - 타입 변환
```

---

## 🎯 두 파일의 차이점

| 구분 | log.yaml | config_loader_log.yaml |
|------|----------|------------------------|
| **용도** | 애플리케이션 로깅 | ConfigLoader 정책 파일 |
| **전달 방식** | LogManager 직접 사용 | config_loader_cfg_path 인자 |
| **대상** | 애플리케이션 로그 | ConfigLoader 내부 동작 추적 |
| **섹션 명명** | `logging`, `example_*` | `config_loader`, `config_loader_debug`, ... |
| **구조** | LogPolicy | ConfigLoaderPolicy (log 필드 포함) |
| **사용 주체** | 개발자 | ConfigLoader |

---

## � 권장 사용 패턴

### 패턴 1: 애플리케이션 로깅
**시나리오**: 일반적인 애플리케이션 로그를 남기고 싶을 때

```python
from logs_utils import LogManager

# log.yaml 사용
manager = LogManager("configs/log.yaml")
manager.logger.info("Application started")
manager.logger.debug("Processing item: {}", item_id)
manager.logger.error("Failed to connect: {}", error)
```

### 패턴 2: ConfigLoader 디버깅
**시나리오**: cfg_utils ConfigLoader가 어떻게 동작하는지 추적하고 싶을 때

```python
from cfg_utils import ConfigLoader

# config_loader_cfg_path로 정책 파일 전달
loader = ConfigLoader(
    config_loader_cfg_path=("config_loader_log.yaml", "config_loader_debug"),
    base_sources=[("config.yaml", "app")]
)

# ConfigLoader 내부 동작이 DEBUG 레벨로 로그 출력됨:
# - 파일 읽기: "Loading YAML file: config.yaml"
# - 병합 과정: "Merging section: app"
# - KeyPath 탐색: "Resolving keypath: app__database__host"
# - 타입 변환: "Converting to model: AppConfig"

config = loader.to_model(AppConfig, section="app")
```

### 패턴 3: 복합 사용
**시나리오**: 애플리케이션 로그 + ConfigLoader 디버깅

```python
from cfg_utils import ConfigLoader
from logs_utils import LogManager

# 1. 애플리케이션 로거
app_logger = LogManager("configs/log.yaml")
app_logger.logger.info("Application initialization")

# 2. ConfigLoader 디버깅 활성화
loader = ConfigLoader(
    config_loader_cfg_path=("config_loader_log.yaml", "config_loader_debug"),
    base_sources=[("config.yaml", "app")]
)

# 3. 설정 로드 (ConfigLoader 로그가 자동 출력됨)
config = loader.to_model(AppConfig, section="app")

# 4. 애플리케이션 로직
app_logger.logger.info("Config loaded: {}", config.name)
```

---

## ⚙️ LogPolicy 주요 필드

### `enabled`
```yaml
enabled: true   # 로깅 활성화
enabled: false  # 로깅 비활성화
```

### `name`
```yaml
name: "app_logger"        # 로거 이름
name: "cfg_loader_debug"  # ConfigLoader 디버깅용
```

### `level`
```yaml
level: "DEBUG"    # 디버깅 레벨
level: "INFO"     # 정보 레벨
level: "WARNING"  # 경고 레벨
level: "ERROR"    # 에러 레벨
```

### `sinks`
```yaml
sinks:
  - sink_type: "console"
    level: "DEBUG"
    colorize: true
    
  - sink_type: "file"
    filepath: "output/logs/app.log"
    rotation: "10 MB"
    retention: "7 days"
```

### `context`
```yaml
context:
  app_name: "CAShop"
  env: "production"
  version: "1.0.0"
```

**사용 예시**:
```python
manager = LogManager({
    "name": "my_app",
    "level": "INFO",
    "context": {
        "env": "production",
        "version": "1.0.0"
    }
})

# 모든 로그에 context가 자동 추가됨
manager.logger.info("Started")  
# → 2024-01-15 10:00:00 | INFO | [env=production][version=1.0.0] Started
```

---

## 📊 로그 레벨 가이드

| Level | 사용 시점 | 예시 |
|-------|---------|------|
| **TRACE** | 최상세 디버깅 | 변수값, 조건문 분기, 루프 반복 |
| **DEBUG** | 개발 중 상세 정보 | 함수 진입/종료, 중간 계산 결과 |
| **INFO** | 일반 정보 메시지 | 작업 시작/완료, 상태 변경 |
| **WARNING** | 잠재적 문제 | Deprecated 사용, 임계값 근접 |
| **ERROR** | 오류 발생 (복구 가능) | API 호출 실패, 파일 없음 |
| **CRITICAL** | 치명적 오류 (복구 불가) | DB 연결 실패, 시스템 중단 |

---

## 🎯 시나리오별 추천

### 로컬 개발
```python
# log.yaml - example_development 섹션
manager = LogManager(("configs/log.yaml", "example_development"))
```

### 운영 환경
```python
# log.yaml - example_production 섹션
manager = LogManager(("configs/log.yaml", "example_production"))
```

### ConfigLoader 디버깅
```python
# config_loader_log.yaml - config_loader_debug 섹션
loader = ConfigLoader(
    config_loader_cfg_path=("config_loader_log.yaml", "config_loader_debug"),
    base_sources=[...]
)
```

### 테스트
```python
# config_loader_log.yaml - config_loader_test 섹션
loader = ConfigLoader(
    config_loader_cfg_path=("config_loader_log.yaml", "config_loader_test"),
    base_sources=[...]
)
```

---

## 🧪 단위 테스트

```bash
# 모든 YAML 파일 검증
cd M:\CALife\CAShop - 구매대행\_code
pytest modules/logs_utils/tests/test_logs_configs.py -v
```

테스트 내용:
- ✅ log.yaml 모든 섹션 로드 검증
- ✅ config_loader_log.yaml 모든 섹션 로드 검증
- ✅ LogPolicy 필드 유효성 검사
- ✅ ConfigLoader + LogPolicy 통합 테스트

---

## � 참고 문서

- [loguru 공식 문서](https://loguru.readthedocs.io/)
- [LogPolicy 정의](../core/policy.py)
- [SinkPolicy 정의](../core/policy.py)
- [LogManager 구현](../services/manager.py)
- [cfg_utils_v2 문서](../../cfg_utils_v2/README.md)

---

## 🔍 트러블슈팅

### Q: config_loader_log.yaml과 log.yaml의 차이는?
**A**: 
- `log.yaml`: 애플리케이션 로그용 (LogManager 직접 사용)
- `config_loader_log.yaml`: ConfigLoader 정책 파일 (config_loader_cfg_path 인자로 전달)

### Q: ConfigLoader 동작을 보고 싶지 않은데 로그가 계속 나옴
**A**: config_loader_cfg_path를 설정하지 않거나 disabled 섹션 사용
```python
# 방법 1: config_loader_cfg_path 없음 (로그 비활성화)
loader = ConfigLoader(base_sources=[...])

# 방법 2: disabled 섹션 사용
loader = ConfigLoader(
    config_loader_cfg_path=("config_loader_log.yaml", "config_loader_disabled"),
    base_sources=[...]
)
```

### Q: 로그 파일이 너무 커짐
**A**: `rotation`과 `retention` 설정 조정
```yaml
sinks:
  - sink_type: "file"
    rotation: "10 MB"      # 10MB마다 회전
    retention: "7 days"    # 7일 후 삭제
    compression: "zip"     # 압축 활성화
```

### Q: 특정 모듈만 DEBUG 레벨로 보고 싶음
**A**: Sink 레벨을 개별 설정
```yaml
sinks:
  - sink_type: "console"
    level: "INFO"          # 전체는 INFO
    
  - sink_type: "file"
    filepath: "logs/debug.log"
    level: "DEBUG"         # 파일만 DEBUG
    filter: "my_module"    # 특정 모듈만
```

