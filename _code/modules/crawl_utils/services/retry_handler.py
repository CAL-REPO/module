# -*- coding: utf-8 -*-
"""RetryHandler - Policy 기반 재시도 메커니즘

RetryPolicy를 사용하여 동기/비동기 재시도를 처리합니다.
"""

import time
import asyncio
from typing import TypeVar, Callable, Any, Optional, Awaitable
from functools import wraps

from crawl_utils.core.policy import RetryPolicy

T = TypeVar('T')


class SyncRetryHandler:
    """동기 재시도 핸들러 (RetryPolicy 기반)
    
    RetryPolicy를 사용하여 지수 백오프 전략으로 함수를 재시도합니다.
    
    Attributes:
        policy: RetryPolicy 인스턴스
        logger: loguru Logger (선택사항)
    
    Examples:
        >>> from crawl_utils.core.policy import RetryPolicy
        >>> 
        >>> policy = RetryPolicy(retries=3, backoff_sec=1.0)
        >>> handler = SyncRetryHandler(policy)
        >>> 
        >>> def unstable_operation():
        ...     if random.random() < 0.5:
        ...         raise ConnectionError("Network error")
        ...     return "Success"
        >>> 
        >>> result = handler.execute(unstable_operation)
    """
    
    def __init__(
        self,
        policy: RetryPolicy,
        logger: Optional[Any] = None
    ):
        """Initialize sync retry handler.
        
        Args:
            policy: RetryPolicy 인스턴스
            logger: loguru Logger (선택사항)
        """
        self.policy = policy
        self.logger = logger
    
    def execute(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """함수 실행 (재시도 포함).
        
        Args:
            func: 실행할 함수
            *args: 함수 위치 인자
            **kwargs: 함수 키워드 인자
        
        Returns:
            함수 실행 결과
        
        Raises:
            마지막 시도에서 발생한 예외
        """
        last_exception: Optional[Exception] = None
        
        for attempt in range(self.policy.retries + 1):
            try:
                return func(*args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                if attempt < self.policy.retries:
                    # 지수 백오프 계산
                    wait_time = self.policy.backoff_sec * (2 ** attempt)
                    
                    if self.logger:
                        self.logger.warning(
                            f"[Retry {attempt + 1}/{self.policy.retries}] "
                            f"{func.__name__} failed: {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                    
                    time.sleep(wait_time)
                else:
                    if self.logger:
                        self.logger.error(
                            f"[Retry Failed] {func.__name__} failed after "
                            f"{self.policy.retries} retries: {e}"
                        )
        
        # 모든 재시도 실패 시 마지막 예외 raise
        if last_exception:
            raise last_exception
        else:
            # 이론적으로 도달 불가
            raise RuntimeError(f"Unexpected retry failure for {func.__name__}")
    
    def wrap(self, func: Callable[..., T]) -> Callable[..., T]:
        """재시도 데코레이터.
        
        Examples:
            >>> handler = SyncRetryHandler(RetryPolicy(retries=3))
            >>> 
            >>> @handler.wrap
            >>> def api_request(url):
            ...     return requests.get(url)
            >>> 
            >>> api_request("https://example.com")
        """
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self.execute(func, *args, **kwargs)
        return wrapper


class AsyncRetryHandler:
    """비동기 재시도 핸들러 (RetryPolicy 기반)
    
    RetryPolicy를 사용하여 지수 백오프 전략으로 async 함수를 재시도합니다.
    
    Attributes:
        policy: RetryPolicy 인스턴스
        logger: loguru Logger (선택사항)
    
    Examples:
        >>> from crawl_utils.core.policy import RetryPolicy
        >>> 
        >>> policy = RetryPolicy(retries=3, backoff_sec=1.0)
        >>> handler = AsyncRetryHandler(policy)
        >>> 
        >>> async def async_unstable():
        ...     if random.random() < 0.5:
        ...         raise aiohttp.ClientError("Network error")
        ...     return "Success"
        >>> 
        >>> result = await handler.execute(async_unstable)
    """
    
    def __init__(
        self,
        policy: RetryPolicy,
        logger: Optional[Any] = None
    ):
        """Initialize async retry handler.
        
        Args:
            policy: RetryPolicy 인스턴스
            logger: loguru Logger (선택사항)
        """
        self.policy = policy
        self.logger = logger
    
    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """async 함수 실행 (재시도 포함).
        
        Args:
            func: 실행할 async 함수
            *args: 함수 위치 인자
            **kwargs: 함수 키워드 인자
        
        Returns:
            함수 실행 결과
        
        Raises:
            마지막 시도에서 발생한 예외
        """
        last_exception: Optional[Exception] = None
        
        for attempt in range(self.policy.retries + 1):
            try:
                return await func(*args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                if attempt < self.policy.retries:
                    # 지수 백오프 계산
                    wait_time = self.policy.backoff_sec * (2 ** attempt)
                    
                    if self.logger:
                        self.logger.warning(
                            f"[Retry {attempt + 1}/{self.policy.retries}] "
                            f"{func.__name__} failed: {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                    
                    await asyncio.sleep(wait_time)
                else:
                    if self.logger:
                        self.logger.error(
                            f"[Retry Failed] {func.__name__} failed after "
                            f"{self.policy.retries} retries: {e}"
                        )
        
        # 모든 재시도 실패 시 마지막 예외 raise
        if last_exception:
            raise last_exception
        else:
            # 이론적으로 도달 불가
            raise RuntimeError(f"Unexpected retry failure for {func.__name__}")
    
    def wrap(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """재시도 데코레이터 (비동기).
        
        Examples:
            >>> handler = AsyncRetryHandler(RetryPolicy(retries=3))
            >>> 
            >>> @handler.wrap
            >>> async def api_request(url):
            ...     async with aiohttp.ClientSession() as session:
            ...         return await session.get(url)
            >>> 
            >>> await api_request("https://example.com")
        """
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await self.execute(func, *args, **kwargs)
        return wrapper  # type: ignore


__all__ = ["SyncRetryHandler", "AsyncRetryHandler"]
