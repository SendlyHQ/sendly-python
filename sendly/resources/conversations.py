from typing import Any, Dict, List, Optional
from urllib.parse import quote

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError
from ..types import (
    Conversation,
    ConversationListResponse,
    ConversationWithMessages,
    Message,
)
from ..utils.http import AsyncHttpClient, HttpClient


class ConversationsResource:
    def __init__(self, http: HttpClient):
        self._http = http

    def list(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
    ) -> ConversationListResponse:
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status

        data = self._http.request(
            method="GET",
            path="/conversations",
            params=params if params else None,
        )

        try:
            return ConversationListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def get(
        self,
        id: str,
        include_messages: bool = False,
        message_limit: Optional[int] = None,
    ) -> ConversationWithMessages:
        params: Dict[str, Any] = {}
        if include_messages:
            params["include_messages"] = "true"
        if message_limit is not None:
            params["message_limit"] = message_limit

        data = self._http.request(
            method="GET",
            path=f"/conversations/{quote(id, safe='')}",
            params=params if params else None,
        )

        try:
            return ConversationWithMessages(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def reply(
        self,
        conversation_id: str,
        text: str,
        media_urls: Optional[List[str]] = None,
    ) -> Message:
        body: Dict[str, Any] = {"text": text}
        if media_urls:
            body["mediaUrls"] = media_urls

        data = self._http.request(
            method="POST",
            path=f"/conversations/{quote(conversation_id, safe='')}/messages",
            body=body,
        )

        try:
            return Message(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def update(
        self,
        id: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Conversation:
        body: Dict[str, Any] = {}
        if metadata is not None:
            body["metadata"] = metadata
        if tags is not None:
            body["tags"] = tags

        data = self._http.request(
            method="PATCH",
            path=f"/conversations/{quote(id, safe='')}",
            body=body,
        )

        try:
            return Conversation(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def close(self, id: str) -> Conversation:
        data = self._http.request(
            method="POST",
            path=f"/conversations/{quote(id, safe='')}/close",
        )

        try:
            return Conversation(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def reopen(self, id: str) -> Conversation:
        data = self._http.request(
            method="POST",
            path=f"/conversations/{quote(id, safe='')}/reopen",
        )

        try:
            return Conversation(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def mark_read(self, id: str) -> Conversation:
        data = self._http.request(
            method="POST",
            path=f"/conversations/{quote(id, safe='')}/mark-read",
        )

        try:
            return Conversation(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e


class AsyncConversationsResource:
    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
    ) -> ConversationListResponse:
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status

        data = await self._http.request(
            method="GET",
            path="/conversations",
            params=params if params else None,
        )

        try:
            return ConversationListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def get(
        self,
        id: str,
        include_messages: bool = False,
        message_limit: Optional[int] = None,
    ) -> ConversationWithMessages:
        params: Dict[str, Any] = {}
        if include_messages:
            params["include_messages"] = "true"
        if message_limit is not None:
            params["message_limit"] = message_limit

        data = await self._http.request(
            method="GET",
            path=f"/conversations/{quote(id, safe='')}",
            params=params if params else None,
        )

        try:
            return ConversationWithMessages(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def reply(
        self,
        conversation_id: str,
        text: str,
        media_urls: Optional[List[str]] = None,
    ) -> Message:
        body: Dict[str, Any] = {"text": text}
        if media_urls:
            body["mediaUrls"] = media_urls

        data = await self._http.request(
            method="POST",
            path=f"/conversations/{quote(conversation_id, safe='')}/messages",
            body=body,
        )

        try:
            return Message(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def update(
        self,
        id: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Conversation:
        body: Dict[str, Any] = {}
        if metadata is not None:
            body["metadata"] = metadata
        if tags is not None:
            body["tags"] = tags

        data = await self._http.request(
            method="PATCH",
            path=f"/conversations/{quote(id, safe='')}",
            body=body,
        )

        try:
            return Conversation(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def close(self, id: str) -> Conversation:
        data = await self._http.request(
            method="POST",
            path=f"/conversations/{quote(id, safe='')}/close",
        )

        try:
            return Conversation(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def reopen(self, id: str) -> Conversation:
        data = await self._http.request(
            method="POST",
            path=f"/conversations/{quote(id, safe='')}/reopen",
        )

        try:
            return Conversation(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def mark_read(self, id: str) -> Conversation:
        data = await self._http.request(
            method="POST",
            path=f"/conversations/{quote(id, safe='')}/mark-read",
        )

        try:
            return Conversation(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e
