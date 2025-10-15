# -*- coding: utf-8 -*-
"""
image_utils.services.image_downloader
이미지 다운로드 전용 모듈 (동기 처리)

HTTP(S) URL에서 이미지를 다운로드하여 로컬에 저장합니다.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field


class ImageDownloadPolicy(BaseModel):
    """이미지 다운로드 정책
    
    Attributes:
        timeout: HTTP 요청 타임아웃 (초)
        max_retries: 실패 시 최대 재시도 횟수
        retry_delay: 재시도 간 지연 시간 (초)
        user_agent: User-Agent 헤더
        headers: 추가 HTTP 헤더
        verify_ssl: SSL 인증서 검증 여부
    """
    timeout: int = Field(30, description="HTTP request timeout (seconds)")
    max_retries: int = Field(3, description="Max retry count on failure")
    retry_delay: float = Field(1.0, description="Delay between retries (seconds)")
    user_agent: str = Field(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        description="User-Agent header"
    )
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional HTTP headers")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")


class ImageDownloader:
    """HTTP(S)에서 이미지를 다운로드하는 동기 클래스
    
    crawl_utils.HTTPFetcher는 async 전용이므로,
    xlcrawl2.py의 동기 환경을 위해 별도로 구현
    
    Examples:
        >>> policy = ImageDownloadPolicy(timeout=30)
        >>> downloader = ImageDownloader(policy)
        >>> 
        >>> # 단일 이미지 다운로드
        >>> path = downloader.download(
        ...     "https://example.com/image.jpg",
        ...     Path("output/image.jpg")
        ... )
        >>> 
        >>> # 여러 이미지 다운로드
        >>> urls = ["https://example.com/1.jpg", "https://example.com/2.jpg"]
        >>> paths = downloader.download_many(urls, Path("output"), prefix="product")
        >>> # output/product_0000.jpg, output/product_0001.jpg
    """
    
    def __init__(self, policy: ImageDownloadPolicy | dict):
        """ImageDownloader 초기화
        
        Args:
            policy: ImageDownloadPolicy 인스턴스 또는 설정 dict
        """
        if isinstance(policy, dict):
            policy = ImageDownloadPolicy(**policy)
        self.policy = policy
        
        # requests 세션 생성 (연결 재사용)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.policy.user_agent,
            **self.policy.headers
        })
    
    def download(self, url: str, save_path: Path) -> Path:
        """단일 이미지 다운로드
        
        Args:
            url: 이미지 URL (http:// 또는 https://)
            save_path: 저장 경로 (확장자 포함)
        
        Returns:
            Path: 저장된 파일 경로
        
        Raises:
            requests.HTTPError: HTTP 오류 (404, 500 등)
            requests.Timeout: 타임아웃
            OSError: 파일 저장 오류
        
        Examples:
            >>> downloader.download(
            ...     "https://example.com/product.jpg",
            ...     Path("output/images/product_001.jpg")
            ... )
            Path('output/images/product_001.jpg')
        """
        last_error = None
        
        for attempt in range(self.policy.max_retries):
            try:
                # HTTP GET 요청
                response = self.session.get(
                    url,
                    timeout=self.policy.timeout,
                    verify=self.policy.verify_ssl,
                    stream=True  # 대용량 이미지 처리
                )
                response.raise_for_status()
                
                # 디렉토리 생성
                save_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 바이트 저장
                save_path.write_bytes(response.content)
                
                return save_path
                
            except (requests.HTTPError, requests.Timeout, requests.ConnectionError) as e:
                last_error = e
                
                if attempt < self.policy.max_retries - 1:
                    # 재시도 전 대기
                    time.sleep(self.policy.retry_delay)
                    continue
                else:
                    # 최종 실패
                    raise
        
        # 여기 도달하면 안 됨
        if last_error:
            raise last_error
        
        return save_path
    
    def download_many(
        self,
        urls: List[str],
        save_dir: Path,
        prefix: str = "image",
        start_index: int = 0
    ) -> List[Dict[str, Any]]:
        """여러 이미지를 다운로드
        
        Args:
            urls: 이미지 URL 리스트
            save_dir: 저장 디렉토리
            prefix: 파일명 접두사 (기본값: "image")
            start_index: 시작 인덱스 (기본값: 0)
        
        Returns:
            List[Dict]: 다운로드 결과 리스트
                각 항목: {
                    "url": str,
                    "path": Path | None,
                    "status": "success" | "failed",
                    "error": str | None
                }
        
        Examples:
            >>> urls = [
            ...     "https://example.com/1.jpg",
            ...     "https://example.com/2.jpg",
            ...     "https://example.com/3.jpg"
            ... ]
            >>> results = downloader.download_many(
            ...     urls,
            ...     Path("output/images"),
            ...     prefix="product"
            ... )
            >>> # output/images/product_0000.jpg
            >>> # output/images/product_0001.jpg
            >>> # output/images/product_0002.jpg
            >>> 
            >>> len([r for r in results if r["status"] == "success"])
            3
        """
        results = []
        save_dir.mkdir(parents=True, exist_ok=True)
        
        for i, url in enumerate(urls):
            index = start_index + i
            
            # 확장자 추출 (URL에서 또는 기본값 .jpg)
            ext = self._extract_extension(url)
            filename = f"{prefix}_{index:04d}{ext}"
            save_path = save_dir / filename
            
            try:
                self.download(url, save_path)
                
                results.append({
                    "url": url,
                    "path": save_path,
                    "status": "success",
                    "error": None,
                    "index": index
                })
                
                print(f"  ✅ Downloaded [{index}]: {filename}")
                
            except Exception as e:
                results.append({
                    "url": url,
                    "path": None,
                    "status": "failed",
                    "error": str(e),
                    "index": index
                })
                
                print(f"  ❌ Failed [{index}]: {url} - {e}")
        
        return results
    
    def _extract_extension(self, url: str) -> str:
        """URL에서 파일 확장자 추출
        
        Args:
            url: 이미지 URL
        
        Returns:
            str: 확장자 (점 포함, 예: ".jpg")
        
        Examples:
            >>> downloader._extract_extension("https://example.com/image.jpg")
            '.jpg'
            >>> downloader._extract_extension("https://example.com/image.png?size=large")
            '.png'
            >>> downloader._extract_extension("https://example.com/no_ext")
            '.jpg'
        """
        parsed = urlparse(url)
        path = Path(parsed.path)
        ext = path.suffix.lower()
        
        # 유효한 이미지 확장자인지 확인
        valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}
        
        if ext in valid_extensions:
            return ext
        
        # 확장자가 없거나 유효하지 않으면 .jpg 기본값
        return ".jpg"
    
    def close(self) -> None:
        """requests 세션 종료"""
        if self.session:
            self.session.close()
    
    def __enter__(self) -> "ImageDownloader":
        """Context manager 진입"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager 종료"""
        self.close()


# Convenience function
def download_images(
    urls: List[str],
    save_dir: Path | str,
    *,
    prefix: str = "image",
    timeout: int = 30,
    max_retries: int = 3
) -> List[Path]:
    """이미지 다운로드 편의 함수
    
    Args:
        urls: 이미지 URL 리스트
        save_dir: 저장 디렉토리
        prefix: 파일명 접두사
        timeout: 타임아웃 (초)
        max_retries: 최대 재시도 횟수
    
    Returns:
        List[Path]: 성공적으로 다운로드된 파일 경로 리스트
    
    Examples:
        >>> urls = ["https://example.com/1.jpg", "https://example.com/2.jpg"]
        >>> paths = download_images(urls, "output/images", prefix="product")
        >>> len(paths)
        2
    """
    policy = ImageDownloadPolicy(timeout=timeout, max_retries=max_retries)
    
    with ImageDownloader(policy) as downloader:
        results = downloader.download_many(urls, Path(save_dir), prefix=prefix)
        
        # 성공한 경로만 반환
        return [r["path"] for r in results if r["status"] == "success"]
