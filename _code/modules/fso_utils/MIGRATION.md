# fso_utils Refactor (core / port / adapter)

## What changed
- Introduced **core** (pure policy & rule engine), **adapters** (local FS implementations), and **ports** (interfaces in `core/interfaces.py`).
- Removed external dependency `data_utils.types.PathLike` in core. Replaced with `Union[str, Path]`.
- Kept backward-friendly exports at package root.

## New imports
```python
from fso_utils_refactored import (
  FSOOpsPolicy, FSOExplorerPolicy, FSOIOPolicy, FSONamePolicy,
  FSOOps, FSOExplorer, FSOPathBuilder,
  IPathBuilderPort, IFileSaver,
  LocalFileSaver, FSOPathBuilderAdapter
)
```

## How to wire with crawl_refactor.saver.StorageDispatcher
```python
from fso_utils_refactored import LocalFileSaver, FSOPathBuilderAdapter

saver = StorageDispatcher(
    policy=policy.storage,
    path_port=FSOPathBuilderAdapter(),
    file_saver=LocalFileSaver(),
)
```
