"""ConfigLoader와 YamlParser의 흐름 분석"""
from pathlib import Path
import os
from modules.cfg_utils.services.config_loader import ConfigLoader

print("="*80)
print("CONFIG LOADER ARCHITECTURE ANALYSIS")
print("="*80)

# 1단계: paths.local.yaml 로드
print("\n[1단계] paths.local.yaml 로드")
print("-"*80)
paths_yaml = Path(os.getenv("CASHOP_PATHS"))
paths_dict = ConfigLoader.load(paths_yaml)

print(f"temp_input_dir: {paths_dict.get('temp_input_dir')}")
print(f"base_path: {paths_dict.get('base_path')}")

# 2단계: config_loader_image.yaml 경로
print("\n[2단계] config_loader_image.yaml 기반 ConfigLoader 생성")
print("-"*80)
config_loader_path = paths_dict['configs_loader_file_path']['image']
print(f"config_loader_path: {config_loader_path}")

# 절대 경로 계산
oto_image_yaml = Path(config_loader_path).parent.parent / "oto" / "image.yaml"
print(f"oto_image_yaml (계산됨): {oto_image_yaml}")

# 3단계: ConfigLoader 생성 및 정책 확인
print("\n[3단계] ConfigLoader 인스턴스 생성")
print("-"*80)
loader = ConfigLoader(
    cfg_like={},
    policy_overrides={
        "config_loader_path": str(config_loader_path),
        "yaml.source_paths": {"path": str(oto_image_yaml), "section": "image"}
    }
)

print(f"loader.policy.yaml.source_paths: {loader.policy.yaml.source_paths}")
print(f"loader.policy.yaml.enable_placeholder: {loader.policy.yaml.enable_placeholder}")
print(f"loader.policy.yaml.enable_reference: {loader.policy.yaml.enable_reference}")

# 4단계: 내부 데이터 확인
print("\n[4단계] 로드된 데이터 구조")
print("-"*80)
print(f"_data keys: {list(loader._data.data.keys())}")

if 'source' in loader._data.data:
    source_data = loader._data.data['source']
    print(f"source.path (raw): {source_data.get('path') if isinstance(source_data, dict) else 'N/A'}")

# 5단계: oto/image.yaml 파일을 직접 읽어서 확인
print("\n[5단계] oto/image.yaml 직접 파싱 (placeholder 해석 확인)")
print("-"*80)
from modules.structured_io.formats.yaml_io import YamlParser
from modules.structured_io.core.base_policy import BaseParserPolicy

policy = BaseParserPolicy(
    enable_placeholder=True,
    enable_env=True,
    enable_reference=True
)
parser = YamlParser(policy=policy, context=paths_dict)

text = oto_image_yaml.read_text(encoding='utf-8')
print(f"\n원본 YAML 일부:")
print(text[:300])

parsed = parser.parse(text, base_path=oto_image_yaml.parent)
print(f"\n파싱 후 image.source.path: {parsed.get('image', {}).get('source', {}).get('path')}")

# 6단계: PlaceholderResolver 직접 테스트
print("\n[6단계] PlaceholderResolver 직접 테스트")
print("-"*80)
from unify_utils.normalizers.resolver_placeholder import PlaceholderResolver

test_string = "${temp_input_dir}/01.jpg"
resolver = PlaceholderResolver(context=paths_dict, recursive=True)
resolved = resolver.apply(test_string)
print(f"Input:  {test_string}")
print(f"Output: {resolved}")

# 7단계: context 내용 확인
print("\n[7단계] PlaceholderResolver context 확인")
print("-"*80)
print(f"temp_input_dir in context: {'temp_input_dir' in paths_dict}")
print(f"temp_input_dir value: {paths_dict.get('temp_input_dir')}")
