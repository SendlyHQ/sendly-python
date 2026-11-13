"""
Voice Resource - Configure how your numbers handle phone calls

Everything a phone call depends on can be set up from code: switch voice on
for a workspace number and choose how it answers (ringing your team in the
dashboard, or one of your AI agents), register the emergency address a number
needs before it can place calls, and create, edit and remove the AI agents
that talk to callers.

    client.voice.numbers   list, get, update, register_emergency_address
    client.voice.agents    list, create, get, update, test, delete
    client.voice.voices    list

Reads need an API key with the ``calls:read`` scope, writes ``calls:write``
and a live key (``live_key_required`` otherwise). In a team workspace,
changing a number or its emergency address needs an owner or admin role, and
so does managing agents, because each agent holds its own key for sending
texts (``forbidden`` otherwise). Voice is enabled workspace by workspace;
until it is enabled for yours every method raises ``SendlyError`` with code
``voice_not_enabled`` (HTTP 404).

These settings change how real phone calls to your numbers are answered.
"""

from enum import Enum
from typing import Any, Dict, Optional, Union
from urllib.parse import quote

from pydantic import ValidationError as PydanticValidationError

from ..errors import ValidationError
from ..types import (
    DeletedVoiceAgent,
    VoiceAgent,
    VoiceAgentConnectionInput,
    VoiceAgentCustomLlmConnectionInput,
    VoiceAgentListResponse,
    VoiceAgentSipConnectionInput,
    VoiceAgentTest,
    VoiceAgentTools,
    VoiceAgentWebsocketConnectionInput,
    VoiceListResponse,
    VoiceNumber,
    VoiceNumberListResponse,
)
from ..utils.http import AsyncHttpClient, HttpClient
from .calls import EnumLike, _parse, _require, _value

VoiceAgentToolsLike = Union[VoiceAgentTools, Dict[str, Any]]


class VoiceNumbersResource:
    """Voice settings on workspace numbers (sync)

    Example:
        >>> number = client.voice.numbers.update(
        ...     '+15555550188',
        ...     voice_enabled=True,
        ...     voice_mode='agent',
        ...     agent_id='3c4d5e6f-7081-4293-a4b5-c6d7e8f90a1b',
        ... )
        >>> print(number.voice_mode)  # 'agent'
    """

    def __init__(self, http: HttpClient):
        self._http = http

    def list(self) -> VoiceNumberListResponse:
        """List the workspace's active numbers with their voice settings.
        Requires the ``calls:read`` scope.

        Example:
            >>> for n in client.voice.numbers.list().data:
            ...     print(n.phone_number, n.voice_mode, n.agent_id)
        """
        data = self._http.request(method="GET", path="/voice/numbers")
        return _parse(VoiceNumberListResponse, data)

    def get(self, number: str) -> VoiceNumber:
        """Fetch one number's voice settings. Requires the ``calls:read``
        scope.

        Args:
            number: The number's id or its E.164 phone number, for example
                ``'+15555550188'``.

        Raises:
            ValidationError: ``number`` is empty.
            SendlyError: With ``code`` ``number_not_found`` when it is not an
                active number in this workspace.
        """
        _require(number, "number")
        data = self._http.request(method="GET", path=_number_path(number))
        return _parse(VoiceNumber, data)

    def update(
        self,
        number: str,
        *,
        voice_enabled: Optional[bool] = None,
        voice_mode: Optional[EnumLike] = None,
        agent_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> VoiceNumber:
        """Change how a number handles phone calls. Requires the
        ``calls:write`` scope and a live API key.

        Only the arguments you pass are sent; the rest keep their current
        value. Voice off always means ``voice_mode`` ``none``. Without
        ``voice_enabled``, ``voice_mode='ring_dashboard'`` or ``'agent'``
        switches voice on and ``voice_mode='none'`` switches it off;
        ``voice_enabled=False`` switches voice off whatever the mode.
        Switching voice on without a mode, or with ``none``, rings your team
        in the dashboard (``ring_dashboard``). ``agent`` needs an enabled
        agent, passed as ``agent_id`` or already set on the number.

        Args:
            number: The number's id or its E.164 phone number.
            voice_enabled: Switch voice on or off. Turning it on connects the
                number for calls before the change is saved.
            voice_mode: ``none``, ``ring_dashboard`` or ``agent`` (see
                :class:`~sendly.types.VoiceMode`). On its own it switches
                voice on (``ring_dashboard``, ``agent``) or off (``none``).
            agent_id: The agent that answers when ``voice_mode`` is ``agent``.
            idempotency_key: Optional key sent as the Idempotency-Key header.

        Raises:
            ValidationError: ``number`` is empty.
            SendlyError: With ``code`` ``number_not_found``,
                ``invalid_voice_mode``, ``agent_required`` (agent mode with no
                agent), ``agent_not_found``, ``agent_disabled`` (turn the agent
                on first), ``voice_attach_failed`` (retry shortly),
                ``voice_unavailable`` or ``voice_not_enabled``.

        Example:
            >>> client.voice.numbers.update('+15555550188', voice_mode='ring_dashboard')
            >>> client.voice.numbers.update('+15555550188', voice_enabled=False)
        """
        _require(number, "number")
        data = self._http.request(
            method="PATCH",
            path=_number_path(number),
            body=_number_body(voice_enabled, voice_mode, agent_id),
            idempotency_key=idempotency_key,
        )
        return _parse(VoiceNumber, data)

    def register_emergency_address(
        self,
        number: str,
        *,
        street: str,
        city: str,
        state: str,
        zip: str,
        unit: Optional[str] = None,
        country: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> VoiceNumber:
        """Register the emergency address for a number. Requires the
        ``calls:write`` scope and a live API key.

        A number needs one before it can place calls in the US and Canada
        (``client.calls.create`` raises ``e911_required`` otherwise). The
        first registration adds 1.50 USD a month to the number's cost;
        replacing the address later does not add it again. Only US and
        Canadian numbers take one.

        Args:
            number: The number's id or its E.164 phone number.
            street: Street address.
            city: City.
            state: State or province code, for example ``TX``.
            zip: A five-digit ZIP code (or ZIP+4) for a US address, a postal
                code like ``A1A 1A1`` for a Canadian one.
            unit: Optional suite, apartment or floor.
            country: ``US`` (the default) or ``CA``.
            idempotency_key: Optional key sent as the Idempotency-Key header;
                generated automatically when omitted.

        Raises:
            ValidationError: ``street``, ``city``, ``state`` or ``zip`` is
                empty or not a string, or the API answered
                ``invalid_request`` (a ``unit`` or ``country`` that is not a
                string).
            SendlyError: With ``code`` ``invalid_address`` (HTTP 400 when a
                field is wrong; HTTP 422 when the address could not be
                validated, with the closest match in
                ``e.response.model_extra['suggested']``),
                ``e911_not_applicable`` (not a US or Canadian number),
                ``carrier_refused``, ``number_not_found`` or
                ``voice_not_enabled``.

        Example:
            >>> number = client.voice.numbers.register_emergency_address(
            ...     '+15555550188',
            ...     street='500 Example Ave',
            ...     unit='Suite 2',
            ...     city='Austin',
            ...     state='TX',
            ...     zip='78701',
            ... )
            >>> print(number.emergency_address.status)
        """
        _require(number, "number")
        body = _address_body(street, unit, city, state, zip, country)
        data = self._http.request(
            method="POST",
            path=_number_path(number, "/emergency-address"),
            body=body,
            idempotency_key=idempotency_key,
        )
        return _parse(VoiceNumber, data)


class VoiceAgentsResource:
    """AI agents that answer and place phone calls (sync)

    Example:
        >>> agent = client.voice.agents.create(
        ...     name='Front desk',
        ...     voice='ashley',
        ...     greeting='Thanks for calling Acme, how can I help?',
        ... )
        >>> print(agent.id, agent.voice_label, agent.can_send_sms)
    """

    def __init__(self, http: HttpClient):
        self._http = http

    def list(self) -> VoiceAgentListResponse:
        """List the workspace's AI agents. Requires the ``calls:read`` scope.

        Example:
            >>> for agent in client.voice.agents.list().data:
            ...     print(agent.name, agent.enabled, agent.calls_handled)
        """
        data = self._http.request(method="GET", path="/voice/agents")
        return _parse(VoiceAgentListResponse, data)

    def create(
        self,
        name: str,
        *,
        enabled: Optional[bool] = None,
        voice: Optional[str] = None,
        language: Optional[str] = None,
        greeting: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[VoiceAgentToolsLike] = None,
        kind: Optional[EnumLike] = None,
        connection: Optional[VoiceAgentConnectionInput] = None,
        idempotency_key: Optional[str] = None,
    ) -> VoiceAgent:
        """Create an AI agent. Requires the ``calls:write`` scope and a live
        API key.

        The agent answers real callers once a number points at it
        (:meth:`VoiceNumbersResource.update` with ``voice_mode='agent'``) and
        talks on the calls you place with ``client.calls.create``. Each agent
        gets its own key for sending texts from your workspace;
        ``can_send_sms`` says whether it has one. A workspace holds up to 20
        agents.

        By default Sendly writes the agent's replies from its
        ``instructions`` (``kind='sendly'``). To answer with your own agent
        instead, pass another ``kind`` and its ``connection``: ``custom_llm``
        (Sendly listens and speaks, and your chat completions endpoint writes
        each reply), ``sip`` (Sendly connects the caller to your SIP address)
        or ``websocket`` (Sendly streams the call audio to your ``wss://``
        server). Your own agents need the workspace's bring-your-own-agent
        feature, which support switches on. The response to creating one
        carries ``signing_secret``, which Sendly uses to sign every request to
        your agent (``X-Sendly-Signature: t=<unix>,v1=<hex HMAC-SHA256>``).
        Save it now; it is never shown again.

        Args:
            name: 1-80 characters.
            enabled: Defaults to True. A disabled agent takes no calls.
            voice: A voice id from :meth:`VoicesResource.list`; an unknown id
                gets the default voice.
            language: Language tag, default ``en-US``.
            greeting: Up to 500 characters, said when the call connects.
            instructions: Up to 4000 characters on what the business does and
                how the agent should handle callers.
            tools: A :class:`~sendly.types.VoiceAgentTools` or a dict.
                ``send_sms`` (default True) lets the agent text the other
                party. ``transfer_to`` is the number the agent transfers a
                caller to when asked for a person, and the one
                ``client.calls.transfer`` uses when given no number.
            kind: ``sendly`` (the default), ``custom_llm``, ``sip`` or
                ``websocket`` (see :class:`~sendly.types.VoiceAgentKind`).
            connection: How Sendly reaches your own agent, matching ``kind``;
                required for every kind but ``sendly``. A
                :class:`~sendly.types.VoiceAgentCustomLlmConnectionInput`,
                :class:`~sendly.types.VoiceAgentSipConnectionInput`,
                :class:`~sendly.types.VoiceAgentWebsocketConnectionInput` or a
                dict (snake_case or camelCase keys). It is sent as given: a
                key you leave out is not sent, and None is sent as null.
                Hosts must resolve to public internet addresses.
            idempotency_key: Optional key sent as the Idempotency-Key header;
                generated automatically when omitted.

        Raises:
            ValidationError: ``name`` is empty, ``tools`` is not a
                VoiceAgentTools or dict, ``connection`` is not one of the
                connection inputs or a dict, or the API answered
                ``invalid_request`` (for a ``connection`` that is missing or
                breaks a rule, the message reads
                ``connection.<field>: <reason>``).
            SendlyError: With ``code`` ``agent_limit`` (HTTP 409),
                ``byo_agents_not_enabled`` (HTTP 403, a ``kind`` other than
                ``sendly`` while the workspace's bring-your-own-agent feature
                is off), ``forbidden`` or ``voice_not_enabled``.

        Example:
            >>> agent = client.voice.agents.create(
            ...     'Support line',
            ...     kind='websocket',
            ...     connection={'url': 'wss://agent.example.com/calls', 'auth_token': 'tok_123'},
            ... )
            >>> secret = agent.signing_secret  # shown only now
        """
        _require(name, "name")
        body = _agent_body(
            name, enabled, voice, language, greeting, instructions, tools, kind, connection
        )
        data = self._http.request(
            method="POST", path="/voice/agents", body=body, idempotency_key=idempotency_key
        )
        return _parse(VoiceAgent, data)

    def get(self, id: str) -> VoiceAgent:
        """Fetch one agent. Requires the ``calls:read`` scope.

        Args:
            id: Agent identifier.

        Raises:
            ValidationError: ``id`` is empty.
            SendlyError: With ``code`` ``agent_not_found``.
        """
        _require(id, "id")
        data = self._http.request(method="GET", path=_agent_path(id))
        return _parse(VoiceAgent, data)

    def update(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        enabled: Optional[bool] = None,
        voice: Optional[str] = None,
        language: Optional[str] = None,
        greeting: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[VoiceAgentToolsLike] = None,
        kind: Optional[EnumLike] = None,
        connection: Optional[VoiceAgentConnectionInput] = None,
        rotate_signing_secret: Optional[bool] = None,
        idempotency_key: Optional[str] = None,
    ) -> VoiceAgent:
        """Edit an agent. Requires the ``calls:write`` scope and a live API
        key.

        Only the arguments you pass are sent; the rest keep their current
        value. ``tools`` may be partial: keys you leave out keep their current
        value, and ``transfer_to=None`` clears the transfer number.

        With the same ``kind``, ``connection`` is merged into the saved one:
        fields you leave out keep their values. Changing ``kind`` to one of
        your own needs that kind's ``connection``. Switching a ``sendly``
        agent to one of your own kinds makes a signing secret, returned once
        in ``signing_secret``; switching back to ``sendly`` removes the
        connection and the signing secret.

        Args:
            id: Agent identifier.
            rotate_signing_secret: True makes a new signing secret for your
                own agent, returned once in ``signing_secret`` (save it now; it
                is never shown again). The old secret stops working at once.
                Only True is sent; False or None sends nothing.
            idempotency_key: Optional key sent as the Idempotency-Key header.

        See :meth:`create` for the other arguments.

        Raises:
            ValidationError: ``id`` is empty, ``tools`` is not a
                VoiceAgentTools or dict, ``connection`` is not one of the
                connection inputs or a dict, or the API answered
                ``invalid_request`` (a ``connection`` that breaks a rule or is
                missing when ``kind`` changes, or ``rotate_signing_secret`` on
                a ``sendly`` agent).
            SendlyError: With ``code`` ``agent_not_found``,
                ``byo_agents_not_enabled`` (HTTP 403) or ``forbidden``.

        Example:
            >>> agent = client.voice.agents.update(agent.id, rotate_signing_secret=True)
            >>> secret = agent.signing_secret  # shown only now
        """
        _require(id, "id")
        body = _agent_body(
            name,
            enabled,
            voice,
            language,
            greeting,
            instructions,
            tools,
            kind,
            connection,
            rotate_signing_secret,
        )
        data = self._http.request(
            method="PATCH", path=_agent_path(id), body=body, idempotency_key=idempotency_key
        )
        return _parse(VoiceAgent, data)

    def test(
        self,
        id: str,
        *,
        kind: Optional[EnumLike] = None,
        connection: Optional[VoiceAgentConnectionInput] = None,
        instructions: Optional[str] = None,
    ) -> VoiceAgentTest:
        """Test your own agent's connection the way a call would reach it,
        without placing one. Requires the ``calls:write`` scope and a live API
        key.

        ``custom_llm`` gets a signed, streamed chat completion with a test
        message. ``websocket`` gets a signed connection with ``connected``, a
        ``start`` carrying ``test: true``, half a second of silence and a
        ``stop`` with reason ``test_finished``. ``sip`` gets an ``OPTIONS``
        request, answered with the saved credentials if the server asks; a SIP
        server answering shows the address and credentials work, not which
        agent picks up.

        Pass ``connection`` to test settings before saving them. A workspace
        can run 10 tests a minute. A failed test is still a successful
        request: check ``ok`` on the result.

        Args:
            id: Agent identifier.
            kind: ``custom_llm``, ``sip`` or ``websocket``: the kind of the
                settings in ``connection``. Defaults to the agent's own kind.
                Needed to test settings of another kind, such as on a
                ``sendly`` agent before switching it.
            connection: Settings to test instead of the saved ones, in the
                same shapes as :meth:`create`. Nothing is saved. For the
                agent's own kind, a secret left out is taken from the saved
                connection, while the host stays the same.
            instructions: For ``custom_llm``: the system prompt to send.
                Defaults to the agent's instructions.

        Raises:
            ValidationError: ``id`` is empty, ``connection`` is not one of the
                connection inputs or a dict, or the API answered
                ``invalid_request`` (a ``sendly`` agent and no ``kind``, or a
                ``connection`` that breaks a rule).
            SendlyError: With ``code`` ``byo_agents_not_enabled`` (HTTP 403),
                ``live_key_required`` (HTTP 403) or ``agent_not_found``
                (HTTP 404).
            RateLimitError: After 10 tests in a minute (HTTP 429).

        Example:
            >>> result = client.voice.agents.test(agent.id)
            >>> if not result.ok:
            ...     print(result.outcome, result.message)
            >>> client.voice.agents.test(
            ...     agent.id,
            ...     connection={'uri': 'sip:+15125550100@sip.example.com', 'transport': 'tls'},
            ... )
        """
        _require(id, "id")
        body = _test_body(kind, connection, instructions)
        data = self._http.request(
            method="POST", path=f"{_agent_path(id)}/test", body=body, auto_idempotency_key=False
        )
        return _parse(VoiceAgentTest, data)

    def delete(self, id: str, *, idempotency_key: Optional[str] = None) -> DeletedVoiceAgent:
        """Delete an agent and revoke its sending key. Requires the
        ``calls:write`` scope and a live API key.

        Refused while a number still points at the agent: the error has
        ``code`` ``agent_in_use`` (HTTP 409) and lists those numbers in
        ``e.response.model_extra['numbers']``. Point them at another agent or
        back to the team first.

        Args:
            id: Agent identifier.
            idempotency_key: Optional key sent as the Idempotency-Key header.

        Example:
            >>> try:
            ...     client.voice.agents.delete(agent.id)
            ... except SendlyError as e:
            ...     if e.code == 'agent_in_use':
            ...         for number in e.response.model_extra['numbers']:
            ...             client.voice.numbers.update(number, voice_mode='ring_dashboard')
        """
        _require(id, "id")
        data = self._http.request(
            method="DELETE", path=_agent_path(id), idempotency_key=idempotency_key
        )
        return _parse(DeletedVoiceAgent, data)


class VoicesResource:
    """Voices an agent can speak with (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def list(self) -> VoiceListResponse:
        """List the voices available to agents. Requires the ``calls:read``
        scope. Pass a voice's ``id`` as ``voice`` when creating or editing an
        agent.

        Example:
            >>> for v in client.voice.voices.list().data:
            ...     print(v.id, v.label, v.language)
        """
        data = self._http.request(method="GET", path="/voice/voices")
        return _parse(VoiceListResponse, data)


class VoiceResource:
    """Voice configuration API resource (sync)

    Example:
        >>> agent = client.voice.agents.create(name='Front desk', voice='ashley')
        >>> client.voice.numbers.register_emergency_address(
        ...     '+15555550188', street='500 Example Ave', city='Austin', state='TX', zip='78701'
        ... )
        >>> client.voice.numbers.update(
        ...     '+15555550188', voice_enabled=True, voice_mode='agent', agent_id=agent.id
        ... )
    """

    def __init__(self, http: HttpClient):
        self._http = http
        self.numbers = VoiceNumbersResource(http)
        self.agents = VoiceAgentsResource(http)
        self.voices = VoicesResource(http)


class AsyncVoiceNumbersResource:
    """Voice settings on workspace numbers (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list(self) -> VoiceNumberListResponse:
        """List numbers with their voice settings.
        See :meth:`VoiceNumbersResource.list`."""
        data = await self._http.request(method="GET", path="/voice/numbers")
        return _parse(VoiceNumberListResponse, data)

    async def get(self, number: str) -> VoiceNumber:
        """Fetch one number's voice settings. See :meth:`VoiceNumbersResource.get`."""
        _require(number, "number")
        data = await self._http.request(method="GET", path=_number_path(number))
        return _parse(VoiceNumber, data)

    async def update(
        self,
        number: str,
        *,
        voice_enabled: Optional[bool] = None,
        voice_mode: Optional[EnumLike] = None,
        agent_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> VoiceNumber:
        """Change how a number handles phone calls.
        See :meth:`VoiceNumbersResource.update`."""
        _require(number, "number")
        data = await self._http.request(
            method="PATCH",
            path=_number_path(number),
            body=_number_body(voice_enabled, voice_mode, agent_id),
            idempotency_key=idempotency_key,
        )
        return _parse(VoiceNumber, data)

    async def register_emergency_address(
        self,
        number: str,
        *,
        street: str,
        city: str,
        state: str,
        zip: str,
        unit: Optional[str] = None,
        country: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> VoiceNumber:
        """Register the emergency address for a number.
        See :meth:`VoiceNumbersResource.register_emergency_address`."""
        _require(number, "number")
        body = _address_body(street, unit, city, state, zip, country)
        data = await self._http.request(
            method="POST",
            path=_number_path(number, "/emergency-address"),
            body=body,
            idempotency_key=idempotency_key,
        )
        return _parse(VoiceNumber, data)


class AsyncVoiceAgentsResource:
    """AI agents that answer and place phone calls (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list(self) -> VoiceAgentListResponse:
        """List agents. See :meth:`VoiceAgentsResource.list`."""
        data = await self._http.request(method="GET", path="/voice/agents")
        return _parse(VoiceAgentListResponse, data)

    async def create(
        self,
        name: str,
        *,
        enabled: Optional[bool] = None,
        voice: Optional[str] = None,
        language: Optional[str] = None,
        greeting: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[VoiceAgentToolsLike] = None,
        kind: Optional[EnumLike] = None,
        connection: Optional[VoiceAgentConnectionInput] = None,
        idempotency_key: Optional[str] = None,
    ) -> VoiceAgent:
        """Create an AI agent. See :meth:`VoiceAgentsResource.create`."""
        _require(name, "name")
        body = _agent_body(
            name, enabled, voice, language, greeting, instructions, tools, kind, connection
        )
        data = await self._http.request(
            method="POST", path="/voice/agents", body=body, idempotency_key=idempotency_key
        )
        return _parse(VoiceAgent, data)

    async def get(self, id: str) -> VoiceAgent:
        """Fetch one agent. See :meth:`VoiceAgentsResource.get`."""
        _require(id, "id")
        data = await self._http.request(method="GET", path=_agent_path(id))
        return _parse(VoiceAgent, data)

    async def update(
        self,
        id: str,
        *,
        name: Optional[str] = None,
        enabled: Optional[bool] = None,
        voice: Optional[str] = None,
        language: Optional[str] = None,
        greeting: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[VoiceAgentToolsLike] = None,
        kind: Optional[EnumLike] = None,
        connection: Optional[VoiceAgentConnectionInput] = None,
        rotate_signing_secret: Optional[bool] = None,
        idempotency_key: Optional[str] = None,
    ) -> VoiceAgent:
        """Edit an agent. See :meth:`VoiceAgentsResource.update`."""
        _require(id, "id")
        body = _agent_body(
            name,
            enabled,
            voice,
            language,
            greeting,
            instructions,
            tools,
            kind,
            connection,
            rotate_signing_secret,
        )
        data = await self._http.request(
            method="PATCH", path=_agent_path(id), body=body, idempotency_key=idempotency_key
        )
        return _parse(VoiceAgent, data)

    async def test(
        self,
        id: str,
        *,
        kind: Optional[EnumLike] = None,
        connection: Optional[VoiceAgentConnectionInput] = None,
        instructions: Optional[str] = None,
    ) -> VoiceAgentTest:
        """Test an agent's connection. See :meth:`VoiceAgentsResource.test`."""
        _require(id, "id")
        body = _test_body(kind, connection, instructions)
        data = await self._http.request(
            method="POST", path=f"{_agent_path(id)}/test", body=body, auto_idempotency_key=False
        )
        return _parse(VoiceAgentTest, data)

    async def delete(
        self, id: str, *, idempotency_key: Optional[str] = None
    ) -> DeletedVoiceAgent:
        """Delete an agent and revoke its sending key.
        See :meth:`VoiceAgentsResource.delete`."""
        _require(id, "id")
        data = await self._http.request(
            method="DELETE", path=_agent_path(id), idempotency_key=idempotency_key
        )
        return _parse(DeletedVoiceAgent, data)


class AsyncVoicesResource:
    """Voices an agent can speak with (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list(self) -> VoiceListResponse:
        """List the voices available to agents. See :meth:`VoicesResource.list`."""
        data = await self._http.request(method="GET", path="/voice/voices")
        return _parse(VoiceListResponse, data)


class AsyncVoiceResource:
    """Voice configuration API resource (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http
        self.numbers = AsyncVoiceNumbersResource(http)
        self.agents = AsyncVoiceAgentsResource(http)
        self.voices = AsyncVoicesResource(http)


def _number_path(number: str, suffix: str = "") -> str:
    return f"/voice/numbers/{quote(number, safe='')}{suffix}"


def _agent_path(id: str) -> str:
    return f"/voice/agents/{quote(id, safe='')}"


def _number_body(
    voice_enabled: Optional[bool],
    voice_mode: Optional[EnumLike],
    agent_id: Optional[str],
) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if voice_enabled is not None:
        body["voiceEnabled"] = voice_enabled
    if voice_mode is not None:
        body["voiceMode"] = _value(voice_mode)
    if agent_id is not None:
        body["agentId"] = agent_id
    return body


def _address_body(
    street: str,
    unit: Optional[str],
    city: str,
    state: str,
    zip: str,
    country: Optional[str],
) -> Dict[str, Any]:
    _require(street, "street")
    _require(city, "city")
    _require(state, "state")
    _require(zip, "zip")
    body: Dict[str, Any] = {"street": street}
    if unit is not None:
        body["unit"] = unit
    body.update({"city": city, "state": state, "zip": zip})
    if country is not None:
        body["country"] = country
    return body


def _agent_body(
    name: Optional[str],
    enabled: Optional[bool],
    voice: Optional[str],
    language: Optional[str],
    greeting: Optional[str],
    instructions: Optional[str],
    tools: Optional[VoiceAgentToolsLike],
    kind: Optional[EnumLike] = None,
    connection: Optional[VoiceAgentConnectionInput] = None,
    rotate_signing_secret: Optional[bool] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    optional: Dict[str, Any] = {
        "name": name,
        "enabled": enabled,
        "voice": voice,
        "language": language,
        "greeting": greeting,
        "instructions": instructions,
    }
    for key, value in optional.items():
        if value is not None:
            body[key] = value
    if tools is not None:
        body["tools"] = _tools_body(tools)
    if kind is not None:
        body["kind"] = _value(kind)
    if connection is not None:
        body["connection"] = _connection_body(connection)
    if rotate_signing_secret is True:
        body["rotateSigningSecret"] = True
    return body


def _test_body(
    kind: Optional[EnumLike],
    connection: Optional[VoiceAgentConnectionInput],
    instructions: Optional[str],
) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if kind is not None:
        body["kind"] = _value(kind)
    if connection is not None:
        body["connection"] = _connection_body(connection)
    if instructions is not None:
        body["instructions"] = instructions
    return body


_CONNECTION_KEYS = {
    "base_url": "baseUrl",
    "api_key": "apiKey",
    "media_encryption": "mediaEncryption",
    "audio_format": "audioFormat",
    "auth_token": "authToken",
    "custom_parameters": "customParameters",
}

_CONNECTION_INPUTS = (
    VoiceAgentCustomLlmConnectionInput,
    VoiceAgentSipConnectionInput,
    VoiceAgentWebsocketConnectionInput,
)


def _connection_body(connection: VoiceAgentConnectionInput) -> Dict[str, Any]:
    if isinstance(connection, _CONNECTION_INPUTS):
        raw = connection.model_dump(by_alias=True, exclude_unset=True)
    elif isinstance(connection, dict):
        raw = {_CONNECTION_KEYS.get(str(key), str(key)): value for key, value in connection.items()}
    else:
        raise ValidationError(
            "'connection' must be a dict or a VoiceAgentCustomLlmConnectionInput, "
            "VoiceAgentSipConnectionInput or VoiceAgentWebsocketConnectionInput"
        )
    return {key: _value(value) if isinstance(value, Enum) else value for key, value in raw.items()}


def _tools_body(tools: VoiceAgentToolsLike) -> Dict[str, Any]:
    if isinstance(tools, VoiceAgentTools):
        return tools.model_dump(by_alias=True, exclude_unset=True)
    if isinstance(tools, dict):
        try:
            parsed = VoiceAgentTools.model_validate(tools)
        except PydanticValidationError as e:
            raise ValidationError(f"Invalid 'tools': {e}") from e
        return parsed.model_dump(by_alias=True, exclude_unset=True)
    raise ValidationError("'tools' must be a VoiceAgentTools or a dict")
