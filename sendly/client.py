"""
Sendly Client

Main entry point for the Sendly SDK.
"""

from typing import Any, Optional, Union

from .resources.account import AccountResource, AsyncAccountResource
from .resources.messages import AsyncMessagesResource, MessagesResource
from .resources.webhooks import AsyncWebhooksResource, WebhooksResource
from .types import RateLimitInfo, SendlyConfig
from .utils.http import AsyncHttpClient, HttpClient

DEFAULT_BASE_URL = "https://sendly.live/api/v1"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3


class Sendly:
    """
    Sendly API Client (synchronous)

    The main entry point for interacting with the Sendly SMS API.

    Example:
        >>> from sendly import Sendly
        >>>
        >>> # Initialize with API key
        >>> client = Sendly('sk_live_v1_your_api_key')
        >>>
        >>> # Send an SMS
        >>> message = client.messages.send(
        ...     to='+15551234567',
        ...     text='Hello from Sendly!'
        ... )
        >>> print(message.id)

    Example with configuration:
        >>> client = Sendly(
        ...     api_key='sk_live_v1_your_api_key',
        ...     timeout=60.0,
        ...     max_retries=5
        ... )

    Example with context manager:
        >>> with Sendly('sk_live_v1_xxx') as client:
        ...     message = client.messages.send(to='+1555...', text='Hello!')
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        config: Optional[SendlyConfig] = None,
    ):
        """
        Create a new Sendly client

        Args:
            api_key: Your Sendly API key (sk_test_v1_xxx or sk_live_v1_xxx)
            base_url: Base URL for the API (default: https://sendly.live/api/v1)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts (default: 3)
            config: Alternative configuration object
        """
        # Handle configuration
        if config is not None:
            api_key = config.api_key
            base_url = config.base_url
            timeout = config.timeout
            max_retries = config.max_retries
        elif api_key is None:
            raise ValueError("api_key is required")

        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries

        # Initialize HTTP client
        self._http = HttpClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

        # Initialize resources
        self.messages = MessagesResource(self._http)
        self.webhooks = WebhooksResource(self._http)
        self.account = AccountResource(self._http)

    def __enter__(self) -> "Sendly":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the HTTP client and release resources"""
        self._http.close()

    def is_test_mode(self) -> bool:
        """
        Check if the client is using a test API key

        Returns:
            True if using a test key (sk_test_v1_xxx)

        Example:
            >>> if client.is_test_mode():
            ...     print('Running in test mode')
        """
        return self._http.is_test_mode()

    def get_rate_limit_info(self) -> Optional[RateLimitInfo]:
        """
        Get current rate limit information

        Returns the rate limit info from the most recent API request.

        Returns:
            Rate limit info or None if no requests have been made

        Example:
            >>> client.messages.send(to='+1555...', text='Hello!')
            >>> rate_limit = client.get_rate_limit_info()
            >>> if rate_limit:
            ...     print(f'{rate_limit.remaining}/{rate_limit.limit} remaining')
        """
        return self._http.get_rate_limit_info()

    @property
    def base_url(self) -> str:
        """Get the configured base URL"""
        return self._base_url


class AsyncSendly:
    """
    Sendly API Client (asynchronous)

    Async version of the Sendly client for use with asyncio.

    Example:
        >>> import asyncio
        >>> from sendly import AsyncSendly
        >>>
        >>> async def main():
        ...     async with AsyncSendly('sk_live_v1_xxx') as client:
        ...         message = await client.messages.send(
        ...             to='+15551234567',
        ...             text='Hello from Sendly!'
        ...         )
        ...         print(message.id)
        >>>
        >>> asyncio.run(main())

    Example without context manager:
        >>> client = AsyncSendly('sk_live_v1_xxx')
        >>> try:
        ...     message = await client.messages.send(to='+1555...', text='Hello!')
        ... finally:
        ...     await client.close()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        config: Optional[SendlyConfig] = None,
    ):
        """
        Create a new async Sendly client

        Args:
            api_key: Your Sendly API key (sk_test_v1_xxx or sk_live_v1_xxx)
            base_url: Base URL for the API (default: https://sendly.live/api/v1)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum retry attempts (default: 3)
            config: Alternative configuration object
        """
        # Handle configuration
        if config is not None:
            api_key = config.api_key
            base_url = config.base_url
            timeout = config.timeout
            max_retries = config.max_retries
        elif api_key is None:
            raise ValueError("api_key is required")

        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries

        # Initialize HTTP client
        self._http = AsyncHttpClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

        # Initialize resources
        self.messages = AsyncMessagesResource(self._http)
        self.webhooks = AsyncWebhooksResource(self._http)
        self.account = AsyncAccountResource(self._http)

    async def __aenter__(self) -> "AsyncSendly":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client and release resources"""
        await self._http.close()

    def is_test_mode(self) -> bool:
        """
        Check if the client is using a test API key

        Returns:
            True if using a test key (sk_test_v1_xxx)
        """
        return self._http.is_test_mode()

    def get_rate_limit_info(self) -> Optional[RateLimitInfo]:
        """
        Get current rate limit information

        Returns:
            Rate limit info or None if no requests have been made
        """
        return self._http.get_rate_limit_info()

    @property
    def base_url(self) -> str:
        """Get the configured base URL"""
        return self._base_url
