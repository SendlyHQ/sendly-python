"""
Links Resource - URL shortening / branded links

Create short links, list them with click analytics, and disable (kill) a link.

These endpoints hang off the versioned ``/api/v1`` base and authenticate with
the API key, like every other resource. URL shortening is gated behind the
``url_shortener`` rollout flag; while the flag is off for your account the calls
read as ``not_found`` (404) — the feature is simply absent, not an error you
need to handle specially.
"""

from typing import Any, Dict, Optional
from urllib.parse import quote

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError
from ..types import (
    CreateShortLinkResponse,
    ShortLinkListResponse,
    UpdateShortLinkResponse,
)
from ..utils.http import AsyncHttpClient, HttpClient


def _validate_url(url: str) -> None:
    """Client-side guard mirroring the server's http/https-only check."""
    if not url or not isinstance(url, str):
        raise SendlyError(
            message="url is required", code="invalid_url", status_code=400
        )
    if not (url.startswith("http://") or url.startswith("https://")):
        raise SendlyError(
            message="url must be an http:// or https:// URL",
            code="invalid_url",
            status_code=400,
        )


class LinksResource:
    """URL shortener API resource (sync)

    Example:
        >>> link = client.links.create('https://example.com/very/long/path')
        >>> print(link.short_url)
        >>> listing = client.links.list(limit=20)
        >>> client.links.disable(link.code)
    """

    def __init__(self, http: HttpClient):
        self._http = http

    def create(self, url: str) -> CreateShortLinkResponse:
        """Create a short link for an http/https URL."""
        _validate_url(url)
        data = self._http.request(
            method="POST",
            path="/links",
            body={"url": url},
        )
        try:
            return CreateShortLinkResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def list(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> ShortLinkListResponse:
        """List short links with click analytics.

        Args:
            limit: Maximum number of links to return (default 50, max 200).
            offset: Number of links to skip (default 0).
        """
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        data = self._http.request(
            method="GET",
            path="/links",
            params=params if params else None,
        )
        try:
            return ShortLinkListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def update(self, code: str, disabled: bool) -> UpdateShortLinkResponse:
        """Enable or disable a short link (kill switch)."""
        data = self._http.request(
            method="PATCH",
            path=f"/links/{quote(code, safe='')}",
            body={"disabled": disabled},
        )
        try:
            return UpdateShortLinkResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def disable(self, code: str) -> UpdateShortLinkResponse:
        """Disable a short link (convenience for ``update(code, True)``)."""
        return self.update(code, True)

    def enable(self, code: str) -> UpdateShortLinkResponse:
        """Re-enable a disabled short link (convenience for ``update(code, False)``)."""
        return self.update(code, False)


class AsyncLinksResource:
    """URL shortener API resource (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def create(self, url: str) -> CreateShortLinkResponse:
        """Create a short link for an http/https URL."""
        _validate_url(url)
        data = await self._http.request(
            method="POST",
            path="/links",
            body={"url": url},
        )
        try:
            return CreateShortLinkResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def list(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> ShortLinkListResponse:
        """List short links with click analytics."""
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        data = await self._http.request(
            method="GET",
            path="/links",
            params=params if params else None,
        )
        try:
            return ShortLinkListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def update(self, code: str, disabled: bool) -> UpdateShortLinkResponse:
        """Enable or disable a short link (kill switch)."""
        data = await self._http.request(
            method="PATCH",
            path=f"/links/{quote(code, safe='')}",
            body={"disabled": disabled},
        )
        try:
            return UpdateShortLinkResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def disable(self, code: str) -> UpdateShortLinkResponse:
        """Disable a short link (convenience for ``update(code, True)``)."""
        return await self.update(code, True)

    async def enable(self, code: str) -> UpdateShortLinkResponse:
        """Re-enable a disabled short link (convenience for ``update(code, False)``)."""
        return await self.update(code, False)


def _invalid_response(e: PydanticValidationError) -> SendlyError:
    """Wrap a pydantic schema error as a SendlyError, matching the SDK's idiom."""
    return SendlyError(
        message=f"Invalid API response format: {e}",
        code="invalid_response",
        status_code=200,
    )
