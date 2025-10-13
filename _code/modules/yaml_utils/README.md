# yaml_utils

> YAML 파일을 안전하고 유연하게 로드 및 저장하기 위한 파서/덤퍼 및 설정 관리 모듈입니다.  
> 환경 변수 치환, 파일 포함(`!include`), placeholder 해석 등 고급 기능을 **정책 기반(pydantic)** 으로 지원하며, SRP 원칙에 따라 `Parser`와 `Dumper`가 분리되어 있습니다.

---

## 🔍 주요 기능

| 기능 | 설명 |
|------|------|
| ✅ 환경 변수 치환 | `${VAR}` 또는 `${VAR:default}` 패턴을 OS 환경 변수로 치환 |
| ✅ `!include` 지원 | 다른 YAML 파일을 현재 위치에 병합 가능 |
| ✅ Placeholder 해석 | `{{ var }}` 형태의 키워드 해석을 통한 동적 구성 |
| ✅ 다중 병합 지원 | 여러 YAML 데이터를 순차적으로 병합 |
| ✅ 정책 기반 제어 | Pydantic 기반 정책 객체로 기능 ON/OFF 및 설정 |
| ✅ 파서/덤퍼 분리 | SRP 원칙 준수: `YamlParser`, `YamlDumper` 클래스로 분리 |

---

## 🧱 구성 요소

| 파일 | 설명 |
|------|------|
| `policy.py` | `YamlParserPolicy` 클래스 정의 (Pydantic 기반 설정 모델) |
| `parser.py` | `YamlParser` 클래스 정의. 문자열을 dict로 파싱 |
| `dumper.py` | `YamlDumper` 클래스 정의. dict를 YAML 문자열로 변환 |
| `__init__.py` | `YamlParser`, `YamlDumper`, `YamlParserPolicy` 외부 노출 |

---

## 🧪 사용 예시

```python
from yaml_utils import YamlParser, YamlDumper, YamlParserPolicy

policy = YamlParserPolicy(enable_env=True, enable_include=True, safe_mode=True)
parser = YamlParser(policy)
dumper = YamlDumper(policy)

with open("config.yaml", encoding=policy.encoding) as f:
    config = parser.parse(f.read(), base_path=Path("config.yaml").parent)

yaml_text = dumper.dump(config)
```

---

## 🔧 확장 포인트

| 항목 | 설명 |
|------|------|
| `safe_mode` | `SafeLoader`를 통해 보안 향상 |
| `encoding` | 기본 인코딩 설정 (`utf-8`) |
| `on_error` | 오류 발생 시 처리 방식 제어: `raise`, `warn`, `ignore` |
| `sort_keys`, `indent` | 출력 YAML 포맷 설정 옵션 |

---

## 🔗 연계 모듈

- `fso_utils.io.YamlFileIO`: 이 모듈을 기반으로 실제 파일 단위 IO 처리 담당
- `resolve_utils.placeholder.PlaceholderResolver`: placeholder 해석 담당
- `data_utils.dict_ops.DictOps`: dict 병합 시 사용
