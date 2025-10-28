import sys
sys.path.insert(0, r"m:\\CALife\\CAShop - 구매대행\\_code")
from modules.crawl_utils.services.extractor import SyncDOMExtractor
from types import SimpleNamespace

policy = SimpleNamespace(item_selector="#product-description")
ext = SyncDOMExtractor(None, policy)
html = '<div id="product-description"><img src="//example.com/a.jpg?x=1" style="background-image:url(https://example.com/bg.jpg)"></div>'
print(ext.extract(html))
