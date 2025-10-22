# Python Context Manager 완벽 가이드

## 🎯 Context Manager란?

**Context Manager**는 Python에서 리소스를 안전하게 관리하기 위한 패턴입니다.
`with` 문과 함께 사용되며, **자동으로 리소스 초기화와 정리를 수행**합니다.

---

## 📚 기본 개념

### 문제 상황: 수동 리소스 관리

```python
# ❌ 위험한 코드 (수동 관리)
file = open("data.txt", "r")
data = file.read()
# 만약 여기서 예외 발생하면?
file.close()  # ← 실행 안 될 수 있음!
```

**문제점:**
- 예외 발생 시 `file.close()`가 실행 안 됨
- 메모리 누수 발생
- 리소스 점유 지속

---

### 해결책: Context Manager 사용

```python
# ✅ 안전한 코드 (자동 관리)
with open("data.txt", "r") as file:
    data = file.read()
    # 예외 발생해도 자동으로 file.close() 호출됨!
# 여기서는 이미 파일이 닫혀있음
```

**장점:**
- ✅ 예외 발생해도 자동 정리
- ✅ 코드 가독성 향상
- ✅ 리소스 누수 방지

---

## 🔍 Context Manager의 동작 원리

### 1. `__enter__`와 `__exit__` 메서드

```python
class MyResource:
    def __enter__(self):
        """with 문 진입 시 호출"""
        print("리소스 초기화")
        return self  # with ... as 변수에 할당될 객체
    
    def __exit__(self, exc_type, exc_value, traceback):
        """with 문 종료 시 호출 (예외 발생해도 무조건 호출!)"""
        print("리소스 정리")
        return False  # True면 예외 억제, False면 예외 전파
```

**사용:**
```python
with MyResource() as resource:
    print("리소스 사용 중")
    # raise Exception("에러!")  # 예외 발생해도 __exit__ 호출됨

# 출력:
# 리소스 초기화
# 리소스 사용 중
# 리소스 정리
```

---

### 2. 동작 순서

```python
with Context() as obj:
    # 코드 블록
    pass
```

**실행 순서:**
1. `Context().__enter__()` 호출 → 리소스 초기화
2. 반환값을 `obj`에 할당
3. 코드 블록 실행
4. `Context().__exit__()` 호출 → 리소스 정리 (예외 여부 무관!)

---

## 💻 실제 사용 예제

### 1. 파일 처리

```python
# Context Manager 내장 지원
with open("data.txt", "r") as f:
    data = f.read()
# 자동으로 f.close() 호출됨
```

---

### 2. 데이터베이스 연결

```python
import sqlite3

with sqlite3.connect("database.db") as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    results = cursor.fetchall()
# 자동으로 conn.close() 호출됨
```

---

### 3. 락(Lock) 관리

```python
import threading

lock = threading.Lock()

with lock:
    # 크리티컬 섹션 (동시 접근 방지)
    shared_resource += 1
# 자동으로 lock.release() 호출됨
```

---

### 4. 임시 디렉토리

```python
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    # 임시 디렉토리 사용
    file_path = Path(tmpdir) / "temp.txt"
    file_path.write_text("data")
# 자동으로 tmpdir 삭제됨
```

---

## 🚀 Context Manager 만들기

### 방법 1: 클래스로 구현 (__enter__, __exit__)

```python
class DatabaseConnection:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.connection = None
    
    def __enter__(self):
        """연결 시작"""
        print(f"Connecting to {self.host}:{self.port}")
        self.connection = f"Connection to {self.host}"
        return self.connection
    
    def __exit__(self, exc_type, exc_value, traceback):
        """연결 종료"""
        print("Closing connection")
        self.connection = None
        
        # 예외 처리
        if exc_type is not None:
            print(f"Exception occurred: {exc_value}")
        
        return False  # 예외를 다시 raise

# 사용
with DatabaseConnection("localhost", 5432) as conn:
    print(f"Using: {conn}")
    # raise ValueError("Test error")

# 출력:
# Connecting to localhost:5432
# Using: Connection to localhost
# Closing connection
```

---

### 방법 2: contextlib.contextmanager 데코레이터

```python
from contextlib import contextmanager

@contextmanager
def database_connection(host, port):
    # __enter__ 부분
    print(f"Connecting to {host}:{port}")
    conn = f"Connection to {host}"
    
    try:
        yield conn  # with ... as 변수에 전달
    finally:
        # __exit__ 부분 (예외 여부 무관하게 실행)
        print("Closing connection")

# 사용 (위와 동일)
with database_connection("localhost", 5432) as conn:
    print(f"Using: {conn}")
```

**장점:**
- ✅ 간결한 코드
- ✅ 함수형 스타일
- ✅ try-finally 자동 처리

---

## 🔥 실전 예제: WebDriver Context Manager

### FirefoxWebDriver의 Context Manager 구현

```python
class FirefoxWebDriver(BaseWebDriver):
    """Firefox WebDriver with Context Manager support"""
    
    def __init__(self, cfg_like, **overrides):
        self.config = self._load_config(cfg_like, **overrides)
        self._driver = None
    
    def __enter__(self):
        """with 문 진입 시 WebDriver 시작"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """with 문 종료 시 WebDriver 정리"""
        self.quit()
        return False  # 예외 전파
    
    def start(self):
        """WebDriver 시작"""
        if self._driver is None:
            self._driver = self._create_driver()
            self.logger.info("WebDriver started")
    
    def quit(self):
        """WebDriver 종료"""
        if self._driver:
            self._driver.quit()
            self._driver = None
            self.logger.info("WebDriver closed")
    
    @property
    def driver(self):
        """Selenium WebDriver 인스턴스 접근"""
        if self._driver is None:
            raise RuntimeError("WebDriver not started. Use 'with' or call start()")
        return self._driver
```

---

### 사용 예제

#### 1. Context Manager 방식 (권장)

```python
# ✅ 자동으로 시작/종료 관리
with FirefoxWebDriver("configs/firefox.yaml") as driver:
    driver.driver.get("https://example.com")
    title = driver.driver.title
    print(f"Title: {title}")
    
    # 예외 발생해도 자동으로 driver.quit() 호출됨!
    # raise Exception("Error!")

# 여기서는 이미 WebDriver가 종료되어 있음
```

**출력:**
```
WebDriver started
Title: Example Domain
WebDriver closed
```

---

#### 2. 수동 관리 방식

```python
# ⚠️ 수동으로 시작/종료 관리 (권장하지 않음)
driver = FirefoxWebDriver("configs/firefox.yaml")
driver.start()  # 명시적 시작

try:
    driver.driver.get("https://example.com")
    title = driver.driver.title
finally:
    driver.quit()  # 반드시 종료해야 함!
```

---

## 📊 Context Manager vs 수동 관리 비교

| 항목 | Context Manager (`with`) | 수동 관리 |
|------|-------------------------|----------|
| **코드 간결성** | ✅ 간결 | ❌ 장황 |
| **리소스 정리** | ✅ 자동 (예외 시에도) | ⚠️ 수동 (try-finally 필요) |
| **안전성** | ✅ 높음 | ⚠️ 낮음 (실수 가능) |
| **가독성** | ✅ 명확 | ❌ 복잡 |
| **Python 관례** | ✅ Pythonic | ❌ 비추천 |

---

## 🎯 Context Manager 사용이 필수적인 경우

### 1. 파일 I/O
```python
with open("file.txt") as f:
    data = f.read()
```

### 2. 네트워크 연결
```python
with socket.socket() as sock:
    sock.connect(("host", 8080))
```

### 3. 데이터베이스 연결
```python
with sqlite3.connect("db.sqlite") as conn:
    cursor = conn.cursor()
```

### 4. 락/세마포어
```python
with threading.Lock():
    # 크리티컬 섹션
    pass
```

### 5. WebDriver/브라우저
```python
with FirefoxWebDriver() as driver:
    driver.driver.get("https://example.com")
```

### 6. 임시 리소스
```python
with tempfile.TemporaryFile() as tmp:
    tmp.write(b"data")
```

---

## 💡 고급 기능

### 1. 여러 Context Manager 중첩

```python
with open("input.txt") as fin, open("output.txt", "w") as fout:
    data = fin.read()
    fout.write(data.upper())
```

---

### 2. contextlib.ExitStack (동적 Context Manager)

```python
from contextlib import ExitStack

files = ["file1.txt", "file2.txt", "file3.txt"]

with ExitStack() as stack:
    # 동적으로 여러 파일 열기
    opened_files = [stack.enter_context(open(f)) for f in files]
    
    for f in opened_files:
        print(f.read())
# 모든 파일 자동으로 닫힘
```

---

### 3. 예외 억제 (suppress)

```python
from contextlib import suppress

with suppress(FileNotFoundError):
    os.remove("file.txt")  # 파일 없어도 예외 발생 안 함
```

---

### 4. 시간 측정 Context Manager

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name):
    start = time.time()
    yield
    end = time.time()
    print(f"{name} took {end - start:.2f} seconds")

with timer("Data processing"):
    # 시간 측정할 코드
    time.sleep(1)

# 출력: Data processing took 1.00 seconds
```

---

## ✅ Context Manager 체크리스트

**구현 시:**
- [ ] `__enter__` 메서드 구현 (리소스 초기화)
- [ ] `__exit__` 메서드 구현 (리소스 정리)
- [ ] `__exit__`에서 예외 처리 결정 (True/False 반환)
- [ ] 예외 발생해도 정리되는지 테스트

**사용 시:**
- [ ] `with` 문 사용
- [ ] 리소스가 자동으로 정리되는지 확인
- [ ] 예외 처리 적절히 수행

---

## 🚀 요약

### Context Manager의 핵심

1. **목적**: 리소스 자동 관리 (초기화 + 정리)
2. **방법**: `with` 문 사용
3. **구현**: `__enter__`, `__exit__` 메서드
4. **장점**: 안전성, 가독성, 자동 정리

### 사용 패턴

```python
# ✅ 권장
with Resource() as res:
    res.use()
# 자동 정리

# ❌ 비권장
res = Resource()
try:
    res.use()
finally:
    res.cleanup()  # 수동 정리
```

### 실전 팁

- ✅ 파일, 네트워크, DB → 항상 Context Manager 사용
- ✅ WebDriver, 브라우저 → Context Manager 사용
- ✅ 임시 리소스 → Context Manager 사용
- ✅ 복잡한 로직 → `@contextmanager` 데코레이터 활용

**Context Manager = 안전하고 깔끔한 리소스 관리!** 🎯
