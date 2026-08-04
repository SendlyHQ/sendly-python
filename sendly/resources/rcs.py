"""
RCS Resource - Discover agents, pre-flight recipient capability

RCS is a first-class Sendly channel: rich cards, suggestion chips, and
branded, verified-sender messaging on Android, sent via
``client.messages.send(channel='rcs', ...)``.

Sending as your brand requires an RCS agent - the verified sender identity
recipients see. Agents are registered per workspace through carrier review
(contact support to register one for your brand); once an agent is
``sendable``, no other setup is needed.

Not every recipient can receive RCS. Text messages fall back to SMS
automatically by default (the send response discloses it via
``channel='sms'`` and ``fell_back_to='sms'``); use ``capability()`` to check
a recipient ahead of time. RCS requires a live API key - delivery is never
sandbox-simulated.
"""

from typing import Any, Dict, Optional

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError
from ..types import RcsAgentListResponse, RcsCapability
from ..utils.http import AsyncHttpClient, HttpClient
from ..utils.validation import validate_phone_number


class RcsAgentsResource:
    """Agents sub-resource for listing your RCS agents (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def list(self) -> RcsAgentListResponse:
        """List your RCS agents.

        Returns the agents registered on your workspace, newest first. An
        empty list means no agent is registered yet - contact support to
        register one for your brand.

        Example:
            >>> for agent in client.rcs.agents.list().agents:
            ...     print(agent.name, agent.status, agent.sendable)
        """
        data = self._http.request(method="GET", path="/rcs/agents")
        try:
            return RcsAgentListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class RcsResource:
    """RCS API resource (sync)

    Example:
        >>> # 1. Find your sendable agent
        >>> agents = client.rcs.agents.list().agents
        >>> agent = next((a for a in agents if a.sendable), None)
        >>> # 2. Optionally pre-flight the recipient
        >>> check = client.rcs.capability(to='+15551234567')
        >>> # 3. Send - text falls back to SMS for non-RCS recipients
        >>> message = client.messages.send(
        ...     channel='rcs',
        ...     to='+15551234567',
        ...     text='Your table is ready!',
        ... )
    """

    def __init__(self, http: HttpClient):
        self._http = http
        self.agents = RcsAgentsResource(http)

    def capability(self, to: str, agent_id: Optional[str] = None) -> RcsCapability:
        """Check whether a recipient can receive RCS.

        Runs a live carrier-backed capability probe, so it requires a live
        API key. You don't have to call this before sending - text sends
        probe capability themselves and fall back to SMS - but it's useful
        to decide between a rich card and plain text up front (cards don't
        fall back).

        Args:
            to: The recipient's number, in E.164 format.
            agent_id: The agent to check as. Optional when your workspace
                has exactly one agent; required when it has several.

        Example:
            >>> check = client.rcs.capability(to='+15551234567')
            >>> if not check.capable:
            ...     pass  # send text (falls back to SMS) instead of a card
        """
        validate_phone_number(to)
        data = self._http.request(
            method="GET", path="/rcs/capability", params=_capability_params(to, agent_id)
        )
        try:
            return RcsCapability(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class AsyncRcsAgentsResource:
    """Agents sub-resource for listing your RCS agents (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list(self) -> RcsAgentListResponse:
        """List your RCS agents. See :meth:`RcsAgentsResource.list`."""
        data = await self._http.request(method="GET", path="/rcs/agents")
        try:
            return RcsAgentListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class AsyncRcsResource:
    """RCS API resource (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http
        self.agents = AsyncRcsAgentsResource(http)

    async def capability(
        self, to: str, agent_id: Optional[str] = None
    ) -> RcsCapability:
        """Check whether a recipient can receive RCS.
        See :meth:`RcsResource.capability`."""
        validate_phone_number(to)
        data = await self._http.request(
            method="GET", path="/rcs/capability", params=_capability_params(to, agent_id)
        )
        try:
            return RcsCapability(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


def _capability_params(to: str, agent_id: Optional[str]) -> Dict[str, Any]:
    params: Dict[str, Any] = {"to": to}
    if agent_id:
        params["agentId"] = agent_id
    return params


def _invalid_response(e: PydanticValidationError) -> SendlyError:
    """Wrap a pydantic schema error as a SendlyError, matching the SDK's idiom."""
    return SendlyError(
        message=f"Invalid API response format: {e}",
        code="invalid_response",
        status_code=200,
    )
