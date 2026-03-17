from typing import Any, Dict, Optional
from urllib.parse import quote

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError
from ..types import (
    Label,
    LabelListResponse,
)
from ..utils.http import AsyncHttpClient, HttpClient


class LabelsResource:
    def __init__(self, http: HttpClient):
        self._http = http

    def create(
        self,
        name: str,
        color: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Label:
        body: Dict[str, Any] = {"name": name}
        if color is not None:
            body["color"] = color
        if description is not None:
            body["description"] = description

        data = self._http.request(
            method="POST",
            path="/labels",
            body=body,
        )

        try:
            return Label(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def list(self) -> LabelListResponse:
        data = self._http.request(
            method="GET",
            path="/labels",
        )

        try:
            return LabelListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def delete(self, id: str) -> None:
        self._http.request(
            method="DELETE",
            path=f"/labels/{quote(id, safe='')}",
        )


class AsyncLabelsResource:
    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def create(
        self,
        name: str,
        color: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Label:
        body: Dict[str, Any] = {"name": name}
        if color is not None:
            body["color"] = color
        if description is not None:
            body["description"] = description

        data = await self._http.request(
            method="POST",
            path="/labels",
            body=body,
        )

        try:
            return Label(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def list(self) -> LabelListResponse:
        data = await self._http.request(
            method="GET",
            path="/labels",
        )

        try:
            return LabelListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def delete(self, id: str) -> None:
        await self._http.request(
            method="DELETE",
            path=f"/labels/{quote(id, safe='')}",
        )
