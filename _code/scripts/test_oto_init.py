# -*- coding: utf-8 -*-
"""OTO 초기화 테스트 (디버깅용)"""

import os
import sys
from pathlib import Path

# PYTHONPATH 설정
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from cfg_utils import ConfigLoader
from logs_utils import LogManager
from logs_utils.core.policy import LogPolicy

# LogManager 초기화
log = LogManager(LogPolicy()).logger

# 1. ENV 확인
paths_env_key = "CASHOP_PATHS"
paths_yaml_str = os.getenv(paths_env_key)

log.info(f"ENV[{paths_env_key}] = {paths_yaml_str}")

if not paths_yaml_str:
    log.error(f"환경변수 '{paths_env_key}'가 설정되지 않았습니다")
    sys.exit(1)

paths_yaml = Path(paths_yaml_str)
if not paths_yaml.exists():
    log.error(f"paths.local.yaml이 없습니다: {paths_yaml}")
    sys.exit(1)

# 2. paths.local.yaml 로드
log.info(f"\n{'='*80}")
log.info(f"Step 1: paths.local.yaml 로드")
log.info(f"{'='*80}")

try:
    paths_dict = ConfigLoader.load(paths_yaml)
    log.success(f"✅ paths.local.yaml 로드 성공")
    log.info(f"Keys: {list(paths_dict.keys())}")
    
    # 주요 경로 출력
    for key, value in paths_dict.items():
        if isinstance(value, str):
            log.info(f"  {key} = {value}")
except Exception as e:
    log.error(f"❌ paths.local.yaml 로드 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. configs_loader_oto.yaml 경로 추출
log.info(f"\n{'='*80}")
log.info(f"Step 2: configs_loader_oto.yaml 경로 추출")
log.info(f"{'='*80}")

loader_paths = paths_dict.get("configs_loader_file_path", {})
if not loader_paths:
    log.error("configs_loader_file_path 키가 없습니다")
    sys.exit(1)

config_loader_oto_path = Path(loader_paths.get('oto', ''))
log.info(f"config_loader_oto_path = {config_loader_oto_path}")

if not config_loader_oto_path.exists():
    log.error(f"configs_loader_oto.yaml이 없습니다: {config_loader_oto_path}")
    sys.exit(1)

log.success(f"✅ configs_loader_oto.yaml 존재 확인")

# 4. paths_dict를 환경변수로 export
log.info(f"\n{'='*80}")
log.info(f"Step 3: paths_dict를 환경변수로 export")
log.info(f"{'='*80}")

exported_count = 0
for key, value in paths_dict.items():
    if isinstance(value, str):
        os.environ[key] = value
        exported_count += 1
        log.debug(f"  ENV[{key}] = {value}")

log.success(f"✅ 환경변수 등록 완료 ({exported_count}개)")

# 5. ConfigLoader로 configs_loader_oto.yaml 로드
log.info(f"\n{'='*80}")
log.info(f"Step 4: ConfigLoader로 configs_loader_oto.yaml 로드")
log.info(f"{'='*80}")

try:
    loader = ConfigLoader(cfg_like=config_loader_oto_path)
    log.success(f"✅ ConfigLoader 생성 성공")
    
    # Internal data 확인
    log.info(f"Loader data keys: {list(loader._data.keys())}")
    
    # 각 section 확인
    sections = ['image', 'ocr', 'translate', 'overlay']
    for section in sections:
        try:
            section_data = loader._data.get(section)
            if section_data:
                log.info(f"  ✅ section '{section}': {type(section_data)} ({len(section_data) if isinstance(section_data, dict) else 'N/A'} keys)")
            else:
                log.warning(f"  ⚠️  section '{section}': None")
        except Exception as e:
            log.warning(f"  ⚠️  section '{section}' 확인 실패: {e}")
    
except Exception as e:
    log.error(f"❌ ConfigLoader 생성 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 6. 정책 변환 테스트
log.info(f"\n{'='*80}")
log.info(f"Step 5: 정책 변환 테스트")
log.info(f"{'='*80}")

from image_utils.core.policy import ImageLoaderPolicy, ImageOCRPolicy, ImageOverlayPolicy

for section, model in [
    ('image', ImageLoaderPolicy),
    ('ocr', ImageOCRPolicy),
    ('overlay', ImageOverlayPolicy),
]:
    try:
        policy = loader._as_model_internal(model, section=section)
        log.success(f"  ✅ {section}: {type(policy).__name__} 변환 성공")
    except Exception as e:
        log.error(f"  ❌ {section}: 변환 실패: {e}")

log.info(f"\n{'='*80}")
log.success(f"✅ 모든 테스트 완료")
log.info(f"{'='*80}")
