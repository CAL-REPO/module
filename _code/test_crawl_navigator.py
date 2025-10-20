# -*- coding: utf-8 -*-
"""
Test: Crawl Adapter - Navigator 통합 테스트

Sync 버전 Navigator 통합:
- SyncSeleniumAdapter: BaseWebDriver → BrowserController
- SyncNavigator: BrowserController를 사용한 페이지 네비게이션
- Crawl Adapter: WebDriver + Adapter + Navigator 통합

테스트 항목:
1. SyncSeleniumAdapter 생성 확인
2. SyncNavigator 생성 확인
3. Navigator로 페이지 로드
4. Navigator로 DOM 가져오기
"""

from pathlib import Path

def test_navigator_integration():
    """Test 1: Navigator 통합 테스트 (Sync 버전)"""
    print("\n" + "="*80)
    print("[Test 1] Navigator 통합 테스트")
    print("="*80)
    
    # 1. Policy dict로 간단하게 생성
    print("\n[Step 1] Policy dict 생성")
    
    policy_dict = {
        "site": "aliexpress",
        "source": {"method": "product_detail", "urls": ["https://www.example.com"]},
        "wait": {"hook": "none", "timeout_sec": 2.0, "condition": "presence"}
    }
    
    # CrawlPolicy 없이 간단히 Mock Policy 사용
    class MockPolicy:
        def __init__(self):
            self.site = "aliexpress"
            self.wait = None
    
    policy = MockPolicy()
    
    print(f"✅ Mock Policy created: site={policy.site}")
    
    # 2. WebDriver 생성 (실제로는 생성하지 않고 Mock 사용)
    print("\n[Step 2] WebDriver Mock 생성")
    
    # Mock WebDriver
    class MockSeleniumDriver:
        def __init__(self):
            self.title = "Example Domain"
            self.current_url = "https://www.example.com"
            self.page_source = "<html><body>Example</body></html>"
        
        def get(self, url):
            print(f"  MockDriver.get({url})")
            self.current_url = url
        
        def execute_script(self, script):
            print(f"  MockDriver.execute_script(...)")
            return None
    
    class MockWebDriver:
        def __init__(self):
            self._driver = MockSeleniumDriver()
            self.driver = self._driver
        
        def quit(self):
            print("  MockDriver.quit()")
    
    mock_driver = MockWebDriver()
    print("✅ Mock WebDriver created")
    
    # 3. SyncSeleniumAdapter 생성
    print("\n[Step 3] SyncSeleniumAdapter 생성")
    from crawl_utils.services.adapter import SyncSeleniumAdapter
    
    adapter = SyncSeleniumAdapter(mock_driver)
    print(f"✅ SyncSeleniumAdapter created: {type(adapter).__name__}")
    print(f"  _drv type: {type(adapter._drv).__name__}")
    
    # 4. SyncNavigator 생성
    print("\n[Step 4] SyncNavigator 생성")
    from crawl_utils.services.navigator import SyncNavigator
    
    navigator = SyncNavigator(driver=adapter, policy=policy)
    print(f"✅ SyncNavigator created: {type(navigator).__name__}")
    
    # 5. Navigator로 페이지 로드
    print("\n[Step 5] Navigator로 페이지 로드")
    url = "https://www.example.com"
    loaded_url = navigator.load(url)
    print(f"✅ Page loaded: {loaded_url}")
    print(f"  Current URL: {navigator._current_url}")
    
    # 6. Wait hook 실행
    print("\n[Step 6] Wait hook 실행")
    from crawl_utils.core.policy import WaitHook, WaitCondition
    navigator.wait(
        hook=WaitHook.NONE,
        selector=None,
        timeout=0.5,
        condition=WaitCondition.PRESENCE.value
    )
    print("✅ Wait completed")
    
    # 7. DOM 가져오기
    print("\n[Step 7] DOM 가져오기")
    dom = navigator.get_dom()
    print(f"✅ DOM retrieved: {len(dom)} bytes")
    print(f"  DOM preview: {dom[:50]}...")
    
    print("\n" + "="*80)
    print("✅ [Test 1] Navigator 통합 테스트 완료!")
    print("="*80)


def test_crawl_adapter_with_navigator():
    """Test 2: Crawl Adapter - Navigator 통합"""
    print("\n" + "="*80)
    print("[Test 2] Crawl Adapter - Navigator 통합")
    print("="*80)
    
    from crawl_utils.adapter.crawl import Crawl
    from crawl_utils.core.policy import CrawlPolicy, CrawlSourcePolicy, WaitPolicy
    
    # 1. Policy 생성
    print("\n[Step 1] CrawlPolicy 생성")
    policy_dict = {
        "site": "aliexpress",
        "source": {
            "method": "product_detail",
            "urls": ["https://www.example.com"]
        },
        "wait": {
            "hook": "none",
            "timeout_sec": 1.0,
            "condition": "presence"
        },
        "log": {
            "enabled": True,
            "level": "DEBUG"
        }
    }
    
    # 2. Crawl Adapter 생성 (Mock WebDriver 주입 필요)
    print("\n[Step 2] Crawl Adapter 생성")
    
    # Note: 실제 테스트에서는 WebDriver를 Mock으로 주입해야 함
    # 현재는 구조 확인만 진행
    crawl = Crawl(policy_dict)
    print(f"✅ Crawl Adapter created")
    print(f"  Policy site: {crawl.policy.site}")
    print(f"  Policy method: {crawl.policy.source.method}")
    
    # 3. Services 확인 (lazy loading)
    print("\n[Step 3] Services 확인")
    
    # WebDriver는 실제 생성하지 않음 (테스트 환경에서는 Mock 필요)
    print("  webdriver: (lazy-loaded, not created in test)")
    print("  adapter: (lazy-loaded, depends on webdriver)")
    print("  navigator: (lazy-loaded, depends on adapter)")
    
    print("\n" + "="*80)
    print("✅ [Test 2] Crawl Adapter 구조 확인 완료!")
    print("="*80)


def test_adapter_properties():
    """Test 3: Adapter Properties 확인"""
    print("\n" + "="*80)
    print("[Test 3] Adapter Properties 확인")
    print("="*80)
    
    # Mock WebDriver로 Adapter 생성 테스트
    class MockSeleniumDriver:
        def __init__(self):
            self.title = "Test Page"
            self.current_url = "https://test.com"
            self.page_source = "<html><body>Test</body></html>"
        
        def get(self, url):
            self.current_url = url
    
    class MockWebDriver:
        def __init__(self):
            self._driver = MockSeleniumDriver()
            self.driver = self._driver
        
        def quit(self):
            pass
    
    # SyncSeleniumAdapter 테스트
    from crawl_utils.services.adapter import SyncSeleniumAdapter
    
    mock_driver = MockWebDriver()
    adapter = SyncSeleniumAdapter(mock_driver)
    
    print("✅ SyncSeleniumAdapter 생성")
    print(f"  _drv 접근 가능: {adapter._drv is not None}")
    print(f"  _drv type: {type(adapter._drv).__name__}")
    
    # BrowserController 인터페이스 확인
    print("\n[BrowserController 인터페이스 확인]")
    methods = ['get', 'scroll_bottom', 'wait_css', 'wait_xpath', 'get_dom', 'execute_js']
    for method in methods:
        has_method = hasattr(adapter, method) and callable(getattr(adapter, method))
        print(f"  {method:20s}: {'✅' if has_method else '❌'}")
    
    # get_dom 테스트
    print("\n[get_dom 테스트]")
    dom = adapter.get_dom()
    print(f"✅ DOM 가져오기 성공: {len(dom)} bytes")
    
    print("\n" + "="*80)
    print("✅ [Test 3] Adapter Properties 확인 완료!")
    print("="*80)


if __name__ == "__main__":
    print("\n" + "🔧 "*40)
    print("Crawl Adapter - Navigator 통합 테스트 (Sync 버전)")
    print("🔧 "*40)
    
    try:
        # Test 1: Navigator 통합
        test_navigator_integration()
        
        # Test 2: Crawl Adapter 통합
        test_crawl_adapter_with_navigator()
        
        # Test 3: Adapter Properties
        test_adapter_properties()
        
        print("\n" + "🎉 "*40)
        print("All Tests Passed!")
        print("🎉 "*40)
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
