import sys
sys.path.insert(0, 'modules')

from script_utils import EnvBasedConfigInitializer
import json

paths_dict = EnvBasedConfigInitializer.load_paths_from_env()
loader = EnvBasedConfigInitializer.create_config_loader('configs_loader_file_oto', paths_dict)

data = loader._as_dict_internal(section='image')
print(json.dumps(data, indent=2, ensure_ascii=False))
