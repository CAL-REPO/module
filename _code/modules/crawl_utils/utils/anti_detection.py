"""
WebDriver Anti-Detection Utilities (참고용)

UA/AL은 Firefox YAML에서 직접 관리
이 파일은 참고/테스트 목적으로만 사용
"""

# 참고: User-Agent 예시
FIREFOX_UA_EXAMPLES = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
]

# 참고: Accept-Language 예시
ACCEPT_LANGUAGE_EXAMPLES = {
    "korean": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "chinese": "zh-CN,zh;q=0.9,ko;q=0.8,en;q=0.7",
    "english": "en-US,en;q=0.9,ko;q=0.8",
}

# 실제 사용: configs/firefox_{site}.yaml 에서 직접 설정
# user_agent: "Mozilla/5.0 ..."
# accept_languages: "zh-CN,zh;q=0.9,..."
