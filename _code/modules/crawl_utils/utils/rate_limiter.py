"""
Rate Limiting 유틸리티 모듈.

토큰 버킷(Token Bucket)과 슬라이딩 윈도우(Sliding Window) 알고리즘을 제공합니다.

Features:
- 동기/비동기 Rate Limiter
- 토큰 버킷 알고리즘
- 슬라이딩 윈도우 알고리즘
- 요청당/초당 제한
- 버스트(burst) 트래픽 지원

Examples:
    >>> # 동기 Rate Limiter (초당 2개 요청)
    >>> limiter = SyncRateLimiter(requests_per_second=2.0)
    >>> for i in range(10):
    ...     limiter.acquire()  # 자동으로 대기
    ...     print(f"Request {i}")
    >>> 
    >>> # 비동기 Rate Limiter
    >>> limiter = AsyncRateLimiter(requests_per_second=2.0)
    >>> for i in range(10):
    ...     await limiter.acquire()
    ...     print(f"Request {i}")
    >>> 
    >>> # 데코레이터 사용
    >>> limiter = SyncRateLimiter(requests_per_second=1.0)
    >>> 
    >>> @limiter.limit
    >>> def api_request(url):
    ...     return requests.get(url)
    >>> 
    >>> api_request("https://example.com")  # 자동 rate limiting
"""

import time
import asyncio
import threading
from typing import Optional, Callable, TypeVar, Any
from functools import wraps
from collections import deque

T = TypeVar('T')


class SyncRateLimiter:
    """동기 Rate Limiter (토큰 버킷 알고리즘).
    
    토큰 버킷 알고리즘:
    - 버킷에 일정 속도로 토큰이 채워짐
    - 요청 시 토큰 1개 소비
    - 토큰이 없으면 대기
    
    Attributes:
        rate: 초당 요청 수 (requests per second)
        tokens: 현재 보유 토큰 수
        last_update: 마지막 토큰 업데이트 시간
        lock: 스레드 안전성을 위한 Lock
    
    Examples:
        >>> limiter = SyncRateLimiter(requests_per_second=2.0)
        >>> 
        >>> for i in range(5):
        ...     limiter.acquire()  # 0.5초마다 요청 허용
        ...     print(f"Request {i}")
    """
    
    def __init__(
        self,
        requests_per_second: float,
        burst_size: Optional[int] = None
    ):
        """Initialize sync rate limiter.
        
        Args:
            requests_per_second: 초당 요청 수 (예: 2.0 = 초당 2개)
            burst_size: 버스트 크기 (기본값: requests_per_second)
                       한 번에 허용할 최대 요청 수
        """
        self.rate = requests_per_second
        self.burst_size = burst_size or int(requests_per_second)
        self.tokens = float(self.burst_size)
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def acquire(self, tokens: int = 1) -> float:
        """토큰 획득 (필요시 대기).
        
        Args:
            tokens: 소비할 토큰 수 (기본값: 1)
        
        Returns:
            대기 시간 (초)
        """
        with self.lock:
            # 토큰 충전
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.burst_size,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            # 토큰 부족 시 대기
            if self.tokens < tokens:
                wait_time = (tokens - self.tokens) / self.rate
                time.sleep(wait_time)
                self.tokens = 0.0
                self.last_update = time.time()
                return wait_time
            else:
                # 토큰 소비
                self.tokens -= tokens
                return 0.0
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """토큰 획득 시도 (대기 없음).
        
        Args:
            tokens: 소비할 토큰 수 (기본값: 1)
        
        Returns:
            획득 성공 여부
        """
        with self.lock:
            # 토큰 충전
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.burst_size,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            # 토큰 확인
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False
    
    def limit(self, func: Callable[..., T]) -> Callable[..., T]:
        """Rate limiting 데코레이터.
        
        Examples:
            >>> limiter = SyncRateLimiter(requests_per_second=1.0)
            >>> 
            >>> @limiter.limit
            >>> def api_request(url):
            ...     return requests.get(url)
            >>> 
            >>> api_request("https://example.com")  # 자동 rate limiting
        """
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            self.acquire()
            return func(*args, **kwargs)
        return wrapper


class AsyncRateLimiter:
    """비동기 Rate Limiter (토큰 버킷 알고리즘).
    
    토큰 버킷 알고리즘:
    - 버킷에 일정 속도로 토큰이 채워짐
    - 요청 시 토큰 1개 소비
    - 토큰이 없으면 대기
    
    Attributes:
        rate: 초당 요청 수 (requests per second)
        tokens: 현재 보유 토큰 수
        last_update: 마지막 토큰 업데이트 시간
        lock: asyncio Lock (비동기 안전성)
    
    Examples:
        >>> limiter = AsyncRateLimiter(requests_per_second=2.0)
        >>> 
        >>> for i in range(5):
        ...     await limiter.acquire()  # 0.5초마다 요청 허용
        ...     print(f"Request {i}")
    """
    
    def __init__(
        self,
        requests_per_second: float,
        burst_size: Optional[int] = None
    ):
        """Initialize async rate limiter.
        
        Args:
            requests_per_second: 초당 요청 수 (예: 2.0 = 초당 2개)
            burst_size: 버스트 크기 (기본값: requests_per_second)
        """
        self.rate = requests_per_second
        self.burst_size = burst_size or int(requests_per_second)
        self.tokens = float(self.burst_size)
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> float:
        """토큰 획득 (필요시 대기).
        
        Args:
            tokens: 소비할 토큰 수 (기본값: 1)
        
        Returns:
            대기 시간 (초)
        """
        async with self.lock:
            # 토큰 충전
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.burst_size,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            # 토큰 부족 시 대기
            if self.tokens < tokens:
                wait_time = (tokens - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
                self.last_update = time.time()
                return wait_time
            else:
                # 토큰 소비
                self.tokens -= tokens
                return 0.0
    
    async def try_acquire(self, tokens: int = 1) -> bool:
        """토큰 획득 시도 (대기 없음).
        
        Args:
            tokens: 소비할 토큰 수 (기본값: 1)
        
        Returns:
            획득 성공 여부
        """
        async with self.lock:
            # 토큰 충전
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.burst_size,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            # 토큰 확인
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False
    
    def limit(self, func: Callable[..., T]) -> Callable[..., T]:
        """Rate limiting 데코레이터 (비동기).
        
        Examples:
            >>> limiter = AsyncRateLimiter(requests_per_second=1.0)
            >>> 
            >>> @limiter.limit
            >>> async def api_request(url):
            ...     async with aiohttp.ClientSession() as session:
            ...         return await session.get(url)
            >>> 
            >>> await api_request("https://example.com")
        """
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            await self.acquire()
            return await func(*args, **kwargs)
        return wrapper


class SlidingWindowRateLimiter:
    """슬라이딩 윈도우 Rate Limiter (동기).
    
    슬라이딩 윈도우 알고리즘:
    - 최근 N초 동안의 요청 수를 추적
    - 윈도우가 시간에 따라 슬라이딩
    - 정확한 요청 수 제어
    
    토큰 버킷 vs 슬라이딩 윈도우:
    - 토큰 버킷: 버스트 트래픽 허용, 평균 제어
    - 슬라이딩 윈도우: 정확한 요청 수 제한
    
    Examples:
        >>> # 10초 동안 최대 5개 요청
        >>> limiter = SlidingWindowRateLimiter(
        ...     max_requests=5,
        ...     window_seconds=10.0
        ... )
        >>> 
        >>> for i in range(10):
        ...     limiter.acquire()
        ...     print(f"Request {i}")
    """
    
    def __init__(
        self,
        max_requests: int,
        window_seconds: float
    ):
        """Initialize sliding window rate limiter.
        
        Args:
            max_requests: 윈도우 내 최대 요청 수
            window_seconds: 윈도우 크기 (초)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self.lock = threading.Lock()
    
    def acquire(self) -> float:
        """요청 획득 (필요시 대기).
        
        Returns:
            대기 시간 (초)
        """
        with self.lock:
            now = time.time()
            
            # 윈도우 밖 요청 제거
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()
            
            # 요청 수 확인
            if len(self.requests) >= self.max_requests:
                # 가장 오래된 요청이 윈도우 밖으로 나갈 때까지 대기
                oldest_request = self.requests[0]
                wait_time = oldest_request + self.window_seconds - now
                time.sleep(wait_time)
                
                # 다시 윈도우 밖 요청 제거
                now = time.time()
                while self.requests and self.requests[0] < now - self.window_seconds:
                    self.requests.popleft()
                
                # 요청 추가
                self.requests.append(now)
                return wait_time
            else:
                # 요청 추가
                self.requests.append(now)
                return 0.0
    
    def try_acquire(self) -> bool:
        """요청 획득 시도 (대기 없음).
        
        Returns:
            획득 성공 여부
        """
        with self.lock:
            now = time.time()
            
            # 윈도우 밖 요청 제거
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()
            
            # 요청 수 확인
            if len(self.requests) >= self.max_requests:
                return False
            else:
                self.requests.append(now)
                return True
    
    def limit(self, func: Callable[..., T]) -> Callable[..., T]:
        """Rate limiting 데코레이터.
        
        Examples:
            >>> limiter = SlidingWindowRateLimiter(
            ...     max_requests=10,
            ...     window_seconds=60.0
            ... )
            >>> 
            >>> @limiter.limit
            >>> def api_request(url):
            ...     return requests.get(url)
            >>> 
            >>> api_request("https://example.com")
        """
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            self.acquire()
            return func(*args, **kwargs)
        return wrapper


class AsyncSlidingWindowRateLimiter:
    """슬라이딩 윈도우 Rate Limiter (비동기).
    
    슬라이딩 윈도우 알고리즘:
    - 최근 N초 동안의 요청 수를 추적
    - 윈도우가 시간에 따라 슬라이딩
    - 정확한 요청 수 제어
    
    Examples:
        >>> # 10초 동안 최대 5개 요청
        >>> limiter = AsyncSlidingWindowRateLimiter(
        ...     max_requests=5,
        ...     window_seconds=10.0
        ... )
        >>> 
        >>> for i in range(10):
        ...     await limiter.acquire()
        ...     print(f"Request {i}")
    """
    
    def __init__(
        self,
        max_requests: int,
        window_seconds: float
    ):
        """Initialize async sliding window rate limiter.
        
        Args:
            max_requests: 윈도우 내 최대 요청 수
            window_seconds: 윈도우 크기 (초)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> float:
        """요청 획득 (필요시 대기).
        
        Returns:
            대기 시간 (초)
        """
        async with self.lock:
            now = time.time()
            
            # 윈도우 밖 요청 제거
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()
            
            # 요청 수 확인
            if len(self.requests) >= self.max_requests:
                # 가장 오래된 요청이 윈도우 밖으로 나갈 때까지 대기
                oldest_request = self.requests[0]
                wait_time = oldest_request + self.window_seconds - now
                await asyncio.sleep(wait_time)
                
                # 다시 윈도우 밖 요청 제거
                now = time.time()
                while self.requests and self.requests[0] < now - self.window_seconds:
                    self.requests.popleft()
                
                # 요청 추가
                self.requests.append(now)
                return wait_time
            else:
                # 요청 추가
                self.requests.append(now)
                return 0.0
    
    async def try_acquire(self) -> bool:
        """요청 획득 시도 (대기 없음).
        
        Returns:
            획득 성공 여부
        """
        async with self.lock:
            now = time.time()
            
            # 윈도우 밖 요청 제거
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()
            
            # 요청 수 확인
            if len(self.requests) >= self.max_requests:
                return False
            else:
                self.requests.append(now)
                return True
    
    def limit(self, func: Callable[..., T]) -> Callable[..., T]:
        """Rate limiting 데코레이터 (비동기).
        
        Examples:
            >>> limiter = AsyncSlidingWindowRateLimiter(
            ...     max_requests=10,
            ...     window_seconds=60.0
            ... )
            >>> 
            >>> @limiter.limit
            >>> async def api_request(url):
            ...     async with aiohttp.ClientSession() as session:
            ...         return await session.get(url)
            >>> 
            >>> await api_request("https://example.com")
        """
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            await self.acquire()
            return await func(*args, **kwargs)
        return wrapper
