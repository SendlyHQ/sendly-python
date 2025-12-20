"""
HTTP Client Utility

Handles HTTP requests to the Sendly API with retries and rate limiting.
"""

import asyncio
import random
import re
import time
from typing import Any, Dict, Optional, TypeVar, Union

import httpx

from ..errors import (
    NetworkError,
    RateLimitError,
    SendlyError,
    TimeoutError,
)
from ..types import RateLimitInfo

T = TypeVar("T")

DEFAULT_BASE_URL = "https://sendly.live/api/v1"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
SDK_VERSION = "1.0.5"


class HttpClient:
    """Synchronous HTTP client for making API requests"""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._rate_limit_info: Optional[RateLimitInfo] = None
        self._client: Optional[httpx.Client] = None

        # Validate API key format
        if not self._is_valid_api_key(api_key):
            raise ValueError("Invalid API key format. Expected sk_test_v1_xxx or sk_live_v1_xxx")

    def _is_valid_api_key(self, key: str) -> bool:
        """Validate API key format"""
        return bool(re.match(r"^sk_(test|live)_v1_[a-zA-Z0-9_-]+$", key))

    def is_test_mode(self) -> bool:
        """Check if using a test API key"""
        return self.api_key.startswith("sk_test_")

    def get_rate_limit_info(self) -> Optional[RateLimitInfo]:
        """Get current rate limit info"""
        return self._rate_limit_info

    @property
    def client(self) -> httpx.Client:
        """Get or create the HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._build_headers(),
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client"""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"sendly-python/{SDK_VERSION}",
        }

    def _update_rate_limit_info(self, headers: httpx.Headers) -> None:
        """Update rate limit info from response headers"""
        limit = headers.get("X-RateLimit-Limit")
        remaining = headers.get("X-RateLimit-Remaining")
        reset = headers.get("X-RateLimit-Reset")

        if limit and remaining and reset:
            self._rate_limit_info = RateLimitInfo(
                limit=int(limit),
                remaining=int(remaining),
                reset=int(reset),
            )

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff time"""
        base_delay = 2**attempt
        jitter = random.uniform(0, 0.5)
        return min(base_delay + jitter, 30.0)

    def request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an HTTP request to the API"""
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.request(
                    method=method,
                    url=path,
                    json=body,
                    params=params,
                )

                # Update rate limit info
                self._update_rate_limit_info(response.headers)

                # Parse response
                data = self._parse_response(response)
                return data

            except SendlyError as e:
                last_error = e

                # Don't retry certain errors
                if e.status_code in (400, 401, 402, 403, 404):
                    raise

                # Handle rate limiting
                if isinstance(e, RateLimitError):
                    if attempt < self.max_retries:
                        time.sleep(e.retry_after)
                        continue
                    raise

            except httpx.TimeoutException as e:
                last_error = TimeoutError(f"Request timed out after {self.timeout}s")
                if attempt < self.max_retries:
                    time.sleep(self._calculate_backoff(attempt))
                    continue

            except httpx.RequestError as e:
                last_error = NetworkError(f"Network error: {str(e)}", e)
                if attempt < self.max_retries:
                    time.sleep(self._calculate_backoff(attempt))
                    continue

        if last_error:
            raise last_error
        raise NetworkError("Request failed after retries")

    def _parse_response(self, response: httpx.Response) -> Any:
        """Parse the response body"""
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            try:
                data = response.json()
            except Exception:
                data = response.text
        else:
            data = response.text

        # Handle error responses
        if not response.is_success:
            if isinstance(data, dict):
                raise SendlyError.from_response(response.status_code, data)
            raise SendlyError(
                message=str(data) or f"HTTP {response.status_code}",
                code="internal_error",
                status_code=response.status_code,
            )

        return data


class AsyncHttpClient:
    """Asynchronous HTTP client for making API requests"""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._rate_limit_info: Optional[RateLimitInfo] = None
        self._client: Optional[httpx.AsyncClient] = None

        # Validate API key format
        if not self._is_valid_api_key(api_key):
            raise ValueError("Invalid API key format. Expected sk_test_v1_xxx or sk_live_v1_xxx")

    def _is_valid_api_key(self, key: str) -> bool:
        """Validate API key format"""
        return bool(re.match(r"^sk_(test|live)_v1_[a-zA-Z0-9_-]+$", key))

    def is_test_mode(self) -> bool:
        """Check if using a test API key"""
        return self.api_key.startswith("sk_test_")

    def get_rate_limit_info(self) -> Optional[RateLimitInfo]:
        """Get current rate limit info"""
        return self._rate_limit_info

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._build_headers(),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "AsyncHttpClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"sendly-python/{SDK_VERSION}",
        }

    def _update_rate_limit_info(self, headers: httpx.Headers) -> None:
        """Update rate limit info from response headers"""
        limit = headers.get("X-RateLimit-Limit")
        remaining = headers.get("X-RateLimit-Remaining")
        reset = headers.get("X-RateLimit-Reset")

        if limit and remaining and reset:
            self._rate_limit_info = RateLimitInfo(
                limit=int(limit),
                remaining=int(remaining),
                reset=int(reset),
            )

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff time"""
        base_delay = 2**attempt
        jitter = random.uniform(0, 0.5)
        return min(base_delay + jitter, 30.0)

    async def request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an async HTTP request to the API"""
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.request(
                    method=method,
                    url=path,
                    json=body,
                    params=params,
                )

                # Update rate limit info
                self._update_rate_limit_info(response.headers)

                # Parse response
                data = self._parse_response(response)
                return data

            except SendlyError as e:
                last_error = e

                # Don't retry certain errors
                if e.status_code in (400, 401, 402, 403, 404):
                    raise

                # Handle rate limiting
                if isinstance(e, RateLimitError):
                    if attempt < self.max_retries:
                        await asyncio.sleep(e.retry_after)
                        continue
                    raise

            except httpx.TimeoutException as e:
                last_error = TimeoutError(f"Request timed out after {self.timeout}s")
                if attempt < self.max_retries:
                    await asyncio.sleep(self._calculate_backoff(attempt))
                    continue

            except httpx.RequestError as e:
                last_error = NetworkError(f"Network error: {str(e)}", e)
                if attempt < self.max_retries:
                    await asyncio.sleep(self._calculate_backoff(attempt))
                    continue

        if last_error:
            raise last_error
        raise NetworkError("Request failed after retries")

    def _parse_response(self, response: httpx.Response) -> Any:
        """Parse the response body"""
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            try:
                data = response.json()
            except Exception:
                data = response.text
        else:
            data = response.text

        # Handle error responses
        if not response.is_success:
            if isinstance(data, dict):
                raise SendlyError.from_response(response.status_code, data)
            raise SendlyError(
                message=str(data) or f"HTTP {response.status_code}",
                code="internal_error",
                status_code=response.status_code,
            )

        return data
