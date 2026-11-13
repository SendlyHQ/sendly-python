"""
Short Codes Resource - apply for a US short code and track the application

A short code is a 5 or 6 digit US sender. Getting one is an application, not
a purchase: you fill it in, Sendly reviews it, the carrier forms are signed,
Sendly files it, and each carrier certifies the code separately.

The application lives at ``short_codes.application``; every application and
code is listed with ``short_codes.list()``. Reads need an API key with the
``short_codes:read`` scope, writes ``short_codes:write``. Until short codes
are enabled for the account every call raises ``SendlyError`` with code
``short_codes_not_enabled`` (HTTP 404).
"""

from typing import Any, Dict, Optional, Type, TypeVar, Union

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError, ValidationError
from ..types import (
    ShortCodeApplicationInput,
    ShortCodeApplicationView,
    ShortCodeListResponse,
    ShortCodePreflight,
    ShortCodeSubmitInput,
)
from ..utils.http import AsyncHttpClient, HttpClient

_M = TypeVar("_M", bound=BaseModel)

ShortCodeApplicationInputLike = Union[ShortCodeApplicationInput, Dict[str, Any]]
ShortCodeSubmitInputLike = Union[ShortCodeSubmitInput, ShortCodeApplicationInput, Dict[str, Any]]


def _dump(value: Any, model: Type[BaseModel], name: str) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, BaseModel):
        value = value.model_dump(by_alias=True, exclude_unset=True)
    if not isinstance(value, dict):
        raise ValidationError(f"'{name}' must be a {model.__name__} or a dict")
    try:
        parsed = model.model_validate(value)
    except PydanticValidationError as e:
        raise ValidationError(f"Invalid '{name}': {e}") from e
    dumped: Dict[str, Any] = parsed.model_dump(by_alias=True, exclude_unset=True)
    return dumped


def _submit_body(
    application: Optional[ShortCodeSubmitInputLike], accept_terms: Optional[bool]
) -> Dict[str, Any]:
    body = _dump(application, ShortCodeSubmitInput, "application")
    if accept_terms is not None:
        body["acceptTerms"] = accept_terms
    return body


def _parse(model: Type[_M], data: Any) -> _M:
    try:
        return model.model_validate(data)
    except PydanticValidationError as e:
        raise SendlyError(
            message=f"Invalid API response format: {e}",
            code="invalid_response",
            status_code=200,
        ) from e


class ShortCodeApplicationResource:
    """The workspace's short code application (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def get(self) -> ShortCodeApplicationView:
        """Fetch the workspace's short code application, with the documents
        it needs, the quote, and ``billing``: where the setup fee and the
        monthly lease stand. With no application yet, ``application.id`` is
        None. Requires the ``short_codes:read`` scope.

        Example:
            >>> view = client.short_codes.application.get()
            >>> if not view.editable:
            ...     print(view.lock_message)
        """
        data = self._http.request(method="GET", path="/short_codes/application")
        return _parse(ShortCodeApplicationView, data)

    def update(
        self,
        application: ShortCodeApplicationInputLike,
        *,
        idempotency_key: Optional[str] = None,
    ) -> ShortCodeApplicationView:
        """Save answers on the application, creating it on the first call.

        Only the fields you set are sent: a field left out keeps its saved
        value, and an explicit None clears it. Fields Sendly or the carriers
        own (the digits, the status, the review state) are ignored and named
        back in ``ignored_fields``. Requires the ``short_codes:write`` scope.

        Args:
            application: :class:`~sendly.types.ShortCodeApplicationInput` or
                a dict of its fields (snake_case or camelCase keys).
            idempotency_key: Optional key (1-255 printable ASCII characters)
                sent as the Idempotency-Key header, so a repeat of the same
                save returns the first answer. When omitted, a unique key is
                generated automatically and reused across retry attempts.

        Raises:
            SendlyError: ``short_code_locked`` (409) once the application is
                with Sendly or the carriers; ``short_code_invalid_application``
                (422) for an unknown ``order_type`` or ``code_type``.

        Example:
            >>> client.short_codes.application.update({
            ...     'use_case': 'Delivery alerts for Acme orders',
            ...     'message_frequency': '4 messages per month',
            ... })
        """
        body = _dump(application, ShortCodeApplicationInput, "application")
        data = self._http.request(
            method="PUT",
            path="/short_codes/application",
            body=body,
            idempotency_key=idempotency_key,
        )
        return _parse(ShortCodeApplicationView, data)

    def check(
        self, application: Optional[ShortCodeApplicationInputLike] = None
    ) -> ShortCodePreflight:
        """Check the application against the carrier rules without changing
        anything. Unsaved answers can be passed in and are checked on top of
        what is saved. Requires the ``short_codes:read`` scope.

        Example:
            >>> result = client.short_codes.application.check()
            >>> for issue in result.issues:
            ...     print(issue.path, issue.message)
        """
        body = _dump(application, ShortCodeApplicationInput, "application")
        data = self._http.request(
            method="POST", path="/short_codes/application/preflight", body=body
        )
        return _parse(ShortCodePreflight, data)

    def submit(
        self,
        application: Optional[ShortCodeSubmitInputLike] = None,
        *,
        accept_terms: Optional[bool] = None,
        idempotency_key: Optional[str] = None,
    ) -> ShortCodeApplicationView:
        """Submit the application to Sendly for review.

        Submitting charges the one-time $999 setup fee to the workspace's
        card on file, so pass ``accept_terms=True`` to accept it, the monthly
        lease from go-live and the 3-month minimum. The fee is refunded in
        full if Sendly rejects the application before filing it. Submitting
        twice is safe: the second call reports ``already_submitted`` and
        charges nothing. Requires the ``short_codes:write`` scope.

        Args:
            application: Optional final answers, saved before the check.
            accept_terms: Sent as ``acceptTerms``; must be True.
            idempotency_key: Optional key (1-255 printable ASCII characters)
                sent as the Idempotency-Key header, so a repeat of the same
                submit returns the first answer. When omitted, a unique key
                is generated automatically and reused across retry attempts.

        Raises:
            SendlyError: ``verification_required`` (403) until the business
                is verified (the answers sent are saved anyway);
                ``short_code_invalid_application`` (422) with an ``errors``
                list naming every field, including ``acceptTerms``;
                ``short_code_ai_draft_unedited`` (422) when the only issues
                are suggested wording nobody edited;
                ``payment_method_required``, ``payment_failed`` or
                ``payment_requires_authentication`` (402) when the fee can't
                be charged, and the application stays a draft.

        Example:
            >>> result = client.short_codes.application.submit(accept_terms=True)
            >>> print(result.application.review_status)  # 'awaiting_review'
        """
        data = self._http.request(
            method="POST",
            path="/short_codes/application/submit",
            body=_submit_body(application, accept_terms),
            idempotency_key=idempotency_key,
        )
        return _parse(ShortCodeApplicationView, data)


class ShortCodesResource:
    """Short codes: list the workspace's codes and manage its application (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http
        self.application = ShortCodeApplicationResource(http)

    def list(self) -> ShortCodeListResponse:
        """List every short code application of the workspace, newest first,
        with its code once Sendly assigns one. Drafts (``short_code`` None),
        rejected and cancelled applications are listed too, so filter on
        ``status`` for the codes you can send from. Requires the
        ``short_codes:read`` scope.

        Example:
            >>> codes = client.short_codes.list().short_codes
            >>> sendable = [c for c in codes if c.status == 'active']
        """
        data = self._http.request(method="GET", path="/short_codes")
        return _parse(ShortCodeListResponse, data)


class AsyncShortCodeApplicationResource:
    """The workspace's short code application (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def get(self) -> ShortCodeApplicationView:
        """Fetch the application. See :meth:`ShortCodeApplicationResource.get`."""
        data = await self._http.request(method="GET", path="/short_codes/application")
        return _parse(ShortCodeApplicationView, data)

    async def update(
        self,
        application: ShortCodeApplicationInputLike,
        *,
        idempotency_key: Optional[str] = None,
    ) -> ShortCodeApplicationView:
        """Save answers. See :meth:`ShortCodeApplicationResource.update`."""
        body = _dump(application, ShortCodeApplicationInput, "application")
        data = await self._http.request(
            method="PUT",
            path="/short_codes/application",
            body=body,
            idempotency_key=idempotency_key,
        )
        return _parse(ShortCodeApplicationView, data)

    async def check(
        self, application: Optional[ShortCodeApplicationInputLike] = None
    ) -> ShortCodePreflight:
        """Dry-run the application. See :meth:`ShortCodeApplicationResource.check`."""
        body = _dump(application, ShortCodeApplicationInput, "application")
        data = await self._http.request(
            method="POST", path="/short_codes/application/preflight", body=body
        )
        return _parse(ShortCodePreflight, data)

    async def submit(
        self,
        application: Optional[ShortCodeSubmitInputLike] = None,
        *,
        accept_terms: Optional[bool] = None,
        idempotency_key: Optional[str] = None,
    ) -> ShortCodeApplicationView:
        """Submit for review. See :meth:`ShortCodeApplicationResource.submit`."""
        data = await self._http.request(
            method="POST",
            path="/short_codes/application/submit",
            body=_submit_body(application, accept_terms),
            idempotency_key=idempotency_key,
        )
        return _parse(ShortCodeApplicationView, data)


class AsyncShortCodesResource:
    """Short codes: list the workspace's codes and manage its application (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http
        self.application = AsyncShortCodeApplicationResource(http)

    async def list(self) -> ShortCodeListResponse:
        """List every application and code. See :meth:`ShortCodesResource.list`."""
        data = await self._http.request(method="GET", path="/short_codes")
        return _parse(ShortCodeListResponse, data)
