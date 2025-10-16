import sys
sys.path.insert(0, 'modules')

from script_utils import EnvBasedConfigInitializer
import json

paths_dict = EnvBasedConfigInitializer.load_paths_from_env()
loader = EnvBasedConfigInitializer.create_config_loader('configs_loader_file_oto', paths_dict)

# 전체 데이터 확인
print("=== 전체 데이터 ===")
all_data = loader._data
print(f"Type: {type(all_data)}")
print(f"Data: {dict(all_data)}")
print()

# image 섹션 확인
data_dict = dict(all_data)
if 'image' in data_dict:
    print("=== image 섹션 ===")
    print(json.dumps(data_dict['image'], indent=2, ensure_ascii=False))
else:
    print("⚠️  'image' 섹션이 없습니다!")
    print(f"Available keys: {list(data_dict.keys())}")
