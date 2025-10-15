"""
CASHOP 환경변수 자동 설정 유틸리티

CASHOP_PATHS 환경변수를 자동으로 설정하여 
xloto.py 및 기타 스크립트에서 paths.local.yaml을 쉽게 로드할 수 있도록 합니다.

Usage:
    # 직접 실행
    python setup_env.py
    
    # 다른 스크립트에서 import
    from setup_env import setup_cashop_env
    setup_cashop_env()
"""

import os
import sys
from pathlib import Path
from typing import Optional


def find_config_file(
    filename: str = "paths.local.yaml",
    search_dirs: Optional[list[Path]] = None
) -> Optional[Path]:
    """
    설정 파일을 자동으로 찾습니다.
    
    Args:
        filename: 찾을 설정 파일명 (기본: paths.local.yaml)
        search_dirs: 검색할 디렉토리 리스트 (없으면 자동 생성)
    
    Returns:
        설정 파일 경로 (없으면 None)
    
    검색 순서:
        1. 현재 스크립트 디렉토리/../configs/
        2. 현재 작업 디렉토리/configs/
        3. 부모 디렉토리들의 configs/ (최대 3단계)
    """
    if search_dirs is None:
        script_dir = Path(__file__).parent.resolve()
        cwd = Path.cwd()
        
        search_dirs = [
            # 1. scripts/../configs/
            script_dir.parent / "configs",
            
            # 2. 현재 작업 디렉토리/configs/
            cwd / "configs",
            
            # 3. _code/configs/ (일반적인 구조)
            cwd.parent / "_code" / "configs" if cwd.name != "_code" else cwd / "configs",
            
            # 4. 부모 디렉토리 탐색
            cwd.parent / "configs",
            cwd.parent.parent / "configs",
        ]
    
    # 중복 제거 및 존재하는 경로만 필터링
    unique_dirs = []
    seen = set()
    for d in search_dirs:
        normalized = d.resolve()
        if normalized not in seen and normalized.exists():
            unique_dirs.append(normalized)
            seen.add(normalized)
    
    # 각 디렉토리에서 파일 검색
    for search_dir in unique_dirs:
        config_path = search_dir / filename
        if config_path.exists():
            return config_path
    
    return None


def setup_cashop_env(
    force: bool = False,
    verbose: bool = True,
    config_filename: str = "paths.local.yaml"
) -> bool:
    """
    CASHOP_PATHS 환경변수를 자동으로 설정합니다.
    
    Args:
        force: 이미 설정된 환경변수를 덮어쓸지 여부 (기본: False)
        verbose: 진행 상황 출력 여부 (기본: True)
        config_filename: 설정 파일명 (기본: paths.local.yaml)
    
    Returns:
        성공 여부 (True/False)
    
    Examples:
        >>> setup_cashop_env()
        ✅ CASHOP_PATHS 설정: M:\CALife\CAShop - 구매대행\_code\configs\paths.local.yaml
        True
        
        >>> setup_cashop_env(force=True)
        ⚠️ CASHOP_PATHS 기존 설정 덮어쓰기: ...
        True
    """
    env_key = "CASHOP_PATHS"
    
    # 이미 설정된 경우
    if env_key in os.environ and not force:
        existing_path = os.environ[env_key]
        if verbose:
            print(f"ℹ️ {env_key} 이미 설정됨: {existing_path}")
        
        # 경로가 유효한지 확인
        if Path(existing_path).exists():
            if verbose:
                print(f"✅ 기존 설정 사용")
            return True
        else:
            if verbose:
                print(f"⚠️ 기존 경로가 존재하지 않음. 재설정 시도...")
    
    # 설정 파일 자동 검색
    config_path = find_config_file(config_filename)
    
    if config_path is None:
        if verbose:
            print(f"❌ {config_filename} 파일을 찾을 수 없습니다.")
            print(f"   검색 위치:")
            print(f"   - 스크립트 디렉토리/../configs/")
            print(f"   - 현재 작업 디렉토리/configs/")
            print(f"   - 부모 디렉토리/configs/")
        return False
    
    # 환경변수 설정
    config_path_str = str(config_path)
    os.environ[env_key] = config_path_str
    
    if verbose:
        if force and env_key in os.environ:
            print(f"⚠️ {env_key} 기존 설정 덮어쓰기")
        print(f"✅ {env_key} 설정 완료")
        print(f"   경로: {config_path_str}")
    
    return True


def check_required_env_vars(
    required_vars: list[str] = None,
    verbose: bool = True
) -> dict[str, bool]:
    """
    필수 환경변수가 설정되었는지 확인합니다.
    
    Args:
        required_vars: 확인할 환경변수 리스트 (기본: CASHOP_PATHS, DEEPL_API_KEY)
        verbose: 진행 상황 출력 여부
    
    Returns:
        {환경변수명: 설정여부} 딕셔너리
    
    Examples:
        >>> check_required_env_vars()
        ✅ CASHOP_PATHS: 설정됨
        ❌ DEEPL_API_KEY: 미설정
        {'CASHOP_PATHS': True, 'DEEPL_API_KEY': False}
    """
    if required_vars is None:
        required_vars = ["CASHOP_PATHS", "DEEPL_API_KEY"]
    
    results = {}
    
    if verbose:
        print("\n🔍 환경변수 확인:")
    
    for var in required_vars:
        is_set = var in os.environ and os.environ[var].strip() != ""
        results[var] = is_set
        
        if verbose:
            status = "✅" if is_set else "❌"
            value = os.environ.get(var, "<미설정>")
            if is_set:
                # 보안을 위해 API 키는 일부만 표시
                if "API" in var or "KEY" in var or "TOKEN" in var:
                    if len(value) > 8:
                        display_value = f"{value[:4]}...{value[-4:]}"
                    else:
                        display_value = "****"
                else:
                    display_value = value
                print(f"{status} {var}: {display_value}")
            else:
                print(f"{status} {var}: 미설정")
    
    return results


def print_setup_guide():
    """환경변수 설정 가이드를 출력합니다."""
    print("\n" + "="*60)
    print("📘 CASHOP 환경변수 설정 가이드")
    print("="*60)
    print("\n1️⃣ CASHOP_PATHS (필수)")
    print("   - 역할: paths.local.yaml 경로 지정")
    print("   - 설정 방법:")
    print('     PowerShell: $env:CASHOP_PATHS = "M:\\CALife\\CAShop - 구매대행\\_code\\configs\\paths.local.yaml"')
    print('     CMD: set CASHOP_PATHS=M:\\CALife\\CAShop - 구매대행\\_code\\configs\\paths.local.yaml')
    print("   - 또는: setup_env.py 실행 (자동 설정)")
    
    print("\n2️⃣ DEEPL_API_KEY (필수 - 번역 사용 시)")
    print("   - 역할: DeepL API 인증")
    print("   - 설정 방법:")
    print('     PowerShell: $env:DEEPL_API_KEY = "your-api-key-here"')
    print('     CMD: set DEEPL_API_KEY=your-api-key-here')
    print("   - API 키 발급: https://www.deepl.com/pro-api")
    
    print("\n3️⃣ 영구 설정 (선택)")
    print("   - Windows 환경변수 설정:")
    print("     시스템 속성 > 고급 > 환경 변수 > 새로 만들기")
    print("   - 또는 PowerShell 프로필에 추가:")
    print("     notepad $PROFILE")
    print('     추가: $env:CASHOP_PATHS = "..."')
    print("="*60 + "\n")


def main():
    """메인 실행 함수 (스크립트 직접 실행 시)"""
    print("\n" + "="*60)
    print("🚀 CASHOP 환경변수 설정 유틸리티")
    print("="*60 + "\n")
    
    # 1. CASHOP_PATHS 자동 설정
    success = setup_cashop_env(force=False, verbose=True)
    
    if not success:
        print("\n⚠️ CASHOP_PATHS 자동 설정 실패")
        print_setup_guide()
        return 1
    
    # 2. 필수 환경변수 확인
    results = check_required_env_vars(verbose=True)
    
    # 3. 결과 요약
    all_set = all(results.values())
    
    print("\n" + "="*60)
    if all_set:
        print("✅ 모든 필수 환경변수가 설정되었습니다!")
        print("   xloto.py 실행 준비 완료")
    else:
        print("⚠️ 일부 환경변수가 설정되지 않았습니다.")
        missing = [k for k, v in results.items() if not v]
        print(f"   미설정: {', '.join(missing)}")
        print("\n   설정 가이드:")
        print_setup_guide()
        return 1
    
    print("="*60 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
