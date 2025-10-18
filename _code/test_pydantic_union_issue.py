# -*- coding: utf-8 -*-
"""Pydantic Union 타입 문제 재현 테스트"""

from typing import Union, Optional, Any
from pydantic import BaseModel, Field
from pathlib import Path


# ============================================================
# 문제 재현: Union에 BaseModel이 있을 때
# ============================================================
class ProblematicPolicy(BaseModel):
    """Union에 BaseModel을 먼저 선언한 정책"""
    src: Optional[Union[
        BaseModel, tuple[BaseModel, str],           # BaseModel 먼저
        dict, tuple[dict, str],                     # dict 나중
        str, Path, tuple[Union[str, Path], str]
    ]] = Field(default=None)


class WorkingPolicy(BaseModel):
    """Any 타입을 사용한 정책"""
    src: Optional[Any] = Field(default=None)


# ============================================================
# 테스트
# ============================================================
def test_union_with_basemodel():
    """Union에 BaseModel이 있을 때 dict가 어떻게 변환되는지 확인"""
    print("\n" + "=" * 60)
    print("테스트 1: Union[BaseModel, dict] - dict 입력")
    print("=" * 60)
    
    test_dict = {"max_width": 1024, "format": "PNG"}
    print(f"📥 입력 dict: {test_dict}")
    print(f"📥 입력 type: {type(test_dict)}")
    
    try:
        policy = ProblematicPolicy(src=test_dict)
        print(f"\n✅ Policy 생성 성공")
        print(f"📦 policy.src type: {type(policy.src)}")
        print(f"📦 policy.src value: {policy.src}")
        
        # isinstance 체크
        print(f"\n🔍 isinstance 체크:")
        print(f"  - isinstance(policy.src, BaseModel): {isinstance(policy.src, BaseModel)}")
        print(f"  - isinstance(policy.src, dict): {isinstance(policy.src, dict)}")
        
        # BaseModel이면 model_dump() 시도
        if isinstance(policy.src, BaseModel):
            print(f"\n⚠️  BaseModel로 인식됨! model_dump() 실행:")
            try:
                dumped = policy.src.model_dump()
                print(f"  📦 model_dump() 결과: {dumped}")
                print(f"  ❌ 원본 데이터 소실! 입력: {test_dict}, 출력: {dumped}")
            except Exception as e:
                print(f"  ❌ model_dump() 실패: {e}")
        
    except Exception as e:
        print(f"❌ Policy 생성 실패: {e}")


def test_any_type():
    """Any 타입을 사용했을 때 dict가 그대로 유지되는지 확인"""
    print("\n" + "=" * 60)
    print("테스트 2: Any 타입 - dict 입력")
    print("=" * 60)
    
    test_dict = {"max_width": 1024, "format": "PNG"}
    print(f"📥 입력 dict: {test_dict}")
    print(f"📥 입력 type: {type(test_dict)}")
    
    try:
        policy = WorkingPolicy(src=test_dict)
        print(f"\n✅ Policy 생성 성공")
        print(f"📦 policy.src type: {type(policy.src)}")
        print(f"📦 policy.src value: {policy.src}")
        
        # isinstance 체크
        print(f"\n🔍 isinstance 체크:")
        print(f"  - isinstance(policy.src, BaseModel): {isinstance(policy.src, BaseModel)}")
        print(f"  - isinstance(policy.src, dict): {isinstance(policy.src, dict)}")
        
        if isinstance(policy.src, dict):
            print(f"\n✅ dict로 정상 인식! 데이터 유지됨")
            print(f"  📦 원본 데이터: {test_dict}")
            print(f"  📦 policy.src: {policy.src}")
            print(f"  ✅ 일치: {test_dict == policy.src}")
        
    except Exception as e:
        print(f"❌ Policy 생성 실패: {e}")


def test_tuple_with_dict():
    """(dict, section) 튜플 형태로 입력했을 때"""
    print("\n" + "=" * 60)
    print("테스트 3: Union - (dict, section) 튜플 입력")
    print("=" * 60)
    
    test_data = ({"max_width": 1024}, "image")
    print(f"📥 입력 tuple: {test_data}")
    
    try:
        policy = ProblematicPolicy(src=test_data)
        print(f"\n✅ Policy 생성 성공")
        print(f"📦 policy.src type: {type(policy.src)}")
        print(f"📦 policy.src value: {policy.src}")
        
        if isinstance(policy.src, tuple):
            data, section = policy.src
            print(f"\n🔍 튜플 언팩:")
            print(f"  - data type: {type(data)}")
            print(f"  - data value: {data}")
            print(f"  - section: {section}")
            
            print(f"\n🔍 isinstance 체크 (data):")
            print(f"  - isinstance(data, BaseModel): {isinstance(data, BaseModel)}")
            print(f"  - isinstance(data, dict): {isinstance(data, dict)}")
        
    except Exception as e:
        print(f"❌ Policy 생성 실패: {e}")


# ============================================================
# 메인 실행
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 Pydantic Union 타입 문제 재현")
    print("=" * 60)
    
    test_union_with_basemodel()
    test_any_type()
    test_tuple_with_dict()
    
    print("\n" + "=" * 60)
    print("📊 결론")
    print("=" * 60)
    print("✅ Any 타입: dict가 그대로 유지됨 (정상)")
    print("❌ Union[BaseModel, dict]: dict가 BaseModel로 변환 시도 → 데이터 소실")
    print("=" * 60)
