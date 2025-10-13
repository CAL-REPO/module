import json
from modules.ocr_utils.pipeline import _defaults_from_cfg_like

p = r"M:\CALife\CAShop - 구매대행\_code\configs\ocr.yaml"
cfg = _defaults_from_cfg_like(p)
print(type(cfg))
print('file_path repr:', repr(cfg.file.file_path))
print('file field:', json.dumps(cfg.file.dict(), ensure_ascii=False, indent=2))
