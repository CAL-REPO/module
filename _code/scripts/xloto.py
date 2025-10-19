#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XLOTO - Excel + OTO Pipeline Main Script.

Excel에서 CAS No 추출 → OTO 처리 → Excel 업데이트

Usage:
    python scripts/xloto.py
"""

import sys
from pathlib import Path

# PYTHONPATH 설정
root = Path(__file__).resolve().parent.parent
modules_dir = root / "modules"
scripts_dir = root / "scripts"

if str(modules_dir) not in sys.path:
    sys.path.insert(0, str(modules_dir))
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))


def main():
    """XLOTO 메인 실행 함수."""
    from xloto import Xloto
    
    # ConfigLoader 설정 파일 경로 (하드코딩)
    config_loader_cfg_path = "M:/CALife/CAShop - 구매대행/_code/configs/loader/config_loader_xloto.yaml"
    # cfg_xloto = "M:/CALife/CAShop - 구매대행/_code/configs/xloto.yaml"
    # Xloto EntryPoint 생성 (config_loader_cfg_path 전달)
    xloto = Xloto(config_loader_cfg_path=config_loader_cfg_path)

    # 실행
    result = xloto.run()
    
    # 결과 반환
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
