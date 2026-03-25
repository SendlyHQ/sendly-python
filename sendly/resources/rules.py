from typing import Any, Dict, Optional
from urllib.parse import quote

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError
from ..types import (
    Rule,
    RuleListResponse,
)
from ..utils.http import AsyncHttpClient, HttpClient


class RulesResource:
    def __init__(self, http: HttpClient):
        self._http = http

    def list(self) -> RuleListResponse:
        data = self._http.request(
            method="GET",
            path="/rules",
        )

        try:
            return RuleListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def create(
        self,
        name: str,
        conditions: Dict[str, Any],
        actions: Dict[str, Any],
        priority: Optional[int] = None,
    ) -> Rule:
        body: Dict[str, Any] = {
            "name": name,
            "conditions": conditions,
            "actions": actions,
        }
        if priority is not None:
            body["priority"] = priority

        data = self._http.request(
            method="POST",
            path="/rules",
            body=body,
        )

        try:
            return Rule(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def update(
        self,
        id: str,
        name: Optional[str] = None,
        conditions: Optional[Dict[str, Any]] = None,
        actions: Optional[Dict[str, Any]] = None,
        priority: Optional[int] = None,
    ) -> Rule:
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if conditions is not None:
            body["conditions"] = conditions
        if actions is not None:
            body["actions"] = actions
        if priority is not None:
            body["priority"] = priority

        data = self._http.request(
            method="PATCH",
            path=f"/rules/{quote(id, safe='')}",
            body=body,
        )

        try:
            return Rule(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def delete(self, id: str) -> None:
        self._http.request(
            method="DELETE",
            path=f"/rules/{quote(id, safe='')}",
        )


class AsyncRulesResource:
    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list(self) -> RuleListResponse:
        data = await self._http.request(
            method="GET",
            path="/rules",
        )

        try:
            return RuleListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def create(
        self,
        name: str,
        conditions: Dict[str, Any],
        actions: Dict[str, Any],
        priority: Optional[int] = None,
    ) -> Rule:
        body: Dict[str, Any] = {
            "name": name,
            "conditions": conditions,
            "actions": actions,
        }
        if priority is not None:
            body["priority"] = priority

        data = await self._http.request(
            method="POST",
            path="/rules",
            body=body,
        )

        try:
            return Rule(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def update(
        self,
        id: str,
        name: Optional[str] = None,
        conditions: Optional[Dict[str, Any]] = None,
        actions: Optional[Dict[str, Any]] = None,
        priority: Optional[int] = None,
    ) -> Rule:
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if conditions is not None:
            body["conditions"] = conditions
        if actions is not None:
            body["actions"] = actions
        if priority is not None:
            body["priority"] = priority

        data = await self._http.request(
            method="PATCH",
            path=f"/rules/{quote(id, safe='')}",
            body=body,
        )

        try:
            return Rule(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def delete(self, id: str) -> None:
        await self._http.request(
            method="DELETE",
            path=f"/rules/{quote(id, safe='')}",
        )
