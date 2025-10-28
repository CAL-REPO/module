import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules"))

from crawl_utils.adapter.webdriver_manager import WebDriverManager
from crawl_utils.services.adapter import SyncSeleniumAdapter
from crawl_utils.services.navigator import SyncNavigator

# Target URL
url = "https://ko.aliexpress.com/item/1005008483128442.html?spm=a2g0o.detail.pcDetailBottomMoreOtherSeller.6.533f4uTA4uTAMR&gps-id=pcDetailBottomMoreOtherSeller&scm=1007.40050.354490.0&scm_id=1007.40050.354490.0&scm-url=1007.40050.354490.0&pvid=786eeffd-8924-47c9-9235-d88951d17399&_t=gps-id%3ApcDetailBottomMoreOtherSeller%2Cscm-url%3A1007.40050.354490.0%2Cpvid%3A786eeffd-8924-47c9-9235-d88951d17399%2Ctpp_buckets%3A668%232846%238107%231934&pdp_ext_f=%7B%22order%22%3A%221414%22%2C%22eval%22%3A%221%22%2C%22sceneId%22%3A%2230050%22%7D&pdp_npi=6%40dis%21USD%2167.48%2137.11%21%21%2167.48%2137.11%21%402141115b17577566942155702e4901%2112000045343899055%21rec%21HK%214335231483%21ACX%211%210%21n_tag%3A-29919%3Bd%3A578eec35%3Bm03_new_user%3A-29894&utparam-url=scene%3ApcDetailBottomMoreOtherSeller%7Cquery_from%3A%7Cx_object_id%3A1005008483128442%7C_p_origin_prod%3A&gatewayAdapt=glo2kor"

probe_snippet = r"""
(function(){
  try{
    const all = Array.from(document.querySelectorAll('img'));
    const nodes = all.slice(0,50);
    const samples = nodes.map(i=>({
      src: i.getAttribute('src') || i.src || null,
      data_src: i.getAttribute('data-src') || null,
      srcset: i.getAttribute('srcset') || null,
      alt: i.getAttribute('alt') || null,
      outer: i.outerHTML ? i.outerHTML.slice(0,200) : null
    }));
    return {count: all.length, samples: samples};
  }catch(e){ return {__error: String(e), stack: e && e.stack}; }
})();
"""

wdm = None
try:
    wdm = WebDriverManager(cfg_like=None, log_manager=None, provider='firefox', region='global')
    wdm.start()
    drv = wdm._webdriver
    adapter = SyncSeleniumAdapter(driver=drv)
    nav = SyncNavigator(driver=adapter, policy=None)
    nav.load(base_url=url)
    # wait briefly for dynamic content and perform a few step scrolls to trigger lazy loads
    import time
    time.sleep(2)
    try:
        nav.scroll(strategy='step', max_scrolls=3, pause_sec=1, scroll_count=3, step_px=800)
    except Exception:
        # fallback: simple sleep
        time.sleep(3)
    time.sleep(2)
    res = adapter.execute_js(probe_snippet)
    import json
    # adapter.execute_js may return driver-native objects; print repr when not JSON-serializable
    try:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    except Exception:
        print('PROBE RESULT (repr):', repr(res))
finally:
    if wdm:
        try:
            wdm.quit()
        except Exception:
            pass
