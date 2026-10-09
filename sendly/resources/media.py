"""
Media Resource

API resource for uploading media files for MMS.
"""

import os
from typing import Any, BinaryIO, Dict, Optional, Tuple

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError
from ..types import MediaFile
from ..utils.http import AsyncHttpClient, HttpClient
from .business_upgrade import _multipart_request_async, _multipart_request_sync


def _file_part(file: BinaryIO, content_type: str) -> Dict[str, Tuple[str, bytes, str]]:
    filename = os.path.basename(str(getattr(file, "name", "") or "")) or "upload"
    return {"file": (filename, file.read(), content_type)}


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
            ValidationError: If no file reached the API (code ``invalid_request``)
            SendlyError: With code ``invalid_file`` when content_type is
                image/jpeg, image/png or image/gif but the content is not a
                JPEG, PNG or GIF; ``unsupported_media_type`` (HTTP 415) when
                content_type is any other type, with the reason in the
                message; ``file_too_large`` (HTTP 413) when the file is over
                600 KB; or ``feature_disabled`` when MMS is not enabled for
                your account
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
        data = _multipart_request_sync(self._http, "/media", {}, _file_part(file, content_type))

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

        Raises:
            SendlyError: The errors :meth:`MediaResource.upload` lists

        Example:
            >>> with open('photo.jpg', 'rb') as f:
            ...     media = await client.media.upload(f, content_type='image/jpeg')
            >>> message = await client.messages.send(
            ...     to='+15551234567',
            ...     text='Check this out!',
            ...     media_urls=[media.url]
            ... )
        """
        data = await _multipart_request_async(
            self._http, "/media", {}, _file_part(file, content_type)
        )

        try:
            return MediaFile(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e
