# 📁 fso_utils

**파일 및 디렉터리 경로 관리, 탐색, 입출력, 정책 기반 제어 기능을 제공하는 객체지향 모듈**

---

## ✅ 목적

- 다양한 파일 시스템 작업을 **정책 기반으로 안전하게 수행**
- 텍스트/바이너리/JSON/YAML 등의 **파일 입출력 기능 통합**
- 디렉터리 내 파일/폴더 탐색 및 필터링 기능 제공

---

## 📦 구성 요소

| 구성 | 설명 |
|------|------|
| `types.py` | `PathLike` 타입 별칭 정의 (`str | Path`) |
| `policy.py` | `FSOOpsPolicy`, `FSOExplorerPolicy`, `ExistencePolicy`, `FileExtensionPolicy` 등 정책 정의 |
| `ops.py` | 정책 기반 경로 해석기 (`FSOOps`) |
| `explorer.py` | 디렉터리 내 파일/폴더 탐색기 (`FSOExplorer`) |
| `io.py` | 파일 입출력 클래스 (`JsonFileIO`, `YamlFileIO`, `BinaryFileIO`) |

---

## 🧱 주요 클래스 구조

### 🔹 `FSOOps`
```python
ops = FSOOps("./data/file.txt", policy=FSOOpsPolicy(exist=ExistencePolicy(must_exist=True)))
print(ops.path)
```

### 🔹 `FSOExplorer`
```python
explorer = FSOExplorer("./data", policy=FSOExplorerPolicy(allowed_exts=[".txt"], recursive=True))
print(explorer.files())
```

### 🔹 `JsonFileIO`, `YamlFileIO`, `BinaryFileIO`
```python
from fso_utils import JsonFileIO

file = JsonFileIO("result.json")
file.write({"ok": True})
data = file.read()
```

---

## ⚙️ 정책 설정 예시

```python
from fso_utils import FSOOpsPolicy, FSOExplorerPolicy, ExistencePolicy

ops_policy = FSOOpsPolicy(as_type="file", exist=ExistencePolicy(must_exist=True))
explorer_policy = FSOExplorerPolicy(recursive=True, allowed_exts=[".json"])
```

---

## 🔄 최신 업데이트

- `YamlFileIO.write()`는 이제 문자열 반환이 아닌 **실제 파일 저장**을 수행합니다.
- `FileReader` / `FileWriter`는 모두 `FSOOpsPolicy`에 `ExistencePolicy`를 **명시적 인스턴스**로 전달하도록 구조 통일
- 내부적으로 `YamlParser`, `YamlDumper`를 구분하여 책임 분리

---

## 🔗 연관 모듈

- `yaml_utils` → `YamlParser`, `YamlDumper`, `YamlParserPolicy`를 통해 `YamlFileIO`와 연동됨
- `cfg_utils` → 설정 파일을 통해 `FSOOpsPolicy` 등 외부 주입 예정

---

## 🧪 테스트 및 예제

- 테스트는 `tests/fso_utils/` 내 별도 모듈에서 수행 예정
- 실제 입출력은 프로젝트 루트 기준 상대경로를 사용하여 실행

---

## 📌 참고 사항

- 윈도우 환경 기반 설계 (단, POSIX 호환 경로도 지원)
- 모든 정책은 `pydantic` 기반 모델로 설정 및 검증 수행
- 클래스 기반 구조로 확장성과 명확한 책임 분리가 목표