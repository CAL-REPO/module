# from modules.pillow import process_image

# cfg_path = "M:\\CALife\\CAShop - 구매대행\\_code\\configs\\oto.yaml"

# process_image(cfg_path)

# from modules.ocr import run_ocr

# cfg_path = "M:\\CALife\\CAShop - 구매대행\\_code\\configs\\oto.yaml"

# run_ocr(cfg_path)

# from modules.overlay import render_overlay

# cfg_path = "M:\\CALife\\CAShop - 구매대행\\_code\\configs\\oto.yaml"

# render_overlay(cfg_path)

# from modules.translate import run_translate

# cfg_path = "M:\\CALife\\CAShop - 구매대행\\_code\\configs\\oto.yaml"

# run_translate(cfg_path)

# from scripts.ocr_translate_overlay import run_oto

# cfg_path = "M:\\CALife\\CAShop - 구매대행\\_code\\configs\\oto.yaml"

# run_oto(cfg_path)

# from scripts.run_oto_from_excel import run_xloto
# run_xloto()

# from modules.firefox import load_firefox
# from time import sleep
# cfg_path = "M:\\CALife\\CAShop - 구매대행\\_code\\configs\\crawl.yaml"

# ff = load_firefox(cfg_path)
# sleep(60)
# ff.quit()

# from modules.crawl import run_crawl

# cfg_path = "M:\\CALife\\CAShop - 구매대행\\_code\\configs\\crawl.yaml"

# run_crawl(cfg_path)

# from firefox.driver import FirefoxDriver
# from time import sleep
# cfg_path = "M:\\CALife\\CAShop - 구매대행\\_code\\configs\\crawl.yaml"

# ff = FirefoxDriver(cfg_path, profile_path=None).driver
# sleep(1)
# ff.get("https://www.google.com")
# sleep(1)
# ff.quit()

# from modules.xl_utils.test import test_xlwings_from_yaml

# cfg_path = "M:\\CALife\\CAShop - 구매대행\\_code\\modules\\xl_utils\\excel.yaml"

# test_xlwings_from_yaml(cfg_path=cfg_path)