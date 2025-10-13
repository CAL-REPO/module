# base_utils/convert.py
class BaseConvert:
    """기본형(str ↔ bytes) 변환 전담 클래스"""

    @staticmethod
    def to_bytes(text: str, encoding: str = 'utf-8') -> bytes:
        return text.encode(encoding)

    @staticmethod
    def from_bytes(data: bytes, encoding: str = 'utf-8') -> str:
        return data.decode(encoding)