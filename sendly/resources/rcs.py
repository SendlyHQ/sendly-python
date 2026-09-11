from urllib.parse import quote
"""
RCS Resource - Register your agent, discover agents, pre-flight recipient capability

RCS is a first-class Sendly channel: rich cards, suggestion chips, and
branded, verified-sender messaging on Android, sent via
``client.messages.send(channel='rcs', ...)``.

Sending as your brand requires an RCS agent - the verified sender identity
recipients see. Registration is self-serve, from the dashboard or from this
SDK: draft a brand and an agent, submit them for review by Sendly, and once
approved they go to the carrier network for verification. Once an agent is
``sendable``, no other setup is needed. The steps, each a method here:

1. ``rcs.dossier.get()`` - business details Sendly already holds, to
   prefill the brand.
2. ``rcs.brands.create()`` - the business identity (US businesses only).
3. ``rcs.agents.create()`` - the sender identity under that brand, with its
   logo, hero image and info-sheet links. Media must already be public
   ``https://`` URLs; uploading assets is a dashboard-only step.
4. ``rcs.agents.submit()`` - hands brand and agent to Sendly for review.
   Poll ``rcs.registration.get()`` (or ``rcs.agents.get()``) and watch
   ``stage`` move through ``in_review``, ``brand_verification``,
   ``agent_review`` and into ``testing``.
5. ``rcs.agents.set_test_devices()`` - invite phones to try the agent, then
   fill in ``campaign`` and ``testing`` with ``rcs.agents.update()``.
6. ``rcs.agents.request_launch()`` - asks for the launch review. The stage
   moves through ``launch_review`` and ``launching`` to ``live``.

Reads need an API key with the ``rcs:read`` scope, writes ``rcs:write``.
Registration is rolling out gradually; until it is enabled for your
account every registration call raises ``SendlyError`` with code
``rcs_not_enabled`` (HTTP 404).

Not every recipient can receive RCS. Text messages fall back to SMS
automatically by default (the send response discloses it via
``channel='sms'`` and ``fell_back_to='sms'``); use ``capability()`` to check
a recipient ahead of time. Sending and capability checks require a live
API key - delivery is never sandbox-simulated.
"""

from typing import Any, Dict, List, Optional, Sequence, Type, TypeVar, Union

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError, ValidationError
from ..types import (
    RcsAgentBasics,
    RcsAgentDetail,
    RcsAgentListResponse,
    RcsBrand,
    RcsBrandAddress,
    RcsBrandContact,
    RcsCampaign,
    RcsCapability,
    RcsDossier,
    RcsRegistration,
    RcsTestDeviceInput,
    RcsTestDeviceListResponse,
    RcsTesting,
)
from ..utils.http import AsyncHttpClient, HttpClient
from ..utils.validation import validate_phone_number

_M = TypeVar("_M", bound=BaseModel)

RcsInputLike = Union[BaseModel, Dict[str, Any]]
RcsTestDeviceLike = Union[RcsTestDeviceInput, Dict[str, Any], str]


class RcsRegistrationResource:
    """Registration sub-resource - the whole registration at a glance (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def get(self) -> RcsRegistration:
        """Fetch the workspace's RCS registration: newest brand, newest agent,
        its test devices, and the overall ``stage``.

        Poll this after :meth:`RcsAgentsResource.submit` and
        :meth:`RcsAgentsResource.request_launch` to follow progress.
        ``stage`` is ``draft`` when nothing has been created yet.

        Example:
            >>> reg = client.rcs.registration.get()
            >>> print(reg.stage, reg.agent and reg.agent.review_note)
        """
        data = self._http.request(method="GET", path="/rcs/registration")
        return _parse(RcsRegistration, data)


class RcsDossierResource:
    """Dossier sub-resource - what Sendly can prefill into a brand (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def get(self) -> RcsDossier:
        """Fetch the business details Sendly already holds for this
        workspace - from your newest 10DLC brand or your active toll-free
        verification - so you can prefill :meth:`RcsBrandsResource.create`.

        Only the keys on file are present; ``source`` says where they came
        from and ``us_eligible`` is False when something on file names a
        non-US country.

        Example:
            >>> dossier = client.rcs.dossier.get()
            >>> if dossier.us_eligible:
            ...     brand = client.rcs.brands.create(
            ...         **dossier.brand.model_dump(exclude_none=True)
            ...     )
        """
        data = self._http.request(method="GET", path="/rcs/dossier")
        return _parse(RcsDossier, data)


class RcsBrandsResource:
    """Brands sub-resource for the business identity behind an agent (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def create(
        self,
        *,
        display_name: Optional[str] = None,
        legal_name: Optional[str] = None,
        legal_entity_type: Optional[str] = None,
        organization_type: Optional[str] = None,
        website_url: Optional[str] = None,
        ein: Optional[str] = None,
        stock_symbol: Optional[str] = None,
        address: Optional[RcsInputLike] = None,
        contact: Optional[RcsInputLike] = None,
        idempotency_key: Optional[str] = None,
    ) -> RcsBrand:
        """Draft a brand - step 1 of registering to send RCS. Requires the
        ``rcs:write`` scope.

        Every field is optional here; required fields are checked when the
        agent is submitted. ``address.country_code`` must be ``US`` -
        registration is open to US businesses for now (``rcs_us_only``).

        Args:
            display_name: The brand name recipients see.
            legal_name: Legal business name.
            legal_entity_type: ``LIMITED_LIABILITY_COMPANY`` |
                ``SOLE_PROPRIETORSHIP`` | ``PARTNERSHIP`` | ``CORPORATION`` |
                ``S_CORPORATION``.
            organization_type: ``PRIVATE_PROFIT`` | ``PUBLIC_PROFIT`` |
                ``NON_PROFIT`` | ``GOVERNMENT`` | ``UNKNOWN``.
            website_url: Business website (https).
            ein: Employer Identification Number (``123456789`` or
                ``12-3456789``).
            stock_symbol: ``EXCHANGE:TICKER`` for publicly traded businesses.
            address: :class:`~sendly.types.RcsBrandAddress` or a dict of
                its fields.
            contact: :class:`~sendly.types.RcsBrandContact` or a dict of
                its fields.
            idempotency_key: Optional key (1-255 printable ASCII characters)
                sent as the Idempotency-Key header - retrying with the same
                key returns the original brand instead of creating another.
                When omitted, a unique key is generated automatically and
                reused across retry attempts.

        Example:
            >>> brand = client.rcs.brands.create(
            ...     display_name='Acme Coffee',
            ...     legal_name='Acme Holdings LLC',
            ...     legal_entity_type='LIMITED_LIABILITY_COMPANY',
            ...     organization_type='PRIVATE_PROFIT',
            ...     website_url='https://acme.example',
            ...     ein='12-3456789',
            ...     address={'line1': '1 Main St', 'city': 'Austin', 'state': 'TX',
            ...              'postal_code': '78701', 'country_code': 'US'},
            ...     contact={'first_name': 'Sam', 'last_name': 'Lee',
            ...              'email': 'sam@acme.example', 'phone_number': '+15551234567'},
            ... )
        """
        body = _brand_body(
            display_name,
            legal_name,
            legal_entity_type,
            organization_type,
            website_url,
            ein,
            stock_symbol,
            address,
            contact,
        )
        data = self._http.request(
            method="POST", path="/rcs/brands", body=body, idempotency_key=idempotency_key
        )
        return _parse(RcsBrand, _unwrap(data, "brand"))

    def update(
        self,
        id: str,
        *,
        display_name: Optional[str] = None,
        legal_name: Optional[str] = None,
        legal_entity_type: Optional[str] = None,
        organization_type: Optional[str] = None,
        website_url: Optional[str] = None,
        ein: Optional[str] = None,
        stock_symbol: Optional[str] = None,
        address: Optional[RcsInputLike] = None,
        contact: Optional[RcsInputLike] = None,
        idempotency_key: Optional[str] = None,
    ) -> RcsBrand:
        """Edit a draft brand. Supply only the fields to change - omitted
        fields keep their current value; ``address`` and ``contact`` may be
        partial. Requires the ``rcs:write`` scope.

        Locked while the brand is under review (``rcs_field_locked``); if
        the review asks for changes, ``review_note`` on the brand says what.

        Args:
            id: Brand identifier.
            idempotency_key: Optional key sent as the Idempotency-Key header.

        See :meth:`create` for the other arguments.
        """
        body = _brand_body(
            display_name,
            legal_name,
            legal_entity_type,
            organization_type,
            website_url,
            ein,
            stock_symbol,
            address,
            contact,
        )
        data = self._http.request(
            method="PATCH",
            path=f"/rcs/brands/{quote(id, safe='')}",
            body=body,
            idempotency_key=idempotency_key,
        )
        return _parse(RcsBrand, _unwrap(data, "brand"))


class RcsAgentsResource:
    """Agents sub-resource for listing and registering your RCS agents (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def list(self) -> RcsAgentListResponse:
        """List your RCS agents.

        Returns the agents registered on your workspace, newest first. An
        empty list means no agent is registered yet - draft one with
        :meth:`create`, or from the dashboard.

        Example:
            >>> for agent in client.rcs.agents.list().agents:
            ...     print(agent.name, agent.status, agent.sendable)
        """
        data = self._http.request(method="GET", path="/rcs/agents")
        try:
            return RcsAgentListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def create(
        self,
        brand_id: str,
        *,
        display_name: Optional[str] = None,
        use_case: Optional[str] = None,
        basics: Optional[RcsInputLike] = None,
        campaign: Optional[RcsInputLike] = None,
        testing: Optional[RcsInputLike] = None,
        idempotency_key: Optional[str] = None,
    ) -> RcsAgentDetail:
        """Draft an agent under a brand - step 2 of registering to send RCS.
        Requires the ``rcs:write`` scope.

        ``basics`` carries the identity recipients see (description, logo,
        hero image, brand color, privacy and terms links, info-sheet
        contacts). Logo and hero must already be public ``https://`` URLs;
        uploading assets is a dashboard-only step (``rcs_invalid_content``
        otherwise). ``campaign`` and ``testing`` can wait until after the
        agent is approved - they are needed for launch, not for submission.

        Args:
            brand_id: The brand this agent belongs to.
            display_name: The agent name recipients see (overrides
                ``basics.display_name``).
            use_case: ``MULTI_USE`` | ``PROMOTIONAL`` | ``TRANSACTIONAL`` |
                ``OTP`` (overrides ``basics.use_case``).
            basics: :class:`~sendly.types.RcsAgentBasics` or a dict of its
                fields.
            campaign: :class:`~sendly.types.RcsCampaign` or a dict of its
                fields.
            testing: :class:`~sendly.types.RcsTesting` or a dict of its
                fields.
            idempotency_key: Optional key sent as the Idempotency-Key header;
                generated automatically when omitted.

        Example:
            >>> agent = client.rcs.agents.create(
            ...     brand.id,
            ...     display_name='Acme Coffee',
            ...     use_case='MULTI_USE',
            ...     basics={
            ...         'description': 'Order updates and support for Acme customers',
            ...         'logo_url': 'https://acme.example/logo.png',
            ...         'hero_url': 'https://acme.example/hero.png',
            ...         'brand_color': '#5B3A29',
            ...         'privacy_policy_url': 'https://acme.example/privacy',
            ...         'terms_and_conditions_url': 'https://acme.example/terms',
            ...         'website': {'url': 'https://acme.example', 'label': 'Acme'},
            ...     },
            ... )
        """
        body = _agent_body(brand_id, display_name, use_case, basics, campaign, testing)
        data = self._http.request(
            method="POST", path="/rcs/agents", body=body, idempotency_key=idempotency_key
        )
        return _parse(RcsAgentDetail, _unwrap(data, "agent"))

    def get(self, id: str) -> RcsAgentDetail:
        """Fetch one agent with its ``review_status``, ``customer_stage``,
        ``review_note`` and invited ``test_devices``. Requires the
        ``rcs:read`` scope.

        Args:
            id: Agent identifier.
        """
        data = self._http.request(method="GET", path=f"/rcs/agents/{quote(id, safe='')}")
        return _parse(RcsAgentDetail, _unwrap(data, "agent"))

    def update(
        self,
        id: str,
        *,
        display_name: Optional[str] = None,
        use_case: Optional[str] = None,
        basics: Optional[RcsInputLike] = None,
        campaign: Optional[RcsInputLike] = None,
        testing: Optional[RcsInputLike] = None,
        idempotency_key: Optional[str] = None,
    ) -> RcsAgentDetail:
        """Edit an agent. Supply only the groups to change: ``display_name``,
        ``use_case`` and ``basics`` patch the identity; ``campaign`` and
        ``testing`` are merged section-wise, so a partial dict updates just
        those keys. Requires the ``rcs:write`` scope.

        Locked while the agent is under review (``rcs_field_locked``). The
        identity locks once it has gone to the carrier network; campaign
        and testing lock once the launch has, unless the launch was
        rejected. Media must be public ``https://`` URLs.

        Args:
            id: Agent identifier.
            idempotency_key: Optional key sent as the Idempotency-Key header.

        See :meth:`create` for the other arguments.

        Example:
            >>> client.rcs.agents.update(
            ...     agent.id,
            ...     campaign={
            ...         'agent_overview': 'Order updates and support replies',
            ...         'interactions': [
            ...             {'interaction_type': 'TRANSACTIONAL_UPDATES',
            ...              'description': 'Shipping and delivery updates'},
            ...         ],
            ...         'message_examples': ['Your order #123 has shipped!',
            ...                              'Your table is ready!',
            ...                              'Reply HELP for help'],
            ...         'consent_settings': {
            ...             'opt_in_methods': [{'method_type': 'WEBSITE',
            ...                                 'description': 'Checkout checkbox'}],
            ...             'opt_out_response': 'You are unsubscribed.',
            ...         },
            ...     },
            ... )
        """
        body = _agent_body(None, display_name, use_case, basics, campaign, testing)
        data = self._http.request(
            method="PATCH",
            path=f"/rcs/agents/{quote(id, safe='')}",
            body=body,
            idempotency_key=idempotency_key,
        )
        return _parse(RcsAgentDetail, _unwrap(data, "agent"))

    def set_test_devices(
        self,
        id: str,
        devices: Sequence[RcsTestDeviceLike],
        *,
        idempotency_key: Optional[str] = None,
    ) -> RcsTestDeviceListResponse:
        """Replace the phones invited to test the agent (up to 20). The list
        is authoritative: numbers missing from it are removed, new ones are
        invited. Requires the ``rcs:write`` scope.

        Args:
            id: Agent identifier.
            devices: Each entry is an E.164 string, a dict with
                ``phone_number`` and optional ``label``, or a
                :class:`~sendly.types.RcsTestDeviceInput`.
            idempotency_key: Optional key sent as the Idempotency-Key header.

        Example:
            >>> client.rcs.agents.set_test_devices(agent.id, [
            ...     '+15551234567',
            ...     {'phone_number': '+15557654321', 'label': 'Sam'},
            ... ])
        """
        body = _devices_body(devices)
        data = self._http.request(
            method="PUT",
            path=f"/rcs/agents/{quote(id, safe='')}/test-devices",
            body=body,
            idempotency_key=idempotency_key,
        )
        return _parse(RcsTestDeviceListResponse, data)

    def submit(self, id: str, *, idempotency_key: Optional[str] = None) -> RcsAgentDetail:
        """Submit the agent and its brand for review by Sendly, after which
        they go to the carrier network. Requires the ``rcs:write`` scope.

        The brand and the agent identity must be complete
        (``rcs_invalid_content`` lists what is missing, with ``brand.`` and
        ``agent.`` paths). On success ``review_status`` is
        ``awaiting_review`` and ``customer_stage`` is ``in_review``; poll
        :meth:`get` or :meth:`RcsRegistrationResource.get`. Submitting again
        while under review raises ``rcs_field_locked``.

        Args:
            id: Agent identifier.
            idempotency_key: Optional key sent as the Idempotency-Key header;
                generated automatically when omitted. A replay returns the
                original response and does not notify reviewers again.
        """
        data = self._http.request(
            method="POST",
            path=f"/rcs/agents/{quote(id, safe='')}/submit",
            body={},
            idempotency_key=idempotency_key,
        )
        return _parse(RcsAgentDetail, _unwrap(data, "agent"))

    def request_launch(
        self,
        id: str,
        *,
        test_url: Optional[str] = None,
        testing_additional_information: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> RcsAgentDetail:
        """Ask for the launch review once the agent is in ``testing`` and
        you have tried it on an invited device. Requires the ``rcs:write``
        scope.

        Needs a complete ``campaign`` (overview, at least one interaction,
        at least three message examples, consent settings) and a
        ``testing.test_url``; ``rcs_invalid_content`` lists what is missing.
        ``rcs_launch_not_ready`` means the agent is not in testing yet. On
        success ``review_status`` is ``launch_requested`` and
        ``customer_stage`` is ``launch_review``.

        Args:
            id: Agent identifier.
            test_url: Link to the test evidence; stored into ``testing``
                before the request.
            testing_additional_information: Notes for reviewers; stored into
                ``testing`` before the request.
            idempotency_key: Optional key sent as the Idempotency-Key header;
                generated automatically when omitted.
        """
        body = _launch_body(test_url, testing_additional_information)
        data = self._http.request(
            method="POST",
            path=f"/rcs/agents/{quote(id, safe='')}/request-launch",
            body=body,
            idempotency_key=idempotency_key,
        )
        return _parse(RcsAgentDetail, _unwrap(data, "agent"))


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

    No agent yet? Register one - see the module docstring for the flow:
        >>> brand = client.rcs.brands.create(display_name='Acme Coffee', ...)
        >>> agent = client.rcs.agents.create(brand.id, display_name='Acme Coffee', ...)
        >>> client.rcs.agents.submit(agent.id)
        >>> print(client.rcs.registration.get().stage)
    """

    def __init__(self, http: HttpClient):
        self._http = http
        self.agents = RcsAgentsResource(http)
        self.registration = RcsRegistrationResource(http)
        self.dossier = RcsDossierResource(http)
        self.brands = RcsBrandsResource(http)

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


class AsyncRcsRegistrationResource:
    """Registration sub-resource - the whole registration at a glance (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def get(self) -> RcsRegistration:
        """Fetch the workspace's RCS registration.
        See :meth:`RcsRegistrationResource.get`."""
        data = await self._http.request(method="GET", path="/rcs/registration")
        return _parse(RcsRegistration, data)


class AsyncRcsDossierResource:
    """Dossier sub-resource - what Sendly can prefill into a brand (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def get(self) -> RcsDossier:
        """Fetch the business details Sendly already holds.
        See :meth:`RcsDossierResource.get`."""
        data = await self._http.request(method="GET", path="/rcs/dossier")
        return _parse(RcsDossier, data)


class AsyncRcsBrandsResource:
    """Brands sub-resource for the business identity behind an agent (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def create(
        self,
        *,
        display_name: Optional[str] = None,
        legal_name: Optional[str] = None,
        legal_entity_type: Optional[str] = None,
        organization_type: Optional[str] = None,
        website_url: Optional[str] = None,
        ein: Optional[str] = None,
        stock_symbol: Optional[str] = None,
        address: Optional[RcsInputLike] = None,
        contact: Optional[RcsInputLike] = None,
        idempotency_key: Optional[str] = None,
    ) -> RcsBrand:
        """Draft a brand. See :meth:`RcsBrandsResource.create`."""
        body = _brand_body(
            display_name,
            legal_name,
            legal_entity_type,
            organization_type,
            website_url,
            ein,
            stock_symbol,
            address,
            contact,
        )
        data = await self._http.request(
            method="POST", path="/rcs/brands", body=body, idempotency_key=idempotency_key
        )
        return _parse(RcsBrand, _unwrap(data, "brand"))

    async def update(
        self,
        id: str,
        *,
        display_name: Optional[str] = None,
        legal_name: Optional[str] = None,
        legal_entity_type: Optional[str] = None,
        organization_type: Optional[str] = None,
        website_url: Optional[str] = None,
        ein: Optional[str] = None,
        stock_symbol: Optional[str] = None,
        address: Optional[RcsInputLike] = None,
        contact: Optional[RcsInputLike] = None,
        idempotency_key: Optional[str] = None,
    ) -> RcsBrand:
        """Edit a draft brand. See :meth:`RcsBrandsResource.update`."""
        body = _brand_body(
            display_name,
            legal_name,
            legal_entity_type,
            organization_type,
            website_url,
            ein,
            stock_symbol,
            address,
            contact,
        )
        data = await self._http.request(
            method="PATCH",
            path=f"/rcs/brands/{quote(id, safe='')}",
            body=body,
            idempotency_key=idempotency_key,
        )
        return _parse(RcsBrand, _unwrap(data, "brand"))


class AsyncRcsAgentsResource:
    """Agents sub-resource for listing and registering your RCS agents (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list(self) -> RcsAgentListResponse:
        """List your RCS agents. See :meth:`RcsAgentsResource.list`."""
        data = await self._http.request(method="GET", path="/rcs/agents")
        try:
            return RcsAgentListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def create(
        self,
        brand_id: str,
        *,
        display_name: Optional[str] = None,
        use_case: Optional[str] = None,
        basics: Optional[RcsInputLike] = None,
        campaign: Optional[RcsInputLike] = None,
        testing: Optional[RcsInputLike] = None,
        idempotency_key: Optional[str] = None,
    ) -> RcsAgentDetail:
        """Draft an agent under a brand. See :meth:`RcsAgentsResource.create`."""
        body = _agent_body(brand_id, display_name, use_case, basics, campaign, testing)
        data = await self._http.request(
            method="POST", path="/rcs/agents", body=body, idempotency_key=idempotency_key
        )
        return _parse(RcsAgentDetail, _unwrap(data, "agent"))

    async def get(self, id: str) -> RcsAgentDetail:
        """Fetch one agent. See :meth:`RcsAgentsResource.get`."""
        data = await self._http.request(method="GET", path=f"/rcs/agents/{quote(id, safe='')}")
        return _parse(RcsAgentDetail, _unwrap(data, "agent"))

    async def update(
        self,
        id: str,
        *,
        display_name: Optional[str] = None,
        use_case: Optional[str] = None,
        basics: Optional[RcsInputLike] = None,
        campaign: Optional[RcsInputLike] = None,
        testing: Optional[RcsInputLike] = None,
        idempotency_key: Optional[str] = None,
    ) -> RcsAgentDetail:
        """Edit an agent. See :meth:`RcsAgentsResource.update`."""
        body = _agent_body(None, display_name, use_case, basics, campaign, testing)
        data = await self._http.request(
            method="PATCH",
            path=f"/rcs/agents/{quote(id, safe='')}",
            body=body,
            idempotency_key=idempotency_key,
        )
        return _parse(RcsAgentDetail, _unwrap(data, "agent"))

    async def set_test_devices(
        self,
        id: str,
        devices: Sequence[RcsTestDeviceLike],
        *,
        idempotency_key: Optional[str] = None,
    ) -> RcsTestDeviceListResponse:
        """Replace the invited test devices.
        See :meth:`RcsAgentsResource.set_test_devices`."""
        body = _devices_body(devices)
        data = await self._http.request(
            method="PUT",
            path=f"/rcs/agents/{quote(id, safe='')}/test-devices",
            body=body,
            idempotency_key=idempotency_key,
        )
        return _parse(RcsTestDeviceListResponse, data)

    async def submit(
        self, id: str, *, idempotency_key: Optional[str] = None
    ) -> RcsAgentDetail:
        """Submit the agent and its brand for review.
        See :meth:`RcsAgentsResource.submit`."""
        data = await self._http.request(
            method="POST",
            path=f"/rcs/agents/{quote(id, safe='')}/submit",
            body={},
            idempotency_key=idempotency_key,
        )
        return _parse(RcsAgentDetail, _unwrap(data, "agent"))

    async def request_launch(
        self,
        id: str,
        *,
        test_url: Optional[str] = None,
        testing_additional_information: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> RcsAgentDetail:
        """Ask for the launch review. See :meth:`RcsAgentsResource.request_launch`."""
        body = _launch_body(test_url, testing_additional_information)
        data = await self._http.request(
            method="POST",
            path=f"/rcs/agents/{quote(id, safe='')}/request-launch",
            body=body,
            idempotency_key=idempotency_key,
        )
        return _parse(RcsAgentDetail, _unwrap(data, "agent"))


class AsyncRcsResource:
    """RCS API resource (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http
        self.agents = AsyncRcsAgentsResource(http)
        self.registration = AsyncRcsRegistrationResource(http)
        self.dossier = AsyncRcsDossierResource(http)
        self.brands = AsyncRcsBrandsResource(http)

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


def _dump(value: Any, model: Type[_M], name: str) -> Dict[str, Any]:
    """Serialize a typed input (model or dict) to the API's camelCase shape,
    keeping only the keys the caller actually set."""
    if isinstance(value, model):
        return value.model_dump(by_alias=True, exclude_unset=True)
    if isinstance(value, dict):
        try:
            parsed = model.model_validate(value)
        except PydanticValidationError as e:
            raise ValidationError(f"Invalid '{name}': {e}") from e
        return parsed.model_dump(by_alias=True, exclude_unset=True)
    raise ValidationError(f"'{name}' must be a {model.__name__} or a dict")


def _brand_body(
    display_name: Optional[str],
    legal_name: Optional[str],
    legal_entity_type: Optional[str],
    organization_type: Optional[str],
    website_url: Optional[str],
    ein: Optional[str],
    stock_symbol: Optional[str],
    address: Optional[RcsInputLike],
    contact: Optional[RcsInputLike],
) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    optional: Dict[str, Any] = {
        "displayName": display_name,
        "legalName": legal_name,
        "legalEntityType": legal_entity_type,
        "organizationType": organization_type,
        "websiteUrl": website_url,
        "ein": ein,
        "stockSymbol": stock_symbol,
    }
    for key, value in optional.items():
        if value is not None:
            body[key] = value
    if address is not None:
        body["address"] = _dump(address, RcsBrandAddress, "address")
    if contact is not None:
        body["contact"] = _dump(contact, RcsBrandContact, "contact")
    return body


def _agent_body(
    brand_id: Optional[str],
    display_name: Optional[str],
    use_case: Optional[str],
    basics: Optional[RcsInputLike],
    campaign: Optional[RcsInputLike],
    testing: Optional[RcsInputLike],
) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if brand_id is not None:
        body["brandId"] = brand_id
    if display_name is not None:
        body["displayName"] = display_name
    if use_case is not None:
        body["useCase"] = use_case
    if basics is not None:
        body["basics"] = _dump(basics, RcsAgentBasics, "basics")
    if campaign is not None:
        body["campaign"] = _dump(campaign, RcsCampaign, "campaign")
    if testing is not None:
        body["testing"] = _dump(testing, RcsTesting, "testing")
    return body


def _devices_body(devices: Sequence[RcsTestDeviceLike]) -> Dict[str, Any]:
    if isinstance(devices, (str, bytes, dict)) or not isinstance(devices, Sequence):
        raise ValidationError("'devices' must be a list")
    items: List[Dict[str, Any]] = []
    for device in devices:
        if isinstance(device, str):
            items.append({"phoneNumber": device})
        else:
            items.append(_dump(device, RcsTestDeviceInput, "devices"))
    return {"devices": items}


def _launch_body(
    test_url: Optional[str], testing_additional_information: Optional[str]
) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if test_url is not None:
        body["testUrl"] = test_url
    if testing_additional_information is not None:
        body["testingAdditionalInformation"] = testing_additional_information
    return body


def _unwrap(data: Any, key: str) -> Any:
    if isinstance(data, dict) and isinstance(data.get(key), dict):
        return data[key]
    raise SendlyError(
        message=f"Invalid API response format: expected a '{key}' object",
        code="invalid_response",
        status_code=200,
    )


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
