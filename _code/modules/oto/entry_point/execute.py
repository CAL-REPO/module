# -*- coding: utf-8 -*-
"""OTO EntryPoint 실행 예제.

Runtime에서 직접 호출할 때 사용하는 방식.
"""

from pathlib import Path
from oto.entry_point.runner import main as oto_main


def main():
    """OTO Pipeline 실행."""
    config_path = "M:/CALife/CAShop - 구매대행/_code/modules/oto/configs/oto_config_loader.yaml"
    env_os = ["CASHOP_PATHS"]
    source_files = [
        Path("M:/CALife/CAShop - 구매대행/_code/modules/oto/test/images/01.jpg"),
        Path("M:/CALife/CAShop - 구매대행/_code/modules/oto/test/images/02.jpg")
    ]
    
    exit_code = oto_main(
        config_loader_cfg_path=config_path,
        source_file_paths=source_files,
        env_os=env_os,
    )
    
    return exit_code


if __name__ == "__main__":
    import sys
    sys.exit(main())
