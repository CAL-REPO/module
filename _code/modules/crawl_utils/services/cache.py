"""
크롤링 결과 캐싱 모듈.

TTL 기반 디스크 캐싱과 LRU 메모리 캐싱을 제공합니다.

Features:
- TTL (Time To Live) 기반 만료
- LRU (Least Recently Used) 메모리 캐시
- 디스크 영속성 (JSON 파일)
- URL 해시 기반 캐시 키
- 자동 만료 캐시 정리

Examples:
    >>> from pathlib import Path
    >>> 
    >>> # 기본 사용
    >>> cache = CrawlCache(cache_dir=Path("cache"), ttl_seconds=3600)
    >>> 
    >>> # 캐시 확인
    >>> data = cache.get("https://example.com/product/123")
    >>> if data is None:
    ...     # 크롤링 수행
    ...     data = crawl_product(url)
    ...     cache.set(url, data)
    >>> 
    >>> # LRU 메모리 캐시 (빠른 접근)
    >>> cache_lru = CrawlCache(
    ...     cache_dir=Path("cache"),
    ...     ttl_seconds=3600,
    ...     use_memory_cache=True,
    ...     memory_cache_size=100
    ... )
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from collections import OrderedDict


class LRUCache:
    """LRU (Least Recently Used) 메모리 캐시.
    
    메모리에 최근 사용된 캐시를 유지하여 디스크 I/O를 줄입니다.
    
    Examples:
        >>> cache = LRUCache(max_size=3)
        >>> cache.set("key1", "value1")
        >>> cache.set("key2", "value2")
        >>> cache.set("key3", "value3")
        >>> cache.get("key1")  # "value1"
        >>> cache.set("key4", "value4")  # key2가 evict됨
        >>> cache.get("key2")  # None
    """
    
    def __init__(self, max_size: int = 100):
        """Initialize LRU cache.
        
        Args:
            max_size: 최대 캐시 크기 (기본값: 100)
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기 (LRU 업데이트).
        
        Args:
            key: 캐시 키
        
        Returns:
            캐시된 값 또는 None
        """
        if key not in self._cache:
            return None
        
        # LRU: 최근 사용으로 이동
        self._cache.move_to_end(key)
        return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """캐시에 값 저장 (LRU 업데이트).
        
        Args:
            key: 캐시 키
            value: 저장할 값
        """
        if key in self._cache:
            # 기존 키 업데이트
            self._cache.move_to_end(key)
        else:
            # 새 키 추가
            if len(self._cache) >= self.max_size:
                # 가장 오래된 항목 제거 (LRU)
                self._cache.popitem(last=False)
        
        self._cache[key] = value
    
    def clear(self) -> None:
        """캐시 전체 삭제."""
        self._cache.clear()
    
    def size(self) -> int:
        """현재 캐시 크기."""
        return len(self._cache)


class CrawlCache:
    """크롤링 결과 캐싱 클래스.
    
    TTL 기반 디스크 캐싱과 선택적 LRU 메모리 캐싱을 제공합니다.
    
    Attributes:
        cache_dir: 캐시 파일 저장 디렉토리
        ttl_seconds: TTL (Time To Live) 초 단위
        use_memory_cache: 메모리 캐시 사용 여부
        memory_cache: LRU 메모리 캐시 인스턴스
    
    Examples:
        >>> cache = CrawlCache(
        ...     cache_dir=Path("output/cache"),
        ...     ttl_seconds=3600,  # 1시간
        ...     use_memory_cache=True,
        ...     memory_cache_size=100
        ... )
        >>> 
        >>> # 캐시 확인
        >>> url = "https://example.com/product/123"
        >>> data = cache.get(url)
        >>> if data is None:
        ...     data = {"title": "Product 123", "price": 99.99}
        ...     cache.set(url, data)
        >>> 
        >>> # 통계
        >>> stats = cache.get_stats()
        >>> print(f"Cache hits: {stats['hits']}, misses: {stats['misses']}")
    """
    
    def __init__(
        self,
        cache_dir: Path,
        ttl_seconds: int = 86400,  # 24시간
        use_memory_cache: bool = True,
        memory_cache_size: int = 100
    ):
        """Initialize crawl cache.
        
        Args:
            cache_dir: 캐시 파일 저장 디렉토리
            ttl_seconds: TTL (기본값: 86400초 = 24시간)
            use_memory_cache: 메모리 캐시 사용 여부 (기본값: True)
            memory_cache_size: 메모리 캐시 최대 크기 (기본값: 100)
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.use_memory_cache = use_memory_cache
        
        # 캐시 디렉토리 생성
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # LRU 메모리 캐시
        self.memory_cache: Optional[LRUCache] = None
        if use_memory_cache:
            self.memory_cache = LRUCache(max_size=memory_cache_size)
        
        # 통계
        self._stats = {
            "hits": 0,
            "misses": 0,
            "memory_hits": 0,
            "disk_hits": 0
        }
    
    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """캐시에서 결과 가져오기.
        
        1. 메모리 캐시 확인 (활성화된 경우)
        2. 디스크 캐시 확인
        3. TTL 검증
        
        Args:
            url: 크롤링 URL
        
        Returns:
            캐시된 데이터 또는 None
        """
        cache_key = self._get_cache_key(url)
        
        # 1. 메모리 캐시 확인
        if self.memory_cache:
            cached = self.memory_cache.get(cache_key)
            if cached is not None:
                self._stats["hits"] += 1
                self._stats["memory_hits"] += 1
                return cached
        
        # 2. 디스크 캐시 확인
        cache_file = self._get_cache_file(cache_key)
        if not cache_file.exists():
            self._stats["misses"] += 1
            return None
        
        # 3. TTL 검증
        file_mtime = cache_file.stat().st_mtime
        current_time = time.time()
        
        if current_time - file_mtime > self.ttl_seconds:
            # 만료된 캐시 삭제
            cache_file.unlink()
            self._stats["misses"] += 1
            return None
        
        # 4. 캐시 로드
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            
            # 메모리 캐시에 저장
            if self.memory_cache:
                self.memory_cache.set(cache_key, data)
            
            self._stats["hits"] += 1
            self._stats["disk_hits"] += 1
            return data
        
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            # 손상된 캐시 파일 삭제
            cache_file.unlink()
            self._stats["misses"] += 1
            return None
    
    def set(self, url: str, data: Dict[str, Any]) -> None:
        """캐시에 결과 저장.
        
        1. 디스크에 JSON 저장
        2. 메모리 캐시에 저장 (활성화된 경우)
        
        Args:
            url: 크롤링 URL
            data: 저장할 데이터
        """
        cache_key = self._get_cache_key(url)
        cache_file = self._get_cache_file(cache_key)
        
        # 1. 디스크에 저장
        cache_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 2. 메모리 캐시에 저장
        if self.memory_cache:
            self.memory_cache.set(cache_key, data)
    
    def delete(self, url: str) -> bool:
        """캐시 삭제.
        
        Args:
            url: 크롤링 URL
        
        Returns:
            삭제 성공 여부
        """
        cache_key = self._get_cache_key(url)
        cache_file = self._get_cache_file(cache_key)
        
        # 디스크 캐시 삭제
        if cache_file.exists():
            cache_file.unlink()
        
        # 메모리 캐시는 자동으로 evict되므로 처리 불필요
        return True
    
    def clear_all(self) -> int:
        """모든 캐시 삭제.
        
        Returns:
            삭제된 캐시 파일 수
        """
        # 메모리 캐시 삭제
        if self.memory_cache:
            self.memory_cache.clear()
        
        # 디스크 캐시 삭제
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        
        return count
    
    def clear_expired(self) -> int:
        """만료된 캐시만 삭제.
        
        Returns:
            삭제된 캐시 파일 수
        """
        current_time = time.time()
        count = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            file_mtime = cache_file.stat().st_mtime
            
            if current_time - file_mtime > self.ttl_seconds:
                cache_file.unlink()
                count += 1
        
        return count
    
    def get_stats(self) -> Dict[str, int]:
        """캐시 통계 반환.
        
        Returns:
            통계 딕셔너리 (hits, misses, memory_hits, disk_hits)
        """
        return self._stats.copy()
    
    def get_cache_files(self) -> List[Path]:
        """모든 캐시 파일 리스트 반환.
        
        Returns:
            캐시 파일 경로 리스트
        """
        return list(self.cache_dir.glob("*.json"))
    
    def get_cache_size(self) -> int:
        """디스크 캐시 파일 수 반환.
        
        Returns:
            캐시 파일 개수
        """
        return len(self.get_cache_files())
    
    def _get_cache_key(self, url: str) -> str:
        """URL → 캐시 키 변환 (MD5 해시).
        
        Args:
            url: 크롤링 URL
        
        Returns:
            MD5 해시 문자열
        """
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """캐시 키 → 파일 경로 변환.
        
        Args:
            cache_key: 캐시 키 (MD5 해시)
        
        Returns:
            캐시 파일 경로
        """
        return self.cache_dir / f"{cache_key}.json"
