# pillow_utils/convert.py
import base64
from io import BytesIO
from PIL import Image

class ImageConvert:
    """이미지 ↔ bytes ↔ base64 변환 전담 클래스"""

    @staticmethod
    def image_to_bytes(image: Image.Image, format_: str = 'PNG') -> bytes:
        buffer = BytesIO()
        image.save(buffer, format=format_)
        return buffer.getvalue()

    @staticmethod
    def bytes_to_image(data: bytes) -> Image.Image:
        return Image.open(BytesIO(data))

    @staticmethod
    def to_base64(image: Image.Image, format_: str = 'PNG') -> str:
        return base64.b64encode(ImageConvert.image_to_bytes(image, format_)).decode('utf-8')