"""WebDriver Override 테스트"""

from crawl_utils.adapter import SyncCrawl

url = "https://www.aliexpress.com/item/1005006150568354.html"

# SyncCrawl 초기화
crawler = SyncCrawl(cfg_like=None)

# run() 호출 → webdriver_overrides 디버깅 로그 출력
result = crawler.run([url])

print("\n✅ 테스트 완료!")
print(f"Success: {result[0].get('success', False)}")
