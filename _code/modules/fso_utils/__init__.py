# -*- coding: utf-8 -*-
# fso_utils/__init__.py
"""
file_utils 패키지

📁 구성 개요
- 정책 정의 (policy)
- 경로 관리 (ops)
- 디렉터리 탐색 (lister)
- 파일 입출력 (io)

이 모듈은 파일 및 디렉터리 관련 모든 I/O, 탐색, 정책 설정 기능을 객체 기반으로 제공합니다.
"""

from .policy import FSOOpsPolicy, FSOExplorerPolicy,  ExistencePolicy, FileExtensionPolicy, FSOIOPolicy
from .ops import FSOOps
from .explorer import FSOExplorer
from .io import FileReader, FileWriter, JsonFileIO, BinaryFileIO

__all__ = [
     # 정책 관련
    "FSOOpsPolicy",
    "FSOExplorerPolicy",
    "FSOIOPolicy",
    "ExistencePolicy",
    "FileExtensionPolicy",

    # 경로/탐색
    "FSOOps",
    "FSOExplorer",

    # I/O 클래스
    "FileReader",
    "FileWriter",
    "JsonFileIO",
    "BinaryFileIO"
]
