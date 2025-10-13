# -*- coding: utf-8 -*-
from .core.policy import (
    FSOOpsPolicy, FSOExplorerPolicy, ExistencePolicy, FileExtensionPolicy, FSOIOPolicy, FSONamePolicy
)
from .core.ops import FSOOps
from .core.explorer import FSOExplorer
from .core.path_builder import FSOPathBuilder
from .core.interfaces import IPathBuilderPort, IFileSaver
# The adapter package is singular (`adapter`), not `adapters`. Import from the correct package.
from .adapters.local_io import LocalFileSaver, FSOPathBuilderAdapter

__all__ = [
    'FSOOpsPolicy','FSOExplorerPolicy','FSOIOPolicy','FSONamePolicy','ExistencePolicy','FileExtensionPolicy',
    'FSOOps','FSOExplorer','FSOPathBuilder',
    'IPathBuilderPort','IFileSaver',
    'LocalFileSaver','FSOPathBuilderAdapter',
]
