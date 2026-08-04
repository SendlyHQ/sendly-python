"""
Tests for RCS resource (agents, capability) and messages.send with
channel='rcs'
"""

import json

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import AuthenticationError, NotFoundError, SendlyError, ValidationError
from sendly.types import RcsAgentListResponse, RcsCapability, RcsMessage


@pytest.fixture
def mock_agent():
    return {
        "id": "rcs_agent_123",
        "name": "Acme Coffee",
        "status": "approved",
        "useCase": "customer service",
        "sendable": True,
        "createdAt": "2026-07-30T09:12:00Z",
    }


@pytest.fixture
def mock_capability():
    return {
        "to": "+15551234567",
        "agentId": "rcs_agent_123",
        "capable": True,
        "features": ["RICHCARD_STANDALONE", "ACTION_OPEN_URL"],
    }


@pytest.fixture
def mock_rcs_message():
    return {
        "id": "msg_rcs_123",
        "channel": "rcs",
        "message_format": "rcs",
        "to": "+15551234567",
        "from": "Acme Coffee",
        "text": "Your table is ready!",
        "status": "sent",
        "segments": 1,
        "creditsUsed": 2,
        "rcs": {
            "kind": "text",
            "agentId": "rcs_agent_123",
            "agentName": "Acme Coffee",
        },
        "createdAt": "2026-07-30T10:00:00Z",
        "metadata": {},
    }


@pytest.fixture
def mock_rcs_fallback_message():
    return {
        "id": "msg_rcs_456",
        "channel": "sms",
        "fellBackTo": "sms",
        "message_format": "sms",
        "to": "+15551234567",
        "from": "+18005550199",
        "text": "Your table is ready!",
        "status": "sent",
        "segments": 1,
        "creditsUsed": 2,
        "rcs": {"requestedChannel": "rcs", "agentId": "rcs_agent_123"},
        "createdAt": "2026-07-30T10:00:00Z",
        "metadata": {},
    }


class TestAgentsList:
    def test_list_agents(self, api_key, mock_agent, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/rcs/agents",
            method="GET",
            json={"agents": [mock_agent]},
        )

        result = client.rcs.agents.list()

        assert isinstance(result, RcsAgentListResponse)
        assert len(result.agents) == 1
        agent = result.agents[0]
        assert agent.id == "rcs_agent_123"
        assert agent.name == "Acme Coffee"
        assert agent.status == "approved"
        assert agent.use_case == "customer service"
        assert agent.sendable is True
        assert agent.created_at == "2026-07-30T09:12:00Z"

        client.close()

    def test_list_agents_empty(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/rcs/agents",
            method="GET",
            json={"agents": []},
        )

        result = client.rcs.agents.list()

        assert result.agents == []

        client.close()

    def test_list_agents_surfaces_non_sendable(
        self, api_key, mock_agent, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/rcs/agents",
            method="GET",
            json={
                "agents": [
                    {
                        **mock_agent,
                        "status": "submitted",
                        "useCase": None,
                        "sendable": False,
                    }
                ]
            },
        )

        agent = client.rcs.agents.list().agents[0]

        assert agent.status == "submitted"
        assert agent.sendable is False
        assert agent.use_case is None

        client.close()

    def test_list_agents_unauthorized_401(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/rcs/agents",
            method="GET",
            status_code=401,
            json=mock_error_response("unauthorized", "Unauthorized"),
        )

        with pytest.raises(AuthenticationError):
            client.rcs.agents.list()

        client.close()

    def test_list_agents_not_enabled_404(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/rcs/agents",
            method="GET",
            status_code=404,
            json=mock_error_response("not_found", "Not found"),
        )

        with pytest.raises(NotFoundError):
            client.rcs.agents.list()

        client.close()


class TestCapability:
    def test_capability(self, api_key, mock_capability, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/rcs/capability?to=%2B15551234567",
            method="GET",
            json=mock_capability,
        )

        result = client.rcs.capability(to="+15551234567")

        assert isinstance(result, RcsCapability)
        assert result.to == "+15551234567"
        assert result.agent_id == "rcs_agent_123"
        assert result.capable is True
        assert "RICHCARD_STANDALONE" in result.features

        client.close()

    def test_capability_with_agent_id(
        self, api_key, mock_capability, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=(
                "https://sendly.live/api/v1/rcs/capability"
                "?to=%2B15551234567&agentId=rcs_agent_123"
            ),
            method="GET",
            json={**mock_capability, "capable": False, "features": []},
        )

        result = client.rcs.capability(to="+15551234567", agent_id="rcs_agent_123")

        assert result.capable is False
        assert result.features == []

        client.close()

    def test_capability_invalid_phone(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Invalid phone number format"):
            client.rcs.capability(to="15551234567")

        client.close()

    def test_capability_requires_live_key_403(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/rcs/capability?to=%2B15551234567",
            method="GET",
            status_code=403,
            json=mock_error_response(
                "rcs_requires_live_key",
                "RCS capability checks require a live API key.",
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.rcs.capability(to="+15551234567")

        assert exc_info.value.code == "rcs_requires_live_key"

        client.close()

    def test_capability_agent_ambiguous_400(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/rcs/capability?to=%2B15551234567",
            method="GET",
            status_code=400,
            json=mock_error_response(
                "rcs_agent_ambiguous",
                "This workspace has more than one RCS agent. Pass agentId to pick one.",
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.rcs.capability(to="+15551234567")

        assert exc_info.value.code == "rcs_agent_ambiguous"

        client.close()


class TestRcsSend:
    def test_send_text(self, api_key, mock_rcs_message, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=201,
            json=mock_rcs_message,
        )

        message = client.messages.send(
            channel="rcs",
            to="+15551234567",
            text="Your table is ready!",
        )

        assert isinstance(message, RcsMessage)
        assert message.channel == "rcs"
        assert message.fell_back_to is None
        assert message.from_ == "Acme Coffee"
        assert message.rcs.kind == "text"
        assert message.rcs.agent_name == "Acme Coffee"
        assert message.status.value == "sent"

        payload = json.loads(httpx_mock.get_request().read().decode())
        assert payload == {
            "channel": "rcs",
            "to": "+15551234567",
            "text": "Your table is ready!",
        }

        client.close()

    def test_send_text_with_suggestions_and_agent(
        self, api_key, mock_rcs_message, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=201,
            json=mock_rcs_message,
        )

        client.messages.send(
            channel="rcs",
            to="+15551234567",
            agent_id="rcs_agent_123",
            text="Your table is ready!",
            suggestions=[
                {"reply": {"text": "On my way", "postbackData": "omw"}},
                {
                    "action": {
                        "text": "View menu",
                        "postbackData": "menu",
                        "url": "https://example.com/menu",
                    }
                },
            ],
        )

        payload = json.loads(httpx_mock.get_request().read().decode())
        assert payload["agentId"] == "rcs_agent_123"
        assert len(payload["suggestions"]) == 2
        assert payload["suggestions"][0]["reply"]["postbackData"] == "omw"
        assert payload["suggestions"][1]["action"]["url"] == "https://example.com/menu"

        client.close()

    def test_send_card(self, api_key, mock_rcs_message, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=201,
            json={
                **mock_rcs_message,
                "text": None,
                "rcs": {
                    "kind": "card",
                    "agentId": "rcs_agent_123",
                    "agentName": "Acme Coffee",
                },
            },
        )

        message = client.messages.send(
            channel="rcs",
            to="+15551234567",
            card={
                "title": "Your order has shipped",
                "description": "Arriving Thursday",
                "mediaUrl": "https://example.com/package.jpg",
                "orientation": "horizontal",
                "suggestions": [
                    {
                        "action": {
                            "text": "Track it",
                            "postbackData": "track",
                            "url": "https://example.com/track",
                        }
                    }
                ],
            },
        )

        assert message.rcs.kind == "card"
        assert message.text is None

        payload = json.loads(httpx_mock.get_request().read().decode())
        assert payload["card"]["title"] == "Your order has shipped"
        assert payload["card"]["orientation"] == "horizontal"
        assert "text" not in payload

        client.close()

    def test_send_discloses_sms_fallback(
        self, api_key, mock_rcs_fallback_message, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=201,
            json={
                **mock_rcs_fallback_message,
                "rcs": {
                    **mock_rcs_fallback_message["rcs"],
                    "suggestionsDropped": True,
                },
            },
        )

        message = client.messages.send(
            channel="rcs",
            to="+15551234567",
            text="Your table is ready!",
            suggestions=[{"reply": {"text": "On my way", "postbackData": "omw"}}],
        )

        assert message.channel == "sms"
        assert message.fell_back_to == "sms"
        assert message.message_format == "sms"
        assert message.from_ == "+18005550199"
        assert message.rcs.requested_channel == "rcs"
        assert message.rcs.suggestions_dropped is True
        assert message.rcs.kind is None

        client.close()

    def test_send_passes_fallback_to_sms_false(
        self, api_key, mock_rcs_message, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=201,
            json=mock_rcs_message,
        )

        client.messages.send(
            channel="rcs",
            to="+15551234567",
            text="Your table is ready!",
            fallback_to_sms=False,
        )

        payload = json.loads(httpx_mock.get_request().read().decode())
        assert payload["fallbackToSms"] is False

        client.close()

    def test_send_requires_exactly_one_of_text_or_card(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(SendlyError, match="exactly one of 'text' or 'card'"):
            client.messages.send(channel="rcs", to="+15551234567")

        with pytest.raises(SendlyError, match="exactly one of 'text' or 'card'"):
            client.messages.send(
                channel="rcs",
                to="+15551234567",
                text="Hello",
                card={"title": "Hi", "description": "There"},
            )

        client.close()

    def test_send_invalid_phone(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Invalid phone number format"):
            client.messages.send(channel="rcs", to="15551234567", text="Hello")

        client.close()

    def test_send_not_supported_for_recipient_422(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=422,
            json=mock_error_response(
                "rcs_not_supported_for_recipient",
                "This recipient's device or network doesn't support RCS.",
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.messages.send(
                channel="rcs",
                to="+15551234567",
                text="Hello!",
                fallback_to_sms=False,
            )

        assert exc_info.value.code == "rcs_not_supported_for_recipient"
        assert exc_info.value.status_code == 422

        client.close()

    def test_send_sms_unchanged(self, api_key, mock_message, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_message,
        )

        message = client.messages.send(to="+15551234567", text="Test message")

        assert message.id == "msg_test_123"

        payload = json.loads(httpx_mock.get_request().read().decode())
        assert "channel" not in payload

        client.close()


class TestAsyncRcs:
    async def test_async_list_agents(self, api_key, mock_agent, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/rcs/agents",
            method="GET",
            json={"agents": [mock_agent]},
        )

        result = await client.rcs.agents.list()

        assert result.agents[0].id == "rcs_agent_123"
        assert result.agents[0].sendable is True

        await client.close()

    async def test_async_capability(
        self, api_key, mock_capability, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url=(
                "https://sendly.live/api/v1/rcs/capability"
                "?to=%2B15551234567&agentId=rcs_agent_123"
            ),
            method="GET",
            json=mock_capability,
        )

        result = await client.rcs.capability(
            to="+15551234567", agent_id="rcs_agent_123"
        )

        assert result.capable is True

        await client.close()

    async def test_async_send_rcs(
        self, api_key, mock_rcs_message, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=201,
            json=mock_rcs_message,
        )

        message = await client.messages.send(
            channel="rcs",
            to="+15551234567",
            text="Your table is ready!",
        )

        assert isinstance(message, RcsMessage)
        assert message.rcs.kind == "text"

        await client.close()

    async def test_async_send_discloses_sms_fallback(
        self, api_key, mock_rcs_fallback_message, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=201,
            json=mock_rcs_fallback_message,
        )

        message = await client.messages.send(
            channel="rcs",
            to="+15551234567",
            text="Your table is ready!",
        )

        assert message.channel == "sms"
        assert message.fell_back_to == "sms"

        await client.close()

    async def test_async_send_requires_exactly_one_of_text_or_card(self, api_key):
        client = AsyncSendly(api_key)

        with pytest.raises(SendlyError, match="exactly one of 'text' or 'card'"):
            await client.messages.send(channel="rcs", to="+15551234567")

        await client.close()
