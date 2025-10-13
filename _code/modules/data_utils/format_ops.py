"""Data format conversion utilities.

This module provides a set of static methods for converting between
different data formats, such as raw bytes and images or Python
dictionaries and JSON/YAML strings.
"""

from io import BytesIO
from typing import Any
from PIL import Image
import json
import yaml


class FormatOps:
    """Utility class for converting between different data formats and types."""

    @staticmethod
    def bytes_to_image(data: bytes) -> Image.Image:
        """Convert raw bytes to a Pillow Image object.

        Args:
            data: A bytes object representing image data.

        Returns:
            An instance of :class:`PIL.Image.Image` loaded from the given bytes.
        """
        return Image.open(BytesIO(data))

    @staticmethod
    def image_to_bytes(img: Image.Image, format: str = "JPEG", **kwargs) -> bytes:
        """Serialize a Pillow Image object to raw bytes.

        Args:
            img: The Pillow image to serialize.
            format: The image format to use when saving (e.g. 'JPEG', 'PNG').
            **kwargs: Additional keyword arguments forwarded to :meth:`PIL.Image.Image.save`.

        Returns:
            A bytes object representing the saved image.
        """
        buf = BytesIO()
        img.save(buf, format=format, **kwargs)
        return buf.getvalue()

    @staticmethod
    def json_to_dict(text: str) -> dict[str, Any]:
        """Parse a JSON string into a Python dictionary."""
        return json.loads(text)

    @staticmethod
    def dict_to_json(data: dict, **kwargs) -> str:
        """Serialize a Python dictionary to a JSON-formatted string.

        Args:
            data: The dictionary to serialize.
            **kwargs: Additional keyword arguments forwarded to :func:`json.dumps`.

        Returns:
            A JSON-formatted string.
        """
        return json.dumps(data, ensure_ascii=False, indent=2, **kwargs)

    @staticmethod
    def dict_to_yaml(data: dict, **kwargs) -> str:
        """Serialize a Python dictionary to a YAML-formatted string.

        Args:
            data: The dictionary to serialize.
            **kwargs: Additional keyword arguments forwarded to :func:`yaml.dump`.

        Returns:
            A YAML-formatted string.
        """
        return yaml.dump(data, allow_unicode=True, default_flow_style=False, **kwargs)

    @staticmethod
    def yaml_to_dict(text: str) -> dict:
        """Parse a YAML string into a Python dictionary."""
        return yaml.safe_load(text)
