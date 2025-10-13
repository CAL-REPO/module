# json_utils/convert.py
import json

class JSONConvert:
    """JSON 직렬화/역직렬화 전담 클래스"""

    @staticmethod
    def to_json(data, indent: int = 2) -> str:
        return json.dumps(data, indent=indent, ensure_ascii=False)

    @staticmethod
    def from_json(json_str: str):
        return json.loads(json_str)