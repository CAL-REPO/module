"""
재시도 유틸리티 모듈.

지수 백오프(Exponential Backoff) 기반의 재시도 메커니즘을 제공합니다.

Features:
- 동기 함수 재시도 (retry_sync)
- 비동기 함수 재시도 (retry_async)
- 지수 백오프 전략
- 재시도 가능 예외 필터링
- 최대 재시도 횟수 제한

Examples:
    >>> from selenium.common.exceptions import TimeoutException, WebDriverException
    >>> 
    >>> # 동기 함수 재시도
    >>> def unstable_operation():
    ...     if random.random() < 0.5:
    ...         raise TimeoutException("Timeout!")
    ...     return "Success"
    >>> 
    >>> result = retry_sync(
    ...     unstable_operation,
    ...     max_retries=3,
    ...     backoff_factor=1.0,
    ...     retryable_exceptions=(TimeoutException, WebDriverException)
    ... )
    >>> 
    >>> # 비동기 함수 재시도
    >>> async def async_unstable():
    ...     if random.random() < 0.5:
    ...         raise TimeoutException("Timeout!")
    ...     return "Success"
    >>> 
    >>> result = await retry_async(
    ...     async_unstable,
    ...     max_retries=3,
    ...     backoff_factor=1.0
    ... )
"""

import time
import asyncio
from typing import TypeVar, Callable, Tuple, Type, Any, Optional
from functools import wraps

T = TypeVar('T')


def retry_sync(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[Any] = None,
    **kwargs: Any
) -> T:
    """동기 함수 재시도 유틸리티.
    
    지수 백오프 전략으로 함수를 재시도합니다.
    대기 시간 = backoff_factor * (2 ** attempt)
    
    Args:
        func: 재시도할 함수
        *args: 함수 위치 인자
        max_retries: 최대 재시도 횟수 (기본값: 3)
        backoff_factor: 백오프 계수 (기본값: 1.0초)
        retryable_exceptions: 재시도 가능한 예외 튜플 (기본값: 모든 예외)
        logger: loguru Logger (선택사항)
        **kwargs: 함수 키워드 인자
    
    Returns:
        함수 실행 결과
    
    Raises:
        마지막 시도에서 발생한 예외
    
    Examples:
        >>> def flaky_request(url: str):
        ...     if random.random() < 0.5:
        ...         raise ConnectionError("Network error")
        ...     return requests.get(url)
        >>> 
        >>> response = retry_sync(
        ...     flaky_request,
        ...     "https://example.com",
        ...     max_retries=3,
        ...     backoff_factor=1.0,
        ...     retryable_exceptions=(ConnectionError, TimeoutError)
        ... )
    """
    last_exception: Optional[Exception] = None
    
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        
        except retryable_exceptions as e:
            last_exception = e
            
            if attempt < max_retries:
                # 지수 백오프 계산
                wait_time = backoff_factor * (2 ** attempt)
                
                if logger:
                    logger.warning(
                        f"[Retry {attempt + 1}/{max_retries}] "
                        f"{func.__name__} failed: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                
                time.sleep(wait_time)
            else:
                if logger:
                    logger.error(
                        f"[Retry Failed] {func.__name__} failed after {max_retries} retries: {e}"
                    )
    
    # 모든 재시도 실패 시 마지막 예외 raise
    if last_exception:
        raise last_exception
    else:
        # 이론적으로 도달 불가
        raise RuntimeError(f"Unexpected retry failure for {func.__name__}")


async def retry_async(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[Any] = None,
    **kwargs: Any
) -> T:
    """비동기 함수 재시도 유틸리티.
    
    지수 백오프 전략으로 async 함수를 재시도합니다.
    대기 시간 = backoff_factor * (2 ** attempt)
    
    Args:
        func: 재시도할 async 함수
        *args: 함수 위치 인자
        max_retries: 최대 재시도 횟수 (기본값: 3)
        backoff_factor: 백오프 계수 (기본값: 1.0초)
        retryable_exceptions: 재시도 가능한 예외 튜플 (기본값: 모든 예외)
        logger: loguru Logger (선택사항)
        **kwargs: 함수 키워드 인자
    
    Returns:
        함수 실행 결과
    
    Raises:
        마지막 시도에서 발생한 예외
    
    Examples:
        >>> async def async_flaky_request(url: str):
        ...     if random.random() < 0.5:
        ...         raise aiohttp.ClientError("Network error")
        ...     async with aiohttp.ClientSession() as session:
        ...         return await session.get(url)
        >>> 
        >>> response = await retry_async(
        ...     async_flaky_request,
        ...     "https://example.com",
        ...     max_retries=3,
        ...     backoff_factor=1.0,
        ...     retryable_exceptions=(aiohttp.ClientError,)
        ... )
    """
    last_exception: Optional[Exception] = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        
        except retryable_exceptions as e:
            last_exception = e
            
            if attempt < max_retries:
                # 지수 백오프 계산
                wait_time = backoff_factor * (2 ** attempt)
                
                if logger:
                    logger.warning(
                        f"[Retry {attempt + 1}/{max_retries}] "
                        f"{func.__name__} failed: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                
                await asyncio.sleep(wait_time)
            else:
                if logger:
                    logger.error(
                        f"[Retry Failed] {func.__name__} failed after {max_retries} retries: {e}"
                    )
    
    # 모든 재시도 실패 시 마지막 예외 raise
    if last_exception:
        raise last_exception
    else:
        # 이론적으로 도달 불가
        raise RuntimeError(f"Unexpected retry failure for {func.__name__}")


def with_retry(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[Any] = None
):
    """재시도 데코레이터 (동기 함수용).
    
    Examples:
        >>> from selenium.common.exceptions import TimeoutException
        >>> 
        >>> @with_retry(
        ...     max_retries=3,
        ...     backoff_factor=1.0,
        ...     retryable_exceptions=(TimeoutException,)
        ... )
        ... def load_page(url: str):
        ...     driver.get(url)
        ...     return driver.page_source
        >>> 
        >>> html = load_page("https://example.com")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return retry_sync(
                func,
                *args,
                max_retries=max_retries,
                backoff_factor=backoff_factor,
                retryable_exceptions=retryable_exceptions,
                logger=logger,
                **kwargs
            )
        return wrapper
    return decorator


def with_retry_async(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[Any] = None
):
    """재시도 데코레이터 (비동기 함수용).
    
    Examples:
        >>> import aiohttp
        >>> 
        >>> @with_retry_async(
        ...     max_retries=3,
        ...     backoff_factor=1.0,
        ...     retryable_exceptions=(aiohttp.ClientError,)
        ... )
        ... async def fetch_data(url: str):
        ...     async with aiohttp.ClientSession() as session:
        ...         async with session.get(url) as resp:
        ...             return await resp.json()
        >>> 
        >>> data = await fetch_data("https://api.example.com/data")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_async(
                func,
                *args,
                max_retries=max_retries,
                backoff_factor=backoff_factor,
                retryable_exceptions=retryable_exceptions,
                logger=logger,
                **kwargs
            )
        return wrapper
    return decorator
