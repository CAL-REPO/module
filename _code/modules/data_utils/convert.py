# data_utils/convert.py (또는 trans_ops.py 안에 포함 가능)
from io import BytesIO
from typing import Any
from PIL import Image
import json
import yaml

class Convert:
    """데이터 간 포맷/타입 변환 유틸리티"""

    @staticmethod
    def bytes_to_image(data: bytes) -> Image.Image:
        """raw bytes → Pillow 이미지 객체"""
        return Image.open(BytesIO(data))

    @staticmethod
    def image_to_bytes(img: Image.Image, format: str = "JPEG", **kwargs) -> bytes:
        """Pillow 이미지 → bytes"""
        buf = BytesIO()
        img.save(buf, format=format, **kwargs)
        return buf.getvalue()

    @staticmethod
    def json_to_dict(text: str) -> dict[str, Any]:
        return json.loads(text)

    @staticmethod
    def dict_to_json(data: dict, **kwargs) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2, **kwargs)

    @staticmethod
    def dict_to_yaml(data: dict, **kwargs) -> str:
        return yaml.dump(data, allow_unicode=True, default_flow_style=False, **kwargs)

    @staticmethod
    def yaml_to_dict(text: str) -> dict:
        return yaml.safe_load(text)
