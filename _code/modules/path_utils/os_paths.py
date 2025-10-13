# -*- coding: utf-8 -*-
# path_utils/os_paths.py

from pathlib import Path
import os

class OSPath:
    def __init__(self):
        self.os_type = os.name

    @staticmethod
    def home() -> Path:
        return Path.home()

    @staticmethod
    def downloads() -> Path:
        # if os.name == 'nt':
        #     # 윈도우 로직
        # else:
        #     # 다른 OS 로직
        return Path.home() / 'Downloads' # 예시