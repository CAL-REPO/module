from pathlib import Path
from typing import Union
import json
import yaml

class FileConvert:
    """파일 단위 객체 저장 및 로드"""

    @staticmethod
    def save_obj(path: Union[str, Path], data, mode: str = 'w'):
        path = Path(path)
        ext = path.suffix.lower()
        with open(path, mode, encoding='utf-8') as f:
            if ext == '.json':
                json.dump(data, f, ensure_ascii=False, indent=2)
            elif ext in {'.yaml', '.yml'}:
                yaml.dump(data, f, allow_unicode=True)
            else:
                raise ValueError(f'Unsupported file format: {ext}')

    @staticmethod
    def load_obj(path: Union[str, Path]):
        path = Path(path)
        ext = path.suffix.lower()
        with open(path, encoding='utf-8') as f:
            if ext == '.json':
                return json.load(f)
            elif ext in {'.yaml', '.yml'}:
                return yaml.safe_load(f)
            else:
                raise ValueError(f'Unsupported file format: {ext}')
