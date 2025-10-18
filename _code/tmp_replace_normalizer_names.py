import pathlib

replacements = {
    "normalizers/keypath.py": "normalizers/keypath.py",
    "normalizers/list.py": "normalizers/list.py",
    "normalizers/rule.py": "normalizers/rule.py",
    "normalizers/value.py": "normalizers/value.py",
    "keypath.py": "keypath.py",
    "list.py": "list.py",
    "rule.py": "rule.py",
    "value.py": "value.py",
}

root = pathlib.Path('.')
for path in root.rglob('*'):
    if path.is_file():
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            text = path.read_text(encoding='utf-8', errors='ignore')
        original = text
        for old, new in replacements.items():
            text = text.replace(old, new)
        if text != original:
            path.write_text(text, encoding='utf-8')
