"""
Media Resource

API resource for uploading media files for MMS.
"""

from typing import Any, BinaryIO, Optional

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError
from ..types import MediaFile
from ..utils.http import AsyncHttpClient, HttpClient


class MediaResource:
    """
    Media API resource (synchronous)

    Example:
        >>> client = Sendly('sk_live_v1_xxx')
        >>> with open('image.jpg', 'rb') as f:
        ...     media = client.media.upload(f, content_type='image/jpeg')
        >>> print(media.url)
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def upload(self, file: BinaryIO, content_type: str = "image/jpeg") -> MediaFile:
        """
        Upload a media file for use in MMS messages

        Args:
            file: File-like object to upload
            content_type: MIME type of the file (default: image/jpeg)

        Returns:
            The uploaded media file details

        Raises:
            ValidationError: If the file is invalid
            AuthenticationError: If the API key is invalid
            RateLimitError: If rate limit is exceeded

        Example:
            >>> with open('photo.jpg', 'rb') as f:
            ...     media = client.media.upload(f, content_type='image/jpeg')
            >>> message = client.messages.send(
            ...     to='+15551234567',
            ...     text='Check this out!',
            ...     media_urls=[media.url]
            ... )
        """
        filename = getattr(file, "name", "upload")
        response = self._http.client.post(
            "/media",
            files={"file": (filename, file, content_type)},
            headers={
                "Authorization": f"Bearer {self._http.api_key}",
                "Accept": "application/json",
                "User-Agent": self._http.client.headers.get("User-Agent", ""),
            },
        )

        self._http._update_rate_limit_info(response.headers)
        data = self._http._parse_response(response)

        try:
            return MediaFile(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e


class AsyncMediaResource:
    """
    Media API resource (asynchronous)

    Example:
        >>> async with AsyncSendly('sk_live_v1_xxx') as client:
        ...     with open('image.jpg', 'rb') as f:
        ...         media = await client.media.upload(f, content_type='image/jpeg')
        ...     print(media.url)
    """

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def upload(self, file: BinaryIO, content_type: str = "image/jpeg") -> MediaFile:
        """
        Upload a media file for use in MMS messages (async)

        Args:
            file: File-like object to upload
            content_type: MIME type of the file (default: image/jpeg)

        Returns:
            The uploaded media file details

        Example:
            >>> with open('photo.jpg', 'rb') as f:
            ...     media = await client.media.upload(f, content_type='image/jpeg')
            >>> message = await client.messages.send(
            ...     to='+15551234567',
            ...     text='Check this out!',
            ...     media_urls=[media.url]
            ... )
        """
        filename = getattr(file, "name", "upload")
        response = await self._http.client.post(
            "/media",
            files={"file": (filename, file, content_type)},
            headers={
                "Authorization": f"Bearer {self._http.api_key}",
                "Accept": "application/json",
                "User-Agent": self._http.client.headers.get("User-Agent", ""),
            },
        )

        self._http._update_rate_limit_info(response.headers)
        data = self._http._parse_response(response)

        try:
            return MediaFile(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e
