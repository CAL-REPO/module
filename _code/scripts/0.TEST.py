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
# cfg_path = "M:\\CALife\\CAShop - 구매대행\\_code\\configs\\firefox.yaml"

# ff = FirefoxDriver(cfg_path).driver
# ff.quit()



# from modules.xl_utils.test import test_xlwings_from_yaml

# cfg_path = "M:\\CALife\\CAShop - 구매대행\\_code\\modules\\xl_utils\\excel.yaml"

# test_xlwings_from_yaml(cfg_path=cfg_path)

# from path_utils import home, downloads
# print("Home Directory:", home())
# print("Downloads Directory:", downloads())


# from scripts.oto import OTO
# cfg_loader_path = "M:\\CALife\\CAShop - 구매대행\\_code\\configs\\config_loader_oto.yaml"
# OTO()

# from modules.image_utils.entry_point.loader import ImageLoader

# # ✅ Test 1: config_loader_path override (절대 경로)
# print("\n" + "="*80)
# print("Test 1: config_loader_path override (절대 경로)")
# print("="*80)
# img_loader = ImageLoader(config_loader_path="M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_image.yaml")
# result = img_loader.run()
# print(f"✅ 결과: success={result['success']}, saved_path={result['saved_path']}")

# # ✅ Test 2: cfg_like + config_loader_path 동시 사용
# print("\n" + "="*80)
# print("Test 2: cfg_like + config_loader_path 동시 사용")
# print("="*80)
# img_loader2 = ImageLoader(
#     cfg_like="./configs/oto/image.yaml",
#     config_loader_path="./modules/image_utils/configs/config_loader_image.yaml"
# )

# from modules.image_utils.entry_point.text_recognizer import ImageTextRecognizer
# print("="*80)
# img_ocr = ImageTextRecognizer(
#     config_loader_path="M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_ocr.yaml"
# )
# result = img_ocr.run()


# from modules.translate_utils.services.translator import Translator
# print("="*80)
# img_translate = Translator(
#     config_loader_path="M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_translate.yaml"
# )
# result = img_translate.run()


# from modules.image_utils.entry_point.overlayer import ImageOverlayer
# print("="*80)
# img_overlay = ImageOverlayer(
#     config_loader_path="M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_overlay.yaml"
# )
# result = img_overlay.run()


from scripts.oto import OTO

print("\n" + "="*80)
print("Test OTO Pipeline - OCR -> Translate -> Overlay")
print("="*80)

try:
    # OTO Pipeline 생성 (ImageLoader와 동일한 패턴)
    # cfg_like 없이 config_loader_path만 지정하면 자동으로 로드
    oto = OTO(
        cfg_like={},  # ✅ 빈 dict 전달 (config_loader_path에서 로드)
        config_loader_path="M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_oto.yaml"
    )
    
    # ✅ run() 메서드 사용 (BaseServiceLoader 대칭)
    result = oto.run(
        source_override="m:/CALife/CAShop - 구매대행/_code/input/01.jpg"
    )
    
    if result['success']:
        print(f"\n✅ OTO Pipeline 성공!")
        if result['image']:
            print(f"   최종 이미지: {result['image'].size} {result['image'].mode}")
        if result['ocr_result']:
            print(f"   OCR Items: {len(result['ocr_result']['ocr_items'])}")
        if result['translate_result']:
            print(f"   번역 결과: {len(result['translate_result'])} 텍스트")
        if result['overlay_result']:
            print(f"   오버레이: {result['overlay_result'].get('overlaid_items', 0)}개 아이템")
    else:
        print(f"\n❌ OTO Pipeline 실패: {result['error']}")
        
except Exception as e:
    import traceback
    print(f"\n❌ 예외 발생: {e}")
    traceback.print_exc()


# print(f"✅ 결과: success={result['success']}, saved_path={result['saved_path']}")

# from modules.image_utils.entry_point.overlayer import ImageO
# from PIL import Image

# print("="*80)
# img_loader2 = ImageTextRecognizer(
#     # cfg_like="./configs/oto/image.yaml",
#     config_loader_path="M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_ocr.yaml"
# )

# result2 = img_loader2.run()
# print(f"✅ 결과: success={result2['success']}, saved_path={result2['saved_path']}")


# SyntaxWarning 억제 (외부 라이브러리 modelscope 버그)
# import warnings
# warnings.filterwarnings('ignore', category=SyntaxWarning)

# from modules.image_utils.entry_point.text_recognizer import ImageTextRecognizer
# from PIL import Image

# # ✅ Test 1: ImageTextRecognizer with 파일 경로 (config_loader 사용)
# print("\n" + "="*80)
# print("Test 1: ImageTextRecognizer with 파일 경로 (config_loader_ocr.yaml)")
# print("="*80)
# try:
#     img_ocr = ImageTextRecognizer(
#         config_loader_path="M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_ocr.yaml",
#         source__path="m:/CALife/CAShop - 구매대행/_public/01.IMAGES(BackUp)/CAPFB-002/translated/DETAIL_19.png"
#     )
#     result = img_ocr.run()
#     print(f"✅ 결과: success={result['success']}")
#     print(f"   image type: {type(result.get('image')).__name__}")
#     print(f"   image size: {result.get('image').size if result.get('image') else None}")
#     print(f"   ocr_items count: {len(result.get('ocr_items', []))}")
#     if result.get('ocr_items'):
#         for i, item in enumerate(result['ocr_items'][:3]):
#             print(f"   OCR {i+1}: {item.text[:30]}... (conf={item.conf:.2f})")
# except Exception as e:
#     import traceback
#     print(f"❌ 에러: {e}")
#     traceback.print_exc()

# # ✅ Test 2: ImageTextRecognizer with 단일 Pillow 객체
# print("\n" + "="*80)
# print("Test 2: ImageTextRecognizer with 단일 Pillow 객체")
# print("="*80)
# try:
#     # Pillow 이미지 로드
#     pil_image = Image.open("m:/CALife/CAShop - 구매대행/_public/01.IMAGES(BackUp)/CAPFB-002/translated/DETAIL_19.jpg")
#     print(f"   입력 이미지: {pil_image.format} {pil_image.size} {pil_image.mode}")
    
#     img_ocr = ImageTextRecognizer(
#         config_loader_path="M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_ocr.yaml"
#     )
#     result = img_ocr.run(image=pil_image)
#     print(f"✅ 결과: success={result['success']}")
#     print(f"   ocr_items count: {len(result.get('ocr_items', []))}")
#     if result.get('ocr_items'):
#         for i, item in enumerate(result['ocr_items'][:3]):
#             print(f"   OCR {i+1}: {item.text[:30]}... (conf={item.conf:.2f})")
# except Exception as e:
#     import traceback
#     print(f"❌ 에러: {e}")
#     traceback.print_exc()

# # ✅ Test 3: ImageTextRecognizer with Pillow 객체 리스트 (ImageLoader와 일관성)
# print("\n" + "="*80)
# print("Test 3: ImageTextRecognizer with Pillow 객체 리스트 (완전 대칭 구조)")
# print("="*80)
# try:
#     # 여러 이미지 로드 (리스트)
#     images = [
#         Image.open("m:/CALife/CAShop - 구매대행/_public/01.IMAGES(BackUp)/CAPFB-002/translated/DETAIL_19.png"),
#         Image.open("m:/CALife/CAShop - 구매대행/_public/01.IMAGES(BackUp)/CAPFB-002/translated/DETAIL_19.jpg"),
#     ]
#     print(f"   입력 리스트: {len(images)}개 이미지")
#     for i, img in enumerate(images):
#         print(f"   - Image {i+1}: {img.format} {img.size} {img.mode}")
    
#     img_ocr = ImageTextRecognizer(
#         config_loader_path="M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_ocr.yaml"
#     )
#     # 리스트 전달 → 첫 번째 이미지 사용 (ImageLoader와 동일)
#     result = img_ocr.run(image=images)
#     print(f"✅ 결과: success={result['success']}")
#     print(f"   처리된 이미지: 첫 번째 (일관성 유지)")
#     print(f"   image size: {result.get('image').size if result.get('image') else None}")
#     print(f"   ocr_items count: {len(result.get('ocr_items', []))}")
#     if result.get('ocr_items'):
#         print(f"   첫 번째 OCR: {result['ocr_items'][0].text[:50]}...")
# except Exception as e:
#     import traceback
#     print(f"❌ 에러: {e}")
#     traceback.print_exc()

# # ✅ Test 4: 빈 리스트 검증 (에러 처리)
# print("\n" + "="*80)
# print("Test 4: 빈 리스트 에러 처리 검증")
# print("="*80)
# try:
#     img_ocr = ImageTextRecognizer(
#         config_loader_path="M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_ocr.yaml"
#     )
#     result = img_ocr.run(image=[])  # 빈 리스트
#     print(f"❌ 예상치 못한 성공: {result['success']}")
# except ValueError as e:
#     print(f"✅ 예상된 에러 발생: {e}")
# except Exception as e:
#     print(f"❌ 다른 에러: {e}")