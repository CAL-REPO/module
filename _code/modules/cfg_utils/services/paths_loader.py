# -*- coding: utf-8 -*-
# cfg_utils/services/paths_loader.py

"""PathsLoader: CASHOP_PATHS 환경변수로 지정된 paths.local.yaml 로더.

SRP 준수:
- 환경변수에서 경로 파일 위치 읽기
- YAML 파싱 + 내부 참조 치환 ({{ }} 패턴)
- reference_context로 사용할 dict 반환

특징:
- 메모리 캐싱 (반복 로드 방지)
- cfg_utils 내부 모듈 (YamlParser, PlaceholderResolver 재사용)
- ConfigPolicy.reference_context에 직접 주입 가능
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Optional

from modules.structured_io.formats.yaml_io import YamlParser
from modules.structured_io.core.base_policy import BaseParserPolicy


class PathsLoader:
    """CASHOP_PATHS 환경변수로 지정된 paths.local.yaml 로더.
    
    사용 예시::
    
        # 방법 1: 명시적 로드
        paths_dict = PathsLoader.load()
        policy = ConfigPolicy(reference_context=paths_dict)
        
        # 방법 2: BaseServiceLoader에서 사용
        class ImageLoader(BaseServiceLoader[ImageLoaderPolicy]):
            def _get_reference_context(self) -> dict:
                return PathsLoader.load()
    
    캐싱:
        - 첫 로드 후 메모리 캐싱
        - force_reload=True로 캐시 무시 가능
        - clear_cache()로 캐시 초기화 (테스트용)
    """
    
    _cache: dict[str, Any] | None = None
    
    @classmethod
    def load(
        cls,
        *,
        env_key: str = "CASHOP_PATHS",
        force_reload: bool = False
    ) -> dict[str, Any]:
        """paths.local.yaml 로드 및 내부 치환.
        
        처리 순서:
        1. 환경변수에서 파일 경로 읽기
        2. YamlParser로 YAML 파일 로드 ({{ }} 패턴 치환)
        3. PlaceholderResolver로 중첩 참조 치환 ({{base_path}} 등)
        4. 메모리 캐싱
        
        Args:
            env_key: 환경변수 키 (기본: "CASHOP_PATHS")
            force_reload: True이면 캐시 무시하고 재로드
            
        Returns:
            치환 완료된 paths dict
            
        Raises:
            FileNotFoundError: 환경변수 미설정 또는 파일 없음
            RuntimeError: YAML 파싱 실패
            
        Example::
        
            # 환경변수 설정: CASHOP_PATHS=M:/CALife/.../paths.local.yaml
            paths = PathsLoader.load()
            # {
            #   "root": "M:/CALife/CAShop - 구매대행",
            #   "base_path": "M:/CALife/CAShop - 구매대행/_code",
            #   "scripts_dir": "M:/CALife/.../scripts",  # ← 치환 완료
            #   ...
            # }
        """
        # 캐시 확인
        if cls._cache is not None and not force_reload:
            return cls._cache
        
        # 1️⃣ 환경변수에서 파일 경로 읽기
        env_path = os.getenv(env_key)
        if not env_path:
            raise FileNotFoundError(
                f"환경변수 '{env_key}'가 설정되지 않았습니다.\n"
                f"다음 명령으로 설정해주세요:\n"
                f"  Windows: $env:{env_key}=\"경로\\paths.local.yaml\"\n"
                f"  Linux/Mac: export {env_key}=\"경로/paths.local.yaml\""
            )
        
        file_path = Path(env_path)
        if not file_path.exists():
            raise FileNotFoundError(
                f"paths.local.yaml 파일을 찾을 수 없습니다: {file_path}\n"
                f"환경변수 '{env_key}' 경로를 확인해주세요."
            )
        
        # 2️⃣ YamlParser로 파일 로드 ({{ }} 패턴 치환)
        parser_policy = BaseParserPolicy(
            enable_placeholder=True,   # ✅ {{base_path}} 치환
            enable_env=False,          # ❌ 환경 변수 비활성화 (paths.local.yaml은 순수 경로만)
            enable_reference=False,    # ❌ 비활성화 (더 이상 사용 안 함)
            encoding="utf-8",
            on_error="raise"
        )
        
        try:
            parser = YamlParser(parser_policy, context={})
            data = parser.parse(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise RuntimeError(
                f"paths.local.yaml 파싱 실패: {file_path}\n"
                f"원인: {e}"
            ) from e
        
        # 3️⃣ 중첩 참조 치환 ({{base_path}} → 실제 경로)
        # PlaceholderResolver로 재귀 치환 (context=data 자신)
        # 루프로 더 이상 {{}}가 없을 때까지 치환 (중첩 참조 지원)
        from unify_utils.resolver.placeholder import PlaceholderResolver
        try:
            max_iterations = 10  # 무한 루프 방지
            for i in range(max_iterations):
                resolver = PlaceholderResolver(context=data, recursive=True, strict=False)
                resolved = resolver.apply(data)
                
                # 더 이상 변화가 없으면 종료
                if resolved == data:
                    break
                    
                data = resolved
            else:
                # max_iterations 초과 (순환 참조 가능성)
                raise RuntimeError(
                    f"paths.local.yaml 순환 참조 가능성: {max_iterations}회 치환 후에도 종료되지 않음"
                )
        except Exception as e:
            raise RuntimeError(
                f"paths.local.yaml 내부 참조 해석 실패: {file_path}\n"
                f"원인: {e}\n"
                f"힌트: {{{{base_path}}}}, {{{{root}}}} 등의 참조가 올바른지 확인하세요."
            ) from e
        
        # 4️⃣ 캐싱
        cls._cache = data
        return data
    
    @classmethod
    def clear_cache(cls) -> None:
        """캐시 초기화 (주로 테스트용).
        
        Example::
        
            # 테스트 케이스 간 캐시 초기화
            PathsLoader.clear_cache()
            paths = PathsLoader.load()  # 재로드
        """
        cls._cache = None
    
    @classmethod
    def is_cached(cls) -> bool:
        """캐시 존재 여부 확인.
        
        Returns:
            True이면 캐시 존재, False이면 미캐싱
        """
        return cls._cache is not None
    
    @classmethod
    def get_cached(cls) -> dict[str, Any] | None:
        """캐시된 데이터 반환 (로드하지 않음).
        
        Returns:
            캐시된 dict 또는 None
        """
        return cls._cache

