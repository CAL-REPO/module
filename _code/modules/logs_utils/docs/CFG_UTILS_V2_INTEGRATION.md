# logs_utils + cfg_utils_v2 통합

## 개요

**logs_utils**의 **LogManager**가 **cfg_utils_v2**를 사용하도록 업그레이드했습니다.

## 주요 변경사항

### Before (cfg_utils v1)
```python
from cfg_utils import ConfigLoader

class LogManager:
    def _load_config(self, cfg_like, *, policy_overrides=None, **overrides):
        return ConfigLoader.load(
            cfg_like,
            model=LogPolicy,
            policy_overrides=policy_overrides,
            **overrides
        )
```

### After (cfg_utils_v2)
```python
from cfg_utils_v2 import ConfigLoader

class LogManager:
    def _load_config(self, cfg_like, **overrides):
        base_policy = LogPolicy()
        
        loader = ConfigLoader(
            base_sources=[(base_policy, "logging")],
            override_sources=[...]
        )
        
        if overrides:
            for key, value in overrides.items():
                loader.override(f"logging__{key}", value)
        
        return loader.to_model(LogPolicy, section="logging")
```

## 장점

### 1. 일관성
- cfg_utils_v2의 패턴을 따름
- base_sources + override_sources 구조

### 2. 유연성
- 런타임 Override 가능
- 다양한 소스 조합 가능

### 3. 타입 안전성
- LogPolicy 기본값 보장
- Override만 적용

## 사용 예시

### 1. LogPolicy 직접 전달
```python
from logs_utils import LogManager, LogPolicy, SinkPolicy

policy = LogPolicy(
    enabled=True,
    name="myapp",
    level="DEBUG",
    sinks=[SinkPolicy(sink_type="console", level="INFO")]
)

manager = LogManager(policy)
manager.logger.info("Hello")
```

### 2. YAML 파일 로드
```python
manager = LogManager("configs/logging.yaml")
manager.logger.info("From YAML")
```

### 3. dict로 생성
```python
config = {
    "enabled": True,
    "name": "myapp",
    "level": "INFO",
    "sinks": [{"sink_type": "console"}]
}

manager = LogManager(config)
```

### 4. Override
```python
manager = LogManager(
    None,  # 기본 설정
    name="custom_logger",
    level="WARNING"
)
```

### 5. Context 추가
```python
manager = LogManager(
    policy,
    context={
        "loader_id": 12345,
        "config_path": "/path/to/config.yaml"
    }
)
```

## 순환 참조 방지

### 문제
- cfg_utils_v2 → logs_utils (LogPolicy 타입 힌트)
- logs_utils → cfg_utils_v2 (ConfigLoader 사용)

### 해결
1. **TYPE_CHECKING 사용**
   ```python
   # cfg_utils_v2/core/policy.py
   if TYPE_CHECKING:
       from modules.logs_utils.core.policy import LogPolicy
   else:
       try:
           from modules.logs_utils.core.policy import LogPolicy
       except ImportError:
           LogPolicy = Any
   ```

2. **런타임 import**
   ```python
   # logs_utils/services/manager.py
   def _load_config(self, ...):
       from cfg_utils_v2 import ConfigLoader  # 런타임 import
       ...
   ```

3. **정책만 전달**
   - ConfigLoader가 LogManager에게 LogPolicy만 전달
   - LogManager가 다시 ConfigLoader를 사용해도 순환 없음
   - 실행 흐름이 단방향이므로 안전

## 테스트

```bash
cd "M:\CALife\CAShop - 구매대행\_code"
$env:PYTHONPATH="M:\CALife\CAShop - 구매대행\_code\modules"
python test_log_manager_v2.py
```

### 테스트 결과
```
✅ 1. LogPolicy 직접 전달 테스트
✅ 2. YAML 파일 로드 테스트
✅ 3. dict로 생성 테스트
✅ 4. Override 테스트
✅ 5. Context 추가 테스트
✅ 6. 로깅 비활성화 테스트
```

## 업데이트된 파일

1. **logs_utils/services/manager.py**
   - cfg_utils → cfg_utils_v2
   - _load_config() 메서드 재작성
   - ConfigLoader 패턴 적용

2. **cfg_utils_v2/core/policy.py**
   - LogPolicy 타입 힌트 추가
   - TYPE_CHECKING + 런타임 import

3. **cfg_utils_v2/service/loader.py**
   - log 파라미터 타입 힌트 수정
   - LogPolicy 타입 명시

## 마이그레이션 가이드

### 기존 코드 (cfg_utils v1 사용)
```python
manager = LogManager("logging.yaml", policy_overrides={"merge_mode": "deep"})
```

### 새 코드 (cfg_utils_v2 사용)
```python
# 방법 1: 그대로 사용 (호환됨)
manager = LogManager("logging.yaml")

# 방법 2: Override
manager = LogManager("logging.yaml", name="custom", level="DEBUG")
```

**호환성**: 기존 코드 대부분 그대로 동작합니다.

## 결론

✅ **cfg_utils_v2 통합 완료**
- LogManager가 cfg_utils_v2 사용
- 순환 참조 문제 해결
- 모든 테스트 통과
- 기존 코드 호환성 유지
