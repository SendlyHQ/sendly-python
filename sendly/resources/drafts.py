from typing import Any, Dict, List, Optional
from urllib.parse import quote

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError
from ..types import (
    DraftListResponse,
    MessageDraft,
)
from ..utils.http import AsyncHttpClient, HttpClient


class DraftsResource:
    def __init__(self, http: HttpClient):
        self._http = http

    def create(
        self,
        conversation_id: str,
        text: str,
        media_urls: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> MessageDraft:
        body: Dict[str, Any] = {
            "conversationId": conversation_id,
            "text": text,
        }
        if media_urls is not None:
            body["mediaUrls"] = media_urls
        if metadata is not None:
            body["metadata"] = metadata
        if source is not None:
            body["source"] = source

        data = self._http.request(
            method="POST",
            path="/drafts",
            body=body,
        )

        try:
            return MessageDraft(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def list(
        self,
        conversation_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> DraftListResponse:
        params: Dict[str, Any] = {}
        if conversation_id is not None:
            params["conversation_id"] = conversation_id
        if status is not None:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        data = self._http.request(
            method="GET",
            path="/drafts",
            params=params if params else None,
        )

        try:
            return DraftListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def get(self, id: str) -> MessageDraft:
        data = self._http.request(
            method="GET",
            path=f"/drafts/{quote(id, safe='')}",
        )

        try:
            return MessageDraft(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def update(
        self,
        id: str,
        text: Optional[str] = None,
        media_urls: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MessageDraft:
        body: Dict[str, Any] = {}
        if text is not None:
            body["text"] = text
        if media_urls is not None:
            body["mediaUrls"] = media_urls
        if metadata is not None:
            body["metadata"] = metadata

        data = self._http.request(
            method="PATCH",
            path=f"/drafts/{quote(id, safe='')}",
            body=body,
        )

        try:
            return MessageDraft(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def approve(self, id: str) -> MessageDraft:
        data = self._http.request(
            method="POST",
            path=f"/drafts/{quote(id, safe='')}/approve",
        )

        try:
            return MessageDraft(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def reject(self, id: str, reason: Optional[str] = None) -> MessageDraft:
        body: Dict[str, Any] = {}
        if reason is not None:
            body["reason"] = reason

        data = self._http.request(
            method="POST",
            path=f"/drafts/{quote(id, safe='')}/reject",
            body=body if body else None,
        )

        try:
            return MessageDraft(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e


class AsyncDraftsResource:
    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def create(
        self,
        conversation_id: str,
        text: str,
        media_urls: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> MessageDraft:
        body: Dict[str, Any] = {
            "conversationId": conversation_id,
            "text": text,
        }
        if media_urls is not None:
            body["mediaUrls"] = media_urls
        if metadata is not None:
            body["metadata"] = metadata
        if source is not None:
            body["source"] = source

        data = await self._http.request(
            method="POST",
            path="/drafts",
            body=body,
        )

        try:
            return MessageDraft(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def list(
        self,
        conversation_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> DraftListResponse:
        params: Dict[str, Any] = {}
        if conversation_id is not None:
            params["conversation_id"] = conversation_id
        if status is not None:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        data = await self._http.request(
            method="GET",
            path="/drafts",
            params=params if params else None,
        )

        try:
            return DraftListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def get(self, id: str) -> MessageDraft:
        data = await self._http.request(
            method="GET",
            path=f"/drafts/{quote(id, safe='')}",
        )

        try:
            return MessageDraft(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def update(
        self,
        id: str,
        text: Optional[str] = None,
        media_urls: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MessageDraft:
        body: Dict[str, Any] = {}
        if text is not None:
            body["text"] = text
        if media_urls is not None:
            body["mediaUrls"] = media_urls
        if metadata is not None:
            body["metadata"] = metadata

        data = await self._http.request(
            method="PATCH",
            path=f"/drafts/{quote(id, safe='')}",
            body=body,
        )

        try:
            return MessageDraft(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def approve(self, id: str) -> MessageDraft:
        data = await self._http.request(
            method="POST",
            path=f"/drafts/{quote(id, safe='')}/approve",
        )

        try:
            return MessageDraft(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def reject(self, id: str, reason: Optional[str] = None) -> MessageDraft:
        body: Dict[str, Any] = {}
        if reason is not None:
            body["reason"] = reason

        data = await self._http.request(
            method="POST",
            path=f"/drafts/{quote(id, safe='')}/reject",
            body=body if body else None,
        )

        try:
            return MessageDraft(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e
