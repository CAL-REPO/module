# -*- coding: utf-8 -*-
# keypath_utils/policy.py
# Pydantic 기반 KeyPathState 정책 정의

from pydantic import BaseModel, Field

class KeyPathStatePolicy(BaseModel):
    allow_override: bool = Field(True, description="None 값을 허용할 경우 path override 수행")
    deep_merge: bool = Field(True, description="DictOps.deep_update를 기본으로 수행 여부")
