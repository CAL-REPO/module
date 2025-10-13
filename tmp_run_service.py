from modules.ocr_utils import service

p = r"M:\CALife\CAShop - 구매대행\_code\configs\ocr.yaml"
print('Calling service.run_ocr with:', p)
try:
    items, meta, saved = service.run_ocr(p)
    print('OK: items=', len(items), 'saved=', saved)
except Exception as e:
    import traceback
    print('Raised:', type(e), e)
    traceback.print_exc()
