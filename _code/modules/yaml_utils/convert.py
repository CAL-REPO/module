# yaml_utils/convert.py
import yaml

class YAMLConvert:
    """YAML 직렬화/역직렬화 전담 클래스"""

    @staticmethod
    def to_yaml(data) -> str:
        return yaml.dump(data, allow_unicode=True)

    @staticmethod
    def from_yaml(yaml_str: str):
        return yaml.safe_load(yaml_str)