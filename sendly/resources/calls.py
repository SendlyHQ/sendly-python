"""
Calls Resource - Phone calls handled by your AI agents

A workspace phone number can take and place phone calls. Over the API you
place an outbound call that one of your AI agents handles, list and inspect
calls, end a call, and fetch recordings. Switching voice on for a number,
choosing how it answers, registering an emergency address and creating agents
are dashboard steps in this release; ``client.numbers.list()`` reports each
number's ``voice_enabled`` and ``voice_mode`` so you can pick a ``from_``.

Reads need an API key with the ``calls:read`` scope, writes ``calls:write``.
Placing and ending calls needs a live key (``live_key_required`` otherwise).
Voice is enabled workspace by workspace; until it is enabled for yours every
method raises ``SendlyError`` with code ``voice_not_enabled`` (HTTP 404).

Calls are prepaid from the workspace balance per started minute: 2 credits a
minute outbound, plus 8 a minute while an AI agent is on the line, so an
agent-handled outbound call costs 10 credits a minute. Unanswered calls cost
nothing. Destinations are US and Canada.
"""

from enum import Enum
from typing import Any, Dict, Optional, Type, TypeVar, Union
from urllib.parse import quote

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError, ValidationError
from ..types import Call, CallListResponse, CallRecording
from ..utils.http import AsyncHttpClient, HttpClient

_M = TypeVar("_M", bound=BaseModel)

EnumLike = Union[str, Enum]


class CallsResource:
    """Voice calls API resource (sync)

    Example:
        >>> call = client.calls.create(
        ...     to='+15555550123',
        ...     agent_id='3c4d5e6f-7081-4293-a4b5-c6d7e8f90a1b',
        ...     context='You are calling Jordan to confirm the 3pm appointment.',
        ... )
        >>> print(call.status)  # 'ringing'
        >>> call = client.calls.get(call.id)
        >>> for line in call.transcript or []:
        ...     print(line.speaker, line.text)
    """

    def __init__(self, http: HttpClient):
        self._http = http

    def create(
        self,
        to: str,
        agent_id: str,
        *,
        from_: Optional[str] = None,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Call:
        """Place a phone call handled by one of your AI agents. Requires the
        ``calls:write`` scope and a live API key.

        The call is returned while it is still ``ringing``; poll :meth:`get`
        or subscribe to the ``call.started`` and ``call.completed`` webhooks
        to follow it. Nothing is charged until the callee answers.

        Args:
            to: Number to call, in E.164 format. US and Canada only
                (``destination_not_supported`` otherwise).
            agent_id: The AI agent that talks on the call. Calls placed over
                the API always have an agent on the line.
            from_: A voice-enabled number in your workspace. Optional
                when exactly one number is voice-enabled; required when
                several are (``from_number_required``).
            context: Up to 2000 characters added to the agent's instructions
                for this call only, for example who is being called and why.
                Not echoed back.
            metadata: Up to 20 string pairs (keys 1-40 characters of
                ``A-Za-z0-9_.:-``, values up to 500 characters). Stored and
                echoed on every read and in every ``call.*`` webhook.
            idempotency_key: Optional key (1-255 printable ASCII characters)
                sent as the Idempotency-Key header - retrying with the same
                key returns the original call instead of dialling again. When
                omitted, a unique key is generated automatically and reused
                across retry attempts.

        Raises:
            ValidationError: ``to`` or ``agent_id`` is empty.
            InsufficientCreditsError: The balance cannot cover one minute at
                the agent rate (``credits_needed``, ``current_balance``).
            SendlyError: With ``code`` ``agent_not_found``, ``agent_disabled``,
                ``no_voice_number``, ``number_not_found``, ``e911_required``
                (register an emergency address for the number first),
                ``lines_busy`` (retry shortly), ``daily_call_limit``,
                ``outbound_calls_not_enabled`` or ``voice_not_enabled``.

        Example:
            >>> call = client.calls.create(
            ...     to='+15555550123',
            ...     agent_id='3c4d5e6f-7081-4293-a4b5-c6d7e8f90a1b',
            ...     from_='+15555550188',
            ...     metadata={'crmId': 'lead_8812'},
            ... )
            >>> print(call.id, call.status)
        """
        body = _create_body(to, agent_id, from_, context, metadata)
        data = self._http.request(
            method="POST", path="/calls", body=body, idempotency_key=idempotency_key
        )
        return _parse(Call, data)

    def list(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[EnumLike] = None,
        direction: Optional[EnumLike] = None,
        kind: Optional[EnumLike] = None,
        agent_id: Optional[str] = None,
        to: Optional[str] = None,
        from_: Optional[str] = None,
    ) -> CallListResponse:
        """List calls in the workspace, newest first. Requires the
        ``calls:read`` scope.

        Live calls are reconciled before they are returned, so a ring that
        ran past its deadline shows as ``no_answer``.

        Args:
            limit: Page size, 1-100 (default 50).
            offset: Rows to skip (default 0).
            status: One :class:`~sendly.types.CallStatus` value.
            direction: ``inbound`` or ``outbound``.
            kind: ``pstn`` or ``internal``.
            agent_id: Only calls handled by this agent.
            to: Exact E.164 match on the called number.
            from_: Exact E.164 match on the calling number.

        Example:
            >>> page = client.calls.list(status='completed', limit=20)
            >>> for call in page.data:
            ...     print(call.id, call.duration_secs, call.credits_charged)
            >>> if page.pagination.has_more:
            ...     page = client.calls.list(status='completed', limit=20, offset=20)
        """
        params = _list_params(limit, offset, status, direction, kind, agent_id, to, from_)
        data = self._http.request(
            method="GET", path="/calls", params=params if params else None
        )
        return _parse(CallListResponse, data)

    def get(self, id: str) -> Call:
        """Fetch one call. Requires the ``calls:read`` scope.

        Agent-handled calls carry ``transcript`` (a list, empty if nothing
        was said); on every other call it is None. A call from another
        workspace raises ``call_not_found``.

        Args:
            id: Call identifier.
        """
        _require(id, "id")
        data = self._http.request(method="GET", path=f"/calls/{quote(id, safe='')}")
        return _parse(Call, data)

    def hangup(self, id: str, *, idempotency_key: Optional[str] = None) -> Call:
        """End a call. Requires the ``calls:write`` scope and a live API key.

        A ``ringing`` call becomes ``cancelled`` (``hangup_class``
        ``caller_cancelled``), an ``active`` one ``completed``
        (``hangup_class`` ``normal``). A call that has already ended is
        returned unchanged, so this is safe to retry.

        Args:
            id: Call identifier.
            idempotency_key: Optional key sent as the Idempotency-Key header;
                generated automatically when omitted.
        """
        _require(id, "id")
        data = self._http.request(
            method="POST",
            path=f"/calls/{quote(id, safe='')}/hangup",
            body={},
            idempotency_key=idempotency_key,
        )
        return _parse(Call, data)

    def recording(self, id: str) -> CallRecording:
        """Fetch where to download a call's recording. Requires the
        ``calls:read`` scope.

        ``url`` and ``expires_at`` are set only while ``status`` is ``ready``;
        the link is signed and valid for 5 minutes, so fetch it right before
        downloading. Recordings are Ogg/Opus; agent calls are recorded
        dual-channel (caller left, agent right). ``status`` is ``none`` when
        nothing was recorded (recording off, or the call was never answered).

        Args:
            id: Call identifier.

        Example:
            >>> rec = client.calls.recording(call.id)
            >>> if rec.status == 'ready':
            ...     audio = httpx.get(rec.url).content
        """
        _require(id, "id")
        data = self._http.request(method="GET", path=f"/calls/{quote(id, safe='')}/recording")
        return _parse(CallRecording, data)


class AsyncCallsResource:
    """Voice calls API resource (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def create(
        self,
        to: str,
        agent_id: str,
        *,
        from_: Optional[str] = None,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Call:
        """Place a phone call handled by one of your AI agents.
        See :meth:`CallsResource.create`."""
        body = _create_body(to, agent_id, from_, context, metadata)
        data = await self._http.request(
            method="POST", path="/calls", body=body, idempotency_key=idempotency_key
        )
        return _parse(Call, data)

    async def list(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[EnumLike] = None,
        direction: Optional[EnumLike] = None,
        kind: Optional[EnumLike] = None,
        agent_id: Optional[str] = None,
        to: Optional[str] = None,
        from_: Optional[str] = None,
    ) -> CallListResponse:
        """List calls, newest first. See :meth:`CallsResource.list`."""
        params = _list_params(limit, offset, status, direction, kind, agent_id, to, from_)
        data = await self._http.request(
            method="GET", path="/calls", params=params if params else None
        )
        return _parse(CallListResponse, data)

    async def get(self, id: str) -> Call:
        """Fetch one call. See :meth:`CallsResource.get`."""
        _require(id, "id")
        data = await self._http.request(method="GET", path=f"/calls/{quote(id, safe='')}")
        return _parse(Call, data)

    async def hangup(self, id: str, *, idempotency_key: Optional[str] = None) -> Call:
        """End a call. See :meth:`CallsResource.hangup`."""
        _require(id, "id")
        data = await self._http.request(
            method="POST",
            path=f"/calls/{quote(id, safe='')}/hangup",
            body={},
            idempotency_key=idempotency_key,
        )
        return _parse(Call, data)

    async def recording(self, id: str) -> CallRecording:
        """Fetch where to download a call's recording.
        See :meth:`CallsResource.recording`."""
        _require(id, "id")
        data = await self._http.request(
            method="GET", path=f"/calls/{quote(id, safe='')}/recording"
        )
        return _parse(CallRecording, data)


def _require(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} is required")


def _value(value: Optional[EnumLike]) -> Optional[str]:
    if isinstance(value, Enum):
        return str(value.value)
    return value


def _create_body(
    to: str,
    agent_id: str,
    from_: Optional[str],
    context: Optional[str],
    metadata: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    _require(to, "to")
    _require(agent_id, "agent_id")
    body: Dict[str, Any] = {"to": to, "agentId": agent_id}
    if from_ is not None:
        body["from"] = from_
    if context is not None:
        body["context"] = context
    if metadata is not None:
        if not isinstance(metadata, dict):
            raise ValidationError("'metadata' must be a dict of string keys to string values")
        body["metadata"] = metadata
    return body


def _list_params(
    limit: Optional[int],
    offset: Optional[int],
    status: Optional[EnumLike],
    direction: Optional[EnumLike],
    kind: Optional[EnumLike],
    agent_id: Optional[str],
    to: Optional[str],
    from_: Optional[str],
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    optional: Dict[str, Any] = {
        "limit": limit,
        "offset": offset,
        "status": _value(status),
        "direction": _value(direction),
        "kind": _value(kind),
        "agentId": agent_id,
        "to": to,
        "from": from_,
    }
    for key, value in optional.items():
        if value is not None:
            params[key] = value
    return params


def _parse(model: Type[_M], data: Any) -> _M:
    try:
        return model.model_validate(data)
    except PydanticValidationError as e:
        raise _invalid_response(e) from e


def _invalid_response(e: PydanticValidationError) -> SendlyError:
    """Wrap a pydantic schema error as a SendlyError, matching the SDK's idiom."""
    return SendlyError(
        message=f"Invalid API response format: {e}",
        code="invalid_response",
        status_code=200,
    )
