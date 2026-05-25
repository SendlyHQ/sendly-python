"""
Business Upgrade Resource — Entity-Upgrade ("fork-with-new-number")

Manages the toll-free business entity upgrade flow: when a customer
forms a new legal entity (e.g. an LLC), this resource lets them
reserve a new toll-free number under the new entity, submit it for
carrier review, and atomically swap to it on approval — without
disrupting outbound SMS during the 1-2 week review window.

See: https://sendly.live/docs/business-upgrade
"""

import binascii
import os
from typing import Any, Dict, Literal, Optional, Tuple, Union
from urllib.parse import quote

import httpx

from ..errors import SendlyError
from ..utils.http import AsyncHttpClient, HttpClient

EntityType = Literal[
    "SOLE_PROPRIETOR",
    "PRIVATE_PROFIT",
    "PUBLIC_PROFIT",
    "NON_PROFIT",
    "GOVERNMENT",
]

BrnType = Literal["EIN", "SSN", "DUNS", "CRA", "VAT", "LEI", "OTHER"]

Disposition = Literal["moved", "released"]


# Allowlisted fields that the server accepts on start / resubmit.
# Mirrors StartUpgradeParams in the Node SDK.
_UPGRADE_FIELDS = (
    "businessName",
    "doingBusinessAs",
    "brn",
    "brnType",
    "brnCountry",
    "entityType",
    "website",
    "address1",
    "address2",
    "city",
    "state",
    "zip",
    "addressCountry",
    "contactFirstName",
    "contactLastName",
    "contactEmail",
    "contactPhone",
    "monthlyVolume",
    "useCase",
    "useCaseSummary",
    "sampleMessages",
    "optInWorkflow",
    "privacyUrl",
    "termsUrl",
    "additionalInformation",
    "ageGatedContent",
)

# snake_case kwarg -> server camelCase
_SNAKE_TO_CAMEL = {
    "business_name": "businessName",
    "doing_business_as": "doingBusinessAs",
    "brn": "brn",
    "brn_type": "brnType",
    "brn_country": "brnCountry",
    "entity_type": "entityType",
    "website": "website",
    "address1": "address1",
    "address2": "address2",
    "city": "city",
    "state": "state",
    "zip": "zip",
    "address_country": "addressCountry",
    "contact_first_name": "contactFirstName",
    "contact_last_name": "contactLastName",
    "contact_email": "contactEmail",
    "contact_phone": "contactPhone",
    "monthly_volume": "monthlyVolume",
    "use_case": "useCase",
    "use_case_summary": "useCaseSummary",
    "sample_messages": "sampleMessages",
    "opt_in_workflow": "optInWorkflow",
    "privacy_url": "privacyUrl",
    "terms_url": "termsUrl",
    "additional_information": "additionalInformation",
    "age_gated_content": "ageGatedContent",
}


# Type alias for the ein_doc parameter — accepts either:
#   - bytes / bytearray (file contents)
#   - (filename, bytes) tuple
#   - (filename, bytes, content_type) tuple
#   - a dict with "buffer", optional "filename", optional "content_type"
EinDocInput = Union[
    bytes,
    bytearray,
    Tuple[str, bytes],
    Tuple[str, bytes, str],
    Dict[str, Any],
]


def _normalize_payload(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Translate snake_case kwargs into the camelCase shape the API expects.

    Drops keys whose value is None. Booleans pass through unchanged.
    Unknown keys are forwarded as-is so callers can opt into newer fields
    the SDK doesn't yet know about.
    """
    out: Dict[str, Any] = {}
    for key, value in fields.items():
        if value is None:
            continue
        camel = _SNAKE_TO_CAMEL.get(key, key)
        out[camel] = value
    return out


def _coerce_form_value(value: Any) -> str:
    """Stringify a value for multipart form encoding."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _build_multipart(
    payload: Dict[str, Any],
    ein_doc: Optional[EinDocInput],
) -> Tuple[Dict[str, str], Optional[Dict[str, Tuple[str, bytes, str]]]]:
    """Split the payload + optional ein doc into (form-data, files) for httpx."""
    data: Dict[str, str] = {k: _coerce_form_value(v) for k, v in payload.items()}

    files: Optional[Dict[str, Tuple[str, bytes, str]]] = None
    if ein_doc is not None:
        filename = "ein-doc.pdf"
        content_type = "application/pdf"
        buffer: bytes

        if isinstance(ein_doc, (bytes, bytearray)):
            buffer = bytes(ein_doc)
        elif isinstance(ein_doc, tuple):
            if len(ein_doc) == 2:
                filename, buffer_raw = ein_doc
                buffer = bytes(buffer_raw)
            elif len(ein_doc) == 3:
                filename, buffer_raw, content_type = ein_doc
                buffer = bytes(buffer_raw)
            else:
                raise ValueError(
                    "ein_doc tuple must be (filename, bytes) or (filename, bytes, content_type)"
                )
        elif isinstance(ein_doc, dict):
            if "buffer" not in ein_doc:
                raise ValueError("ein_doc dict must include a 'buffer' key")
            buffer_raw = ein_doc["buffer"]
            buffer = bytes(buffer_raw)
            filename = ein_doc.get("filename", filename)
            content_type = ein_doc.get("content_type", content_type)
        else:
            raise TypeError(
                "ein_doc must be bytes, a (filename, bytes[, content_type]) tuple, or a dict"
            )

        files = {"einDoc": (filename, buffer, content_type)}

    return data, files


def _validate_response(data: Any) -> Dict[str, Any]:
    """Defensive check that the API returned a JSON object."""
    if not isinstance(data, dict):
        raise SendlyError(
            message=f"Invalid API response format: expected JSON object, got {type(data).__name__}",
            code="invalid_response",
            status_code=200,
        )
    return data


def _generate_boundary() -> str:
    """Random boundary token for a multipart payload."""
    return binascii.hexlify(os.urandom(16)).decode("ascii")


def _encode_multipart(
    data: Dict[str, str],
    files: Optional[Dict[str, Tuple[str, bytes, str]]],
) -> Tuple[bytes, str]:
    """Encode form fields + file parts as multipart/form-data.

    Returns `(body_bytes, content_type)`. We do this ourselves rather than
    relying on httpx's per-request encoding so the client-level
    `Content-Type: application/json` header on the shared HTTP client can't
    shadow the multipart boundary on the wire.
    """
    boundary = _generate_boundary()
    crlf = b"\r\n"
    chunks: list = []
    for name, value in data.items():
        chunks.append(f"--{boundary}".encode("ascii"))
        chunks.append(crlf)
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"'.encode("utf-8")
        )
        chunks.append(crlf)
        chunks.append(crlf)
        chunks.append(value.encode("utf-8") if isinstance(value, str) else bytes(value))
        chunks.append(crlf)
    if files:
        for name, (filename, content, content_type) in files.items():
            chunks.append(f"--{boundary}".encode("ascii"))
            chunks.append(crlf)
            chunks.append(
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"'
                ).encode("utf-8")
            )
            chunks.append(crlf)
            chunks.append(f"Content-Type: {content_type}".encode("ascii"))
            chunks.append(crlf)
            chunks.append(crlf)
            chunks.append(bytes(content))
            chunks.append(crlf)
    chunks.append(f"--{boundary}--".encode("ascii"))
    chunks.append(crlf)
    body = b"".join(chunks)
    return body, f"multipart/form-data; boundary={boundary}"


def _multipart_headers(
    api_key: str,
    user_agent: str,
    organization_id: Optional[str],
    content_type: str,
    content_length: int,
) -> Dict[str, str]:
    """Headers for a manually-encoded multipart request."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": content_type,
        "Content-Length": str(content_length),
        "User-Agent": user_agent,
    }
    if organization_id:
        headers["X-Organization-Id"] = organization_id
    return headers


def _build_multipart_request(
    client: Union[httpx.Client, httpx.AsyncClient],
    path: str,
    api_key: str,
    organization_id: Optional[str],
    data: Dict[str, str],
    files: Optional[Dict[str, Tuple[str, bytes, str]]],
) -> httpx.Request:
    """Build an httpx.Request carrying a pre-encoded multipart body."""
    body, content_type = _encode_multipart(data, files)
    user_agent = client.headers.get("User-Agent", "")
    headers = _multipart_headers(
        api_key, user_agent, organization_id, content_type, len(body)
    )
    return client.build_request(
        method="POST",
        url=path,
        content=body,
        headers=headers,
    )


def _multipart_request_sync(
    http: HttpClient,
    path: str,
    data: Dict[str, str],
    files: Optional[Dict[str, Tuple[str, bytes, str]]],
) -> Dict[str, Any]:
    """POST a multipart/form-data body via the SDK's underlying httpx client."""
    client = http.client
    request = _build_multipart_request(
        client, path, http.api_key, http.organization_id, data, files
    )
    response = client.send(request)
    http._update_rate_limit_info(response.headers)
    parsed = http._parse_response(response)
    return _validate_response(parsed)


async def _multipart_request_async(
    http: AsyncHttpClient,
    path: str,
    data: Dict[str, str],
    files: Optional[Dict[str, Tuple[str, bytes, str]]],
) -> Dict[str, Any]:
    """Async equivalent of `_multipart_request_sync`."""
    client = http.client
    request = _build_multipart_request(
        client, path, http.api_key, http.organization_id, data, files
    )
    response = await client.send(request)
    http._update_rate_limit_info(response.headers)
    parsed = http._parse_response(response)
    return _validate_response(parsed)


class BusinessUpgradeResource:
    """
    Business upgrade resource (synchronous).

    Example:
        >>> client = Sendly('sk_live_v1_xxx')
        >>>
        >>> # Preview validation before submitting
        >>> preview = client.business_upgrade.preflight(
        ...     business_name='Acme Holdings LLC',
        ...     brn='12-3456789',
        ...     brn_type='EIN',
        ...     brn_country='US',
        ...     entity_type='PRIVATE_PROFIT',
        ... )
        >>>
        >>> # Submit the upgrade with the IRS letter
        >>> with open('CP-575.pdf', 'rb') as f:
        ...     result = client.business_upgrade.start(
        ...         'ws_abc',
        ...         business_name='Acme Holdings LLC',
        ...         brn='12-3456789',
        ...         brn_type='EIN',
        ...         brn_country='US',
        ...         entity_type='PRIVATE_PROFIT',
        ...         ein_doc=(f.name, f.read()),
        ...     )
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def preflight(self, **candidate: Any) -> Dict[str, Any]:
        """Validate a candidate entity upgrade payload before submission.

        No writes — purely advisory. Returns issues + proposed auto-fixes.

        Accepts the same fields as :meth:`start` (snake_case kwargs).
        """
        body = _normalize_payload(candidate)
        data = self._http.request(method="POST", path="/verification/preflight", body=body)
        return _validate_response(data)

    def best_prefill(self) -> Dict[str, Any]:
        """Get a "best-of" prefill across the caller's verified workspaces.

        Returns most-recent non-empty values per messaging field. Use this
        to pre-populate the upgrade form for users whose current workspace
        has incomplete data.
        """
        data = self._http.request(method="GET", path="/verification/best-prefill")
        return _validate_response(data)

    def start(
        self,
        workspace_id: str,
        *,
        ein_doc: Optional[EinDocInput] = None,
        **params: Any,
    ) -> Dict[str, Any]:
        """Start an entity upgrade for the given workspace.

        Auto-provisions a new toll-free number + messaging profile and
        submits to the carrier for review. The current toll-free number
        continues sending throughout the 1-2 week carrier review; on
        approval, an atomic swap promotes the new number.

        Args:
            workspace_id: The workspace ("organization") ID to upgrade.
            ein_doc: Optional IRS confirmation letter (CP-575) as bytes,
                ``(filename, bytes)``, ``(filename, bytes, content_type)``,
                or a dict with ``buffer`` / ``filename`` / ``content_type``.
            **params: Fields describing the new entity. Same shape as
                the Node SDK's StartUpgradeParams (snake_case here).
                Required: ``business_name``, ``brn``, ``brn_type``,
                ``brn_country``, ``entity_type``.
        """
        payload = _normalize_payload(params)
        data, files = _build_multipart(payload, ein_doc)
        path = f"/workspaces/{quote(workspace_id, safe='')}/upgrade"
        return _multipart_request_sync(self._http, path, data, files)

    def status(self, workspace_id: str) -> Dict[str, Any]:
        """Check whether the given workspace has a pending entity upgrade.

        Returns ``{"pending": None}`` if no upgrade is in flight.
        """
        data = self._http.request(
            method="GET",
            path=f"/workspaces/{quote(workspace_id, safe='')}/upgrade/status",
        )
        return _validate_response(data)

    def cancel(self, workspace_id: str) -> Dict[str, Any]:
        """Cancel a pending entity upgrade for the given workspace.

        Releases the reserved toll-free number, deletes the new messaging
        profile, and removes the stored EIN document. Idempotent.
        """
        data = self._http.request(
            method="POST",
            path=f"/workspaces/{quote(workspace_id, safe='')}/upgrade/cancel",
        )
        return _validate_response(data)

    def resubmit(
        self,
        workspace_id: str,
        *,
        ein_doc: Optional[EinDocInput] = None,
        **params: Any,
    ) -> Dict[str, Any]:
        """Resubmit a rejected (or waiting-for-customer) entity upgrade.

        Supply only the fields you want to change — the rest are pulled
        from the existing pending record.
        """
        payload = _normalize_payload(params)
        data, files = _build_multipart(payload, ein_doc)
        path = f"/workspaces/{quote(workspace_id, safe='')}/upgrade/resubmit"
        return _multipart_request_sync(self._http, path, data, files)

    def set_disposition(
        self,
        workspace_id: str,
        *,
        disposition: Disposition,
        target_workspace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """After a successful entity-upgrade approval, choose what happens
        to the old toll-free number.

        Args:
            workspace_id: The workspace whose upgrade was approved.
            disposition: Either ``"moved"`` (requires ``target_workspace_id``)
                to keep the old number under another workspace owned by the
                same user, or ``"released"`` to return it to the carrier pool.
            target_workspace_id: Destination workspace if moving the number.
        """
        body: Dict[str, Any] = {"disposition": disposition}
        if target_workspace_id is not None:
            body["targetOrgId"] = target_workspace_id
        data = self._http.request(
            method="POST",
            path=f"/workspaces/{quote(workspace_id, safe='')}/upgrade/disposition",
            body=body,
        )
        return _validate_response(data)


class AsyncBusinessUpgradeResource:
    """
    Business upgrade resource (asynchronous).

    Async equivalent of :class:`BusinessUpgradeResource`.
    """

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def preflight(self, **candidate: Any) -> Dict[str, Any]:
        """Async: validate a candidate entity upgrade payload before submission."""
        body = _normalize_payload(candidate)
        data = await self._http.request(
            method="POST", path="/verification/preflight", body=body
        )
        return _validate_response(data)

    async def best_prefill(self) -> Dict[str, Any]:
        """Async: get a "best-of" prefill across the caller's verified workspaces."""
        data = await self._http.request(method="GET", path="/verification/best-prefill")
        return _validate_response(data)

    async def start(
        self,
        workspace_id: str,
        *,
        ein_doc: Optional[EinDocInput] = None,
        **params: Any,
    ) -> Dict[str, Any]:
        """Async: start an entity upgrade for the given workspace."""
        payload = _normalize_payload(params)
        data, files = _build_multipart(payload, ein_doc)
        path = f"/workspaces/{quote(workspace_id, safe='')}/upgrade"
        return await _multipart_request_async(self._http, path, data, files)

    async def status(self, workspace_id: str) -> Dict[str, Any]:
        """Async: check whether the given workspace has a pending entity upgrade."""
        data = await self._http.request(
            method="GET",
            path=f"/workspaces/{quote(workspace_id, safe='')}/upgrade/status",
        )
        return _validate_response(data)

    async def cancel(self, workspace_id: str) -> Dict[str, Any]:
        """Async: cancel a pending entity upgrade for the given workspace."""
        data = await self._http.request(
            method="POST",
            path=f"/workspaces/{quote(workspace_id, safe='')}/upgrade/cancel",
        )
        return _validate_response(data)

    async def resubmit(
        self,
        workspace_id: str,
        *,
        ein_doc: Optional[EinDocInput] = None,
        **params: Any,
    ) -> Dict[str, Any]:
        """Async: resubmit a rejected entity upgrade with updated fields."""
        payload = _normalize_payload(params)
        data, files = _build_multipart(payload, ein_doc)
        path = f"/workspaces/{quote(workspace_id, safe='')}/upgrade/resubmit"
        return await _multipart_request_async(self._http, path, data, files)

    async def set_disposition(
        self,
        workspace_id: str,
        *,
        disposition: Disposition,
        target_workspace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Async: choose what happens to the old toll-free number after approval."""
        body: Dict[str, Any] = {"disposition": disposition}
        if target_workspace_id is not None:
            body["targetOrgId"] = target_workspace_id
        data = await self._http.request(
            method="POST",
            path=f"/workspaces/{quote(workspace_id, safe='')}/upgrade/disposition",
            body=body,
        )
        return _validate_response(data)


__all__ = [
    "BrnType",
    "BusinessUpgradeResource",
    "AsyncBusinessUpgradeResource",
    "Disposition",
    "EinDocInput",
    "EntityType",
]
