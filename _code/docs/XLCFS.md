네트워크/요청 레벨

속도/패턴 제어: 고정 간격 대신 지터(jitter) 섞은 min..max 랜덤 지연, 도메인별 동시성 제한, 429/5xx 시 지수 백오프.

헤더 일관성: User-Agent, Accept-Language, (필요 시) Referer, Accept를 세트로 유지. 도메인별로 “세션 수명 동안”은 고정.

쿠키/세션 재사용: 로그인/세션 사이트는 session_from_driver_cookies()로 requests.Session에 쿠키·UA·언어를 이관해서 정적 리소스(이미지/JSON)만 requests로 받기.

ETag/If-Modified-Since: 중복 요청 줄여 서버 부담↓(불필요한 200 회피).

프록시 운영: 같은 사이트에 과도한 동일 IP 트래픽 금물. 세션 경계에서만 프록시 회전(중간 회전은 의심↑). 가능하면 레지덴셜.

브라우저 지문/환경

헤드리스 흔적 최소화: (이미 적용한) dom.webdriver.enabled = false, privacy.resistFingerprinting = false 등. window_size를 전형적 값(예: 1366×768, 1440×900)으로.

프로파일 사용: use_cli_profile + profile_path로 실제 프로필을 재사용(쿠키/스토리지/서비스워커 누적). “새 계정처럼 보이는” 매 실행 지양.

언어/시간대 일관: intl.accept_languages와 시스템 타임존·locale이 동떨어지면 의심 신호. 가능한 실제 환경과 맞추기.

자원 차단 과용 금지: 이미지/JS 전면 차단은 비현실적 패턴. 필요한 것만 부분 차단(트래킹·광고 도메인)으로.

행동 시뮬레이션

인간형 인터랙션: 뷰포트 진입 후 즉시 API만 치는 패턴 대신, scroll → idle → click/expand → idle 등 짧은 시퀀스를 섞기.

가시영역 로딩 대기: wait_until_visible(selector) 후 스크린샷/추출. 스크롤은 고정 step 대신 콘텐츠 높이/요소 위치 기반.

항로 유지: 목록 → 상세 → 목록(뒤로가기) 같은 실제 탐색 경로 유지. 직접 API 엔드포인트만 연타는 패턴은 리스크↑.

인프라/운영

도메인별 쿼터: 시간당/일일 요청 상한 관리(특히 이미지). 크롤 상태/오류코드 대시보드화.

에러 다양도 살피기: 403/429/406/451 등 상세 코드별 핸들러 분리. 403 연속이면 즉시 휴지기 쿨다운.

Warm-up & Stagger: 첫 진입은 가볍게(홈/카테고리), 이어서 깊이. 여러 작업은 시작 시간을 분산.

콘텐츠/렌더링

동적 데이터는 “실제 호출” 복제: 네트워크 패널에서 API·헤더·쿼리·토큰(예: x-csrf, bearer)을 똑같이 재현. 필요 시 execute_script로 토큰 읽어 Session에 주입.

서명 URL/만료 대응: 이미지가 서명URL이면 즉시 저장, 실패 시 페이지 재로딩→URL 재획득 루틴 준비.

코드에 바로 얹기 쉬운 포인트

FirefoxConfig에 이미 있는 것 적극 활용: user_agent, accept_languages, use_cli_profile, window_size, disable_automation_flags.

session_from_driver_cookies()로 리퍼러/Accept/Accept-Language/UA 통일해서 requests로 다운로드.

크롤러 공통 유틸에 지터 포함 backoff/retry 데코레이터 추가(429, 5xx, 커스텀 4xx 구간별로 다른 backoff).

원하면 위 항목들 중 프로젝트에 바로 넣을 수 있는 지터 백오프 유틸이랑 리퍼러 체인 유지 다운로드 함수를 만들어 드릴게요.

# FirefoxConfig 설정 템플릿

`FirefoxConfig`는 Firefox WebDriver 실행을 위한 설정 정보를 포함하며, Pydantic 기반으로 타입 검증 및 유효성 확인이 수행됩니다.

## 🔧 전체 필드 설명

| 필드명              | 타입             | 기본값             | 설명 |
|---------------------|------------------|---------------------|------|
| `driver_path`       | str\|None        | `None`              | geckodriver 실행 파일 경로 (없으면 자동 탐색/설치됨) |
| `binary_path`       | str\|None        | `None`              | Firefox 실행 파일 경로 |
| `profile_path`      | str\|None        | `None`              | 기존 Firefox 프로필 경로 (로그인 유지 목적 등) |
| `headless`          | bool             | `False`             | 창 없이 백그라운드 실행 여부 |
| `window_size`       | tuple(int, int)  | `(1440, 900)`       | 브라우저 창 크기 (width, height) |
| `log_dir`           | str\|None        | `None`              | geckodriver 로그 파일 저장 디렉토리 |
| `accept_languages`  | str\|None        | `None`              | 브라우저 언어 설정 (ex: `"ko,en-US;q=0.8"`) |
| `user_agent`        | str\|None        | `None`              | 사용자 에이전트 (User-Agent) 문자열 |
| `dom_enabled`       | bool             | `False`             | `navigator.webdriver` 값 설정 여부 |
| `fingerprint_enabled` | bool           | `False`             | fingerprint 방지 기능 (ResistFingerprinting) |
| `session_file`      | str\|None        | `None`              | 헤더 설정 저장/불러올 경로 (json 파일) |

## 📦 session_file 동작 방식

- 파일이 존재할 경우: 내부의 `"headers"` 정보를 읽어 UA / 언어 정보를 설정
- 파일이 없을 경우: 브라우저 실행 후 자동으로 UA / 언어 정보를 추출하여 저장

예시: session_file 내용
{
  "headers": {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0...)",
    "Accept-Language": "ko,en-US;q=0.8,en;q=0.7"
  }
}

## ✅ 설정 예시 (YAML)

firefox:
  driver_path: null
  binary_path: null
  profile_path: "~/.mozilla/firefox/abcd1234.default-release"
  headless: true
  window_size: [1440, 900]
  log_dir: "./log"
  accept_languages: null
  user_agent: null
  dom_enabled: false
  fingerprint_enabled: true
  session_file: "./session/fingerprint_headers.json"

## 🧪 실행 흐름 요약

1. 설정 객체 생성 (`FirefoxConfig`)
2. `load_firefox(cfg)` 호출
3. - `session_file` 있을 경우: headers 로딩
   - 없을 경우: headers 추출 후 저장
4. Firefox WebDriver 실행 완료

> 설정이 잘못된 경우 자동 검증/예외 발생하므로, 문제 추적이 쉬움