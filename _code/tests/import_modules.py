# smoke import tester for modules — prints success/failure per module
modules = [
    "cfg_utils",
    "logs_utils",
    "data_utils",
    "structured_data",
    "structured_io",
    "translate_utils",
    "image_utils",
    "fso_utils",
    "crawl_utils",
    "keypath_utils",
    "color_utils",
    "font_utils",
    "path_utils",
    "unify_utils",
    "xl_utils",
    "web_utils",
]

if __name__ == "__main__":
    import importlib, traceback
    for m in modules:
        try:
            importlib.import_module(m)
            print(f"[OK]   {m}")
        except Exception as e:
            print(f"[FAIL] {m} -> {e.__class__.__name__}: {e}")
            traceback.print_exc(limit=1)
