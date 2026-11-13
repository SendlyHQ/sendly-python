"""
Tests for voice configuration (numbers, emergency address, agents, voices)
"""

import json
import re

import pytest
from pytest_httpx import HTTPXMock

from sendly import (
    AsyncSendly,
    AsyncVoiceResource,
    Sendly,
    VoiceResource,
)
from sendly.errors import RateLimitError, SendlyError, ValidationError
from sendly.types import (
    DeletedVoiceAgent,
    EmergencyAddress,
    SipTransport,
    Voice,
    VoiceAgent,
    VoiceAgentConnection,
    VoiceAgentCustomLlmConnectionInput,
    VoiceAgentKind,
    VoiceAgentListResponse,
    VoiceAgentSipConnectionInput,
    VoiceAgentTest,
    VoiceAgentTestOutcome,
    VoiceAgentTestStep,
    VoiceAgentTestStepName,
    VoiceAgentTools,
    VoiceAgentWebsocketConnectionInput,
    VoiceListResponse,
    VoiceMode,
    VoiceNumber,
    VoiceNumberEmergencyAddress,
    VoiceNumberListResponse,
    VoiceNumberRates,
)

BASE = "https://sendly.live/api/v1"
AUTO_KEY = re.compile(r"^sendly-python-retry-[0-9a-f-]{36}$")
NUMBER_ID = "5f0c1c2e-2a44-4d4b-9d51-0a9b0f6f4a11"
AGENT_ID = "3c4d5e6f-7081-4293-a4b5-c6d7e8f90a1b"
PHONE = "+15555550188"
ENCODED_PHONE = "%2B15555550188"


def _body(request):
    return json.loads(request.read().decode())


@pytest.fixture
def mock_voice_number():
    return {
        "id": NUMBER_ID,
        "object": "voice_number",
        "phoneNumber": PHONE,
        "phoneNumberType": "local",
        "countryCode": "US",
        "isDefault": True,
        "voiceEnabled": True,
        "voiceMode": "agent",
        "agentId": AGENT_ID,
        "emergencyAddress": {
            "status": "active",
            "address": {
                "street": "500 Example Ave",
                "unit": "Suite 2",
                "city": "Austin",
                "state": "TX",
                "zip": "78701",
                "country": "US",
            },
        },
        "ratePerMinute": {"inbound": 2, "outbound": 2, "agent": 10},
    }


@pytest.fixture
def mock_voice_number_off():
    return {
        "id": "7a8b9c0d-1e2f-4a3b-8c4d-5e6f7a8b9c0d",
        "object": "voice_number",
        "phoneNumber": "+15555550199",
        "phoneNumberType": "toll_free",
        "countryCode": "US",
        "isDefault": False,
        "voiceEnabled": False,
        "voiceMode": "none",
        "agentId": None,
        "emergencyAddress": None,
        "ratePerMinute": {"inbound": 3, "outbound": 2, "agent": 11},
    }


@pytest.fixture
def mock_agent():
    return {
        "id": AGENT_ID,
        "object": "voice_agent",
        "name": "Front desk",
        "enabled": True,
        "voice": "ashley",
        "voiceLabel": "Ashley (US, warm)",
        "language": "en-US",
        "greeting": "Thanks for calling Acme, how can I help?",
        "instructions": "Answer questions about opening hours.",
        "tools": {"sendSms": False, "transferTo": None},
        "canSendSms": True,
        "callsHandled": 12,
        "avgDurationSecs": 74,
        "createdAt": "2026-09-14T17:00:00.000Z",
        "updatedAt": "2026-09-14T17:05:00.000Z",
    }


class TestVoiceClient:
    def test_client_exposes_voice_sub_resources(self, api_key):
        client = Sendly(api_key)

        assert isinstance(client.voice, VoiceResource)
        assert hasattr(client.voice.numbers, "register_emergency_address")
        assert hasattr(client.voice.agents, "delete")
        assert hasattr(client.voice.voices, "list")

        client.close()

    async def test_async_client_exposes_voice_sub_resources(self, api_key):
        client = AsyncSendly(api_key)

        assert isinstance(client.voice, AsyncVoiceResource)
        assert hasattr(client.voice.numbers, "register_emergency_address")

        await client.close()


class TestVoiceNumbers:
    def test_list(
        self, api_key, mock_voice_number, mock_voice_number_off, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        payload = dict(mock_voice_number)
        payload["emergencyAddress"] = {
            "status": "provisioning",
            "address": {
                "street": "500 Example Ave",
                "city": "Austin",
                "state": "TX",
                "zip": "78701",
                "country": "US",
            },
        }
        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers",
            method="GET",
            json={"data": [payload, mock_voice_number_off]},
        )

        result = client.voice.numbers.list()

        assert isinstance(result, VoiceNumberListResponse)
        assert len(result.data) == 2
        first, second = result.data
        assert isinstance(first, VoiceNumber)
        assert first.id == NUMBER_ID
        assert first.object == "voice_number"
        assert first.phone_number == PHONE
        assert first.phone_number_type == "local"
        assert first.country_code == "US"
        assert first.is_default is True
        assert first.voice_enabled is True
        assert first.voice_mode == VoiceMode.AGENT
        assert first.agent_id == AGENT_ID
        assert isinstance(first.emergency_address, VoiceNumberEmergencyAddress)
        assert first.emergency_address.status == "provisioning"
        assert isinstance(first.emergency_address.address, EmergencyAddress)
        assert first.emergency_address.address.unit is None
        assert first.emergency_address.address.zip == "78701"
        assert isinstance(first.rate_per_minute, VoiceNumberRates)
        assert first.rate_per_minute.agent == 10

        assert second.voice_enabled is False
        assert second.voice_mode == VoiceMode.NONE
        assert second.agent_id is None
        assert second.emergency_address is None
        assert second.rate_per_minute.inbound == 3

        request = httpx_mock.get_request()
        assert request.method == "GET"
        assert request.url.path == "/api/v1/voice/numbers"
        assert "Idempotency-Key" not in request.headers

        client.close()

    def test_get_by_id(self, api_key, mock_voice_number, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{NUMBER_ID}", method="GET", json=mock_voice_number
        )

        result = client.voice.numbers.get(NUMBER_ID)

        assert result.id == NUMBER_ID
        assert result.emergency_address.address.unit == "Suite 2"
        assert httpx_mock.get_request().url.path == f"/api/v1/voice/numbers/{NUMBER_ID}"

        client.close()

    def test_get_by_e164_percent_encodes_plus(
        self, api_key, mock_voice_number, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{ENCODED_PHONE}", method="GET", json=mock_voice_number
        )

        result = client.voice.numbers.get(PHONE)

        assert result.phone_number == PHONE
        assert (
            httpx_mock.get_request().url.raw_path
            == f"/api/v1/voice/numbers/{ENCODED_PHONE}".encode()
        )

        client.close()

    def test_get_rejects_empty_number_before_request(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="number is required"):
            client.voice.numbers.get("")

        with pytest.raises(ValidationError, match="number is required"):
            client.voice.numbers.get("   ")

        client.close()

    def test_get_not_found_404(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{ENCODED_PHONE}",
            method="GET",
            status_code=404,
            json=mock_error_response("number_not_found", "This number isn't in your workspace."),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.voice.numbers.get(PHONE)

        assert exc_info.value.code == "number_not_found"
        assert exc_info.value.status_code == 404

        client.close()

    def test_update_sends_camel_case_body(
        self, live_api_key, mock_voice_number, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{ENCODED_PHONE}", method="PATCH", json=mock_voice_number
        )

        result = client.voice.numbers.update(
            PHONE,
            voice_enabled=True,
            voice_mode="agent",
            agent_id=AGENT_ID,
            idempotency_key="number-agent-1",
        )

        assert isinstance(result, VoiceNumber)
        assert result.voice_mode == "agent"

        request = httpx_mock.get_request()
        assert request.method == "PATCH"
        assert request.url.raw_path == f"/api/v1/voice/numbers/{ENCODED_PHONE}".encode()
        assert request.headers["Idempotency-Key"] == "number-agent-1"
        body = _body(request)
        assert body == {"voiceEnabled": True, "voiceMode": "agent", "agentId": AGENT_ID}
        assert "voiceAgentId" not in body
        assert "voice_enabled" not in body

        client.close()

    def test_update_sends_false_and_enum_values(
        self, live_api_key, mock_voice_number_off, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{NUMBER_ID}", method="PATCH", json=mock_voice_number_off
        )

        client.voice.numbers.update(NUMBER_ID, voice_enabled=False, voice_mode=VoiceMode.NONE)

        assert _body(httpx_mock.get_request()) == {"voiceEnabled": False, "voiceMode": "none"}

        client.close()

    def test_update_omits_unset_fields(
        self, live_api_key, mock_voice_number, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{NUMBER_ID}", method="PATCH", json=mock_voice_number
        )

        client.voice.numbers.update(NUMBER_ID, agent_id=AGENT_ID)

        assert _body(httpx_mock.get_request()) == {"agentId": AGENT_ID}

        client.close()

    def test_update_rejects_empty_number_before_request(self, live_api_key):
        client = Sendly(live_api_key)

        with pytest.raises(ValidationError, match="number is required"):
            client.voice.numbers.update("", voice_enabled=True)

        client.close()

    def test_update_does_not_validate_mode_client_side(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{NUMBER_ID}",
            method="PATCH",
            status_code=400,
            json=mock_error_response(
                "invalid_voice_mode", "voiceMode must be one of none, ring_dashboard, agent."
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.voice.numbers.update(NUMBER_ID, voice_mode="voicemail")

        assert exc_info.value.code == "invalid_voice_mode"
        assert not isinstance(exc_info.value, ValidationError)
        assert _body(httpx_mock.get_request()) == {"voiceMode": "voicemail"}

        client.close()

    def test_update_agent_disabled_409(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{NUMBER_ID}",
            method="PATCH",
            status_code=409,
            json=mock_error_response(
                "agent_disabled",
                "That agent is switched off. Turn it on before pointing a number at it.",
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.voice.numbers.update(NUMBER_ID, voice_mode="agent", agent_id=AGENT_ID)

        assert exc_info.value.code == "agent_disabled"
        assert exc_info.value.status_code == 409

        client.close()

    def test_register_emergency_address(
        self, live_api_key, mock_voice_number, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{ENCODED_PHONE}/emergency-address",
            method="POST",
            json=mock_voice_number,
        )

        result = client.voice.numbers.register_emergency_address(
            PHONE,
            street="500 Example Ave",
            unit="Suite 2",
            city="Austin",
            state="TX",
            zip="78701",
            country="US",
        )

        assert isinstance(result, VoiceNumber)
        assert result.emergency_address.status == "active"
        assert result.emergency_address.address.street == "500 Example Ave"
        assert result.emergency_address.address.country == "US"

        request = httpx_mock.get_request()
        assert request.method == "POST"
        assert (
            request.url.raw_path
            == f"/api/v1/voice/numbers/{ENCODED_PHONE}/emergency-address".encode()
        )
        assert AUTO_KEY.match(request.headers["Idempotency-Key"])
        assert _body(request) == {
            "street": "500 Example Ave",
            "unit": "Suite 2",
            "city": "Austin",
            "state": "TX",
            "zip": "78701",
            "country": "US",
        }

        client.close()

    def test_register_emergency_address_minimal_omits_optional_keys(
        self, live_api_key, mock_voice_number, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{NUMBER_ID}/emergency-address",
            method="POST",
            json=mock_voice_number,
        )

        client.voice.numbers.register_emergency_address(
            NUMBER_ID,
            street="500 Example Ave",
            city="Austin",
            state="TX",
            zip="78701",
            idempotency_key="e911-1",
        )

        request = httpx_mock.get_request()
        assert request.headers["Idempotency-Key"] == "e911-1"
        assert _body(request) == {
            "street": "500 Example Ave",
            "city": "Austin",
            "state": "TX",
            "zip": "78701",
        }

        client.close()

    @pytest.mark.parametrize("field", ["street", "city", "state", "zip"])
    def test_register_emergency_address_rejects_empty_fields(self, live_api_key, field):
        client = Sendly(live_api_key)

        address = {"street": "500 Example Ave", "city": "Austin", "state": "TX", "zip": "78701"}
        address[field] = " "

        with pytest.raises(ValidationError, match=f"{field} is required"):
            client.voice.numbers.register_emergency_address(PHONE, **address)

        client.close()

    def test_register_emergency_address_invalid_address_422_carries_suggestion(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key, max_retries=0)

        suggested = {
            "street": "500 Example Avenue",
            "city": "Austin",
            "state": "TX",
            "zip": "78701",
            "country": "US",
        }
        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{ENCODED_PHONE}/emergency-address",
            method="POST",
            status_code=422,
            json=mock_error_response(
                "invalid_address",
                "We couldn't validate that address. Check the suggestion.",
                suggested=suggested,
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.voice.numbers.register_emergency_address(
                PHONE, street="500 Example Av", city="Austin", state="TX", zip="78701"
            )

        assert exc_info.value.code == "invalid_address"
        assert exc_info.value.status_code == 422
        assert exc_info.value.response is not None
        assert exc_info.value.response.model_extra["suggested"] == suggested

        client.close()


class TestVoiceAgents:
    def test_list(self, api_key, mock_agent, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents",
            method="GET",
            json={"data": [mock_agent, {**mock_agent, "id": "second", "enabled": False}]},
        )

        result = client.voice.agents.list()

        assert isinstance(result, VoiceAgentListResponse)
        assert [a.id for a in result.data] == [AGENT_ID, "second"]
        assert result.data[1].enabled is False

        request = httpx_mock.get_request()
        assert request.method == "GET"
        assert request.url.path == "/api/v1/voice/agents"

        client.close()

    def test_create(self, live_api_key, mock_agent, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents", method="POST", status_code=201, json=mock_agent
        )

        result = client.voice.agents.create(
            "Front desk",
            enabled=True,
            voice="ashley",
            language="en-US",
            greeting="Thanks for calling Acme, how can I help?",
            instructions="Answer questions about opening hours.",
            tools=VoiceAgentTools(send_sms=False),
        )

        assert isinstance(result, VoiceAgent)
        assert result.id == AGENT_ID
        assert result.object == "voice_agent"
        assert result.name == "Front desk"
        assert result.enabled is True
        assert result.voice == "ashley"
        assert result.voice_label == "Ashley (US, warm)"
        assert result.language == "en-US"
        assert result.greeting == "Thanks for calling Acme, how can I help?"
        assert result.instructions == "Answer questions about opening hours."
        assert isinstance(result.tools, VoiceAgentTools)
        assert result.tools.send_sms is False
        assert result.tools.transfer_to is None
        assert result.can_send_sms is True
        assert result.calls_handled == 12
        assert result.avg_duration_secs == 74
        assert result.created_at == "2026-09-14T17:00:00.000Z"
        assert result.updated_at == "2026-09-14T17:05:00.000Z"
        assert "llm_model" not in VoiceAgent.model_fields

        request = httpx_mock.get_request()
        assert request.method == "POST"
        assert request.url.path == "/api/v1/voice/agents"
        assert AUTO_KEY.match(request.headers["Idempotency-Key"])
        assert _body(request) == {
            "name": "Front desk",
            "enabled": True,
            "voice": "ashley",
            "language": "en-US",
            "greeting": "Thanks for calling Acme, how can I help?",
            "instructions": "Answer questions about opening hours.",
            "tools": {"sendSms": False},
        }

        client.close()

    def test_create_minimal_sends_only_name(
        self, live_api_key, mock_agent, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents", method="POST", status_code=201, json=mock_agent
        )

        client.voice.agents.create(name="Front desk", idempotency_key="agent-front-desk")

        request = httpx_mock.get_request()
        assert request.headers["Idempotency-Key"] == "agent-front-desk"
        assert _body(request) == {"name": "Front desk"}

        client.close()

    def test_create_tools_dict_accepts_snake_and_camel_keys(
        self, live_api_key, mock_agent, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents", method="POST", status_code=201, json=mock_agent
        )
        httpx_mock.add_response(
            url=f"{BASE}/voice/agents", method="POST", status_code=201, json=mock_agent
        )

        client.voice.agents.create("Front desk", tools={"transfer_to": "+15125550190"})
        client.voice.agents.create("Front desk", tools={"sendSms": True, "ignored": 1})

        first, second = httpx_mock.get_requests()
        assert _body(first)["tools"] == {"transferTo": "+15125550190"}
        assert _body(second)["tools"] == {"sendSms": True}

        client.close()

    def test_create_rejects_empty_name_before_request(self, live_api_key):
        client = Sendly(live_api_key)

        with pytest.raises(ValidationError, match="name is required"):
            client.voice.agents.create("")

        with pytest.raises(ValidationError, match="name is required"):
            client.voice.agents.create("  ")

        client.close()

    def test_create_rejects_non_dict_tools_before_request(self, live_api_key):
        client = Sendly(live_api_key)

        with pytest.raises(ValidationError, match="tools"):
            client.voice.agents.create("Front desk", tools="sms")

        client.close()

    def test_create_agent_limit_409(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents",
            method="POST",
            status_code=409,
            json=mock_error_response(
                "agent_limit", "You've reached the agent limit for this workspace."
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.voice.agents.create("Front desk")

        assert exc_info.value.code == "agent_limit"
        assert exc_info.value.status_code == 409

        client.close()

    def test_get_percent_encodes_id(self, api_key, mock_agent, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/agent%2Fwith%20space", method="GET", json=mock_agent
        )

        result = client.voice.agents.get("agent/with space")

        assert result.id == AGENT_ID
        assert (
            httpx_mock.get_request().url.raw_path == b"/api/v1/voice/agents/agent%2Fwith%20space"
        )

        client.close()

    def test_get_rejects_empty_id_before_request(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="id is required"):
            client.voice.agents.get("")

        client.close()

    def test_update_sends_only_given_fields(
        self, live_api_key, mock_agent, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}",
            method="PATCH",
            json={**mock_agent, "greeting": "Hi, you have reached Acme."},
        )

        result = client.voice.agents.update(
            AGENT_ID,
            greeting="Hi, you have reached Acme.",
            enabled=False,
            idempotency_key="agent-update-1",
        )

        assert result.greeting == "Hi, you have reached Acme."

        request = httpx_mock.get_request()
        assert request.method == "PATCH"
        assert request.url.path == f"/api/v1/voice/agents/{AGENT_ID}"
        assert request.headers["Idempotency-Key"] == "agent-update-1"
        assert _body(request) == {"greeting": "Hi, you have reached Acme.", "enabled": False}

        client.close()

    def test_update_can_clear_transfer_number(
        self, live_api_key, mock_agent, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}", method="PATCH", json=mock_agent
        )

        client.voice.agents.update(AGENT_ID, tools=VoiceAgentTools(transfer_to=None))

        assert _body(httpx_mock.get_request()) == {"tools": {"transferTo": None}}

        client.close()

    def test_update_rejects_empty_id_before_request(self, live_api_key):
        client = Sendly(live_api_key)

        with pytest.raises(ValidationError, match="id is required"):
            client.voice.agents.update("", name="Front desk")

        client.close()

    def test_delete(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}",
            method="DELETE",
            json={"id": AGENT_ID, "object": "voice_agent", "deleted": True},
        )

        result = client.voice.agents.delete(AGENT_ID)

        assert isinstance(result, DeletedVoiceAgent)
        assert result.id == AGENT_ID
        assert result.object == "voice_agent"
        assert result.deleted is True

        request = httpx_mock.get_request()
        assert request.method == "DELETE"
        assert request.url.path == f"/api/v1/voice/agents/{AGENT_ID}"

        client.close()

    def test_delete_rejects_empty_id_before_request(self, live_api_key):
        client = Sendly(live_api_key)

        with pytest.raises(ValidationError, match="id is required"):
            client.voice.agents.delete("")

        client.close()

    def test_delete_agent_in_use_409(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}",
            method="DELETE",
            status_code=409,
            json=mock_error_response(
                "agent_in_use",
                "This agent answers 1 number(s). Point them elsewhere first.",
                numbers=[PHONE],
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.voice.agents.delete(AGENT_ID)

        assert exc_info.value.code == "agent_in_use"
        assert exc_info.value.status_code == 409
        assert not isinstance(exc_info.value, ValidationError)
        assert exc_info.value.response.model_extra["numbers"] == [PHONE]

        client.close()

    def test_forbidden_403(self, live_api_key, mock_error_response, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents",
            method="POST",
            status_code=403,
            json=mock_error_response(
                "forbidden", "Only workspace owners and admins can manage agents."
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.voice.agents.create("Front desk")

        assert exc_info.value.code == "forbidden"
        assert exc_info.value.status_code == 403

        client.close()


@pytest.fixture
def mock_websocket_agent(mock_agent):
    return {
        **mock_agent,
        "kind": "websocket",
        "connection": {
            "url": "wss://agent.example.com/calls",
            "audioFormat": "pcm16_16000",
            "hasAuthToken": True,
            "customParameters": {"tenant": "acme"},
        },
        "hasSigningSecret": True,
    }


class TestVoiceAgentsBringYourOwn:
    def test_sendly_agent_reads_kind_and_no_connection(self, api_key, mock_agent, httpx_mock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}",
            method="GET",
            json={**mock_agent, "kind": "sendly", "connection": None, "hasSigningSecret": False},
        )

        result = client.voice.agents.get(AGENT_ID)

        assert result.kind == VoiceAgentKind.SENDLY
        assert result.connection is None
        assert result.has_signing_secret is False
        assert result.signing_secret is None

        client.close()

    def test_older_response_defaults_new_fields(self, api_key, mock_agent, httpx_mock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}", method="GET", json=mock_agent
        )

        result = client.voice.agents.get(AGENT_ID)

        assert result.kind == "sendly"
        assert result.connection is None
        assert result.has_signing_secret is False

        client.close()

    def test_create_websocket_agent_sends_kind_and_connection(
        self, live_api_key, mock_websocket_agent, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents",
            method="POST",
            status_code=201,
            json={**mock_websocket_agent, "signingSecret": "whsec_agent_once"},
        )

        result = client.voice.agents.create(
            "Support line",
            kind=VoiceAgentKind.WEBSOCKET,
            connection={
                "url": "wss://agent.example.com/calls",
                "audio_format": "pcm16_16000",
                "auth_token": "tok_123",
                "custom_parameters": {"tenant_id": "acme"},
            },
        )

        request = httpx_mock.get_request()
        assert AUTO_KEY.match(request.headers["Idempotency-Key"])
        assert _body(request) == {
            "name": "Support line",
            "kind": "websocket",
            "connection": {
                "url": "wss://agent.example.com/calls",
                "audioFormat": "pcm16_16000",
                "authToken": "tok_123",
                "customParameters": {"tenant_id": "acme"},
            },
        }
        assert result.kind == VoiceAgentKind.WEBSOCKET
        assert isinstance(result.connection, VoiceAgentConnection)
        assert result.connection.url == "wss://agent.example.com/calls"
        assert result.connection.audio_format == "pcm16_16000"
        assert result.connection.has_auth_token is True
        assert result.connection.custom_parameters == {"tenant": "acme"}
        assert result.connection.base_url is None
        assert result.connection.uri is None
        assert result.has_signing_secret is True
        assert result.signing_secret == "whsec_agent_once"

        client.close()

    def test_create_custom_llm_agent_from_input_model(
        self, live_api_key, mock_agent, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents",
            method="POST",
            status_code=201,
            json={
                **mock_agent,
                "kind": "custom_llm",
                "connection": {
                    "baseUrl": "https://llm.example.com/v1",
                    "model": "support-v2",
                    "headerNames": ["X-Tenant"],
                    "hasApiKey": True,
                },
                "hasSigningSecret": True,
                "signingSecret": "whsec_agent_once",
            },
        )

        result = client.voice.agents.create(
            "Front desk",
            instructions="Answer questions about opening hours.",
            kind="custom_llm",
            connection=VoiceAgentCustomLlmConnectionInput(
                base_url="https://llm.example.com/v1",
                model="support-v2",
                api_key="sk_example",
                headers={"X-Tenant": "acme"},
            ),
        )

        assert _body(httpx_mock.get_request()) == {
            "name": "Front desk",
            "instructions": "Answer questions about opening hours.",
            "kind": "custom_llm",
            "connection": {
                "baseUrl": "https://llm.example.com/v1",
                "model": "support-v2",
                "apiKey": "sk_example",
                "headers": {"X-Tenant": "acme"},
            },
        }
        assert result.kind == VoiceAgentKind.CUSTOM_LLM
        assert result.connection.base_url == "https://llm.example.com/v1"
        assert result.connection.model == "support-v2"
        assert result.connection.header_names == ["X-Tenant"]
        assert result.connection.has_api_key is True
        assert result.connection.url is None

        client.close()

    def test_create_sip_agent_parses_sip_connection(
        self, live_api_key, mock_agent, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents",
            method="POST",
            status_code=201,
            json={
                **mock_agent,
                "kind": "sip",
                "connection": {
                    "uri": "sip:+15125550100@sip.example.com",
                    "transport": "tls",
                    "mediaEncryption": "require",
                    "username": "frontdesk",
                    "hasPassword": True,
                    "headers": {"X-Account": "42"},
                },
                "hasSigningSecret": True,
                "signingSecret": "whsec_agent_once",
            },
        )

        result = client.voice.agents.create(
            "Front desk",
            kind=VoiceAgentKind.SIP,
            connection=VoiceAgentSipConnectionInput(
                uri="sip:+15125550100@sip.example.com",
                transport=SipTransport.TLS,
                media_encryption="require",
                username="frontdesk",
                password="hunter2",
            ),
        )

        assert _body(httpx_mock.get_request())["connection"] == {
            "uri": "sip:+15125550100@sip.example.com",
            "transport": "tls",
            "mediaEncryption": "require",
            "username": "frontdesk",
            "password": "hunter2",
        }
        assert result.kind == "sip"
        assert result.connection.uri == "sip:+15125550100@sip.example.com"
        assert result.connection.transport == SipTransport.TLS
        assert result.connection.media_encryption == "require"
        assert result.connection.username == "frontdesk"
        assert result.connection.has_password is True
        assert result.connection.headers == {"X-Account": "42"}

        client.close()

    def test_unknown_kind_is_kept(self, api_key, mock_agent, httpx_mock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}",
            method="GET",
            json={**mock_agent, "kind": "future_kind", "connection": {"endpoint": "x"}},
        )

        result = client.voice.agents.get(AGENT_ID)

        assert result.kind == "future_kind"
        assert isinstance(result.connection, VoiceAgentConnection)

        client.close()

    def test_update_merges_connection_keeping_left_out_and_null_keys(
        self, live_api_key, mock_websocket_agent, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}", method="PATCH", json=mock_websocket_agent
        )
        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}", method="PATCH", json=mock_websocket_agent
        )

        client.voice.agents.update(
            AGENT_ID, connection={"authToken": None, "url": "wss://agent.example.com/v2"}
        )
        client.voice.agents.update(
            AGENT_ID, connection=VoiceAgentWebsocketConnectionInput(auth_token=None)
        )

        first, second = httpx_mock.get_requests()
        assert _body(first) == {
            "connection": {"authToken": None, "url": "wss://agent.example.com/v2"}
        }
        assert _body(second) == {"connection": {"authToken": None}}

        client.close()

    def test_update_rotate_signing_secret_sends_true_and_reads_secret(
        self, live_api_key, mock_websocket_agent, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}",
            method="PATCH",
            json={**mock_websocket_agent, "signingSecret": "whsec_rotated"},
        )

        result = client.voice.agents.update(
            AGENT_ID, rotate_signing_secret=True, idempotency_key="rotate-1"
        )

        request = httpx_mock.get_request()
        assert request.headers["Idempotency-Key"] == "rotate-1"
        assert _body(request) == {"rotateSigningSecret": True}
        assert result.signing_secret == "whsec_rotated"

        client.close()

    def test_update_never_sends_rotate_false(
        self, live_api_key, mock_agent, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}", method="PATCH", json=mock_agent
        )

        client.voice.agents.update(AGENT_ID, name="Reception", rotate_signing_secret=False)

        assert _body(httpx_mock.get_request()) == {"name": "Reception"}

        client.close()

    def test_update_switches_kind_with_connection(
        self, live_api_key, mock_agent, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}", method="PATCH", json=mock_agent
        )
        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}", method="PATCH", json=mock_agent
        )

        client.voice.agents.update(
            AGENT_ID,
            kind="sip",
            connection={"uri": "sip:+15125550100@sip.example.com", "media_encryption": "allow"},
            rotate_signing_secret=True,
        )
        client.voice.agents.update(AGENT_ID, kind=VoiceAgentKind.SENDLY)

        first, second = httpx_mock.get_requests()
        assert _body(first) == {
            "kind": "sip",
            "connection": {
                "uri": "sip:+15125550100@sip.example.com",
                "mediaEncryption": "allow",
            },
            "rotateSigningSecret": True,
        }
        assert _body(second) == {"kind": "sendly"}

        client.close()

    def test_rejects_non_dict_connection_before_request(self, live_api_key):
        client = Sendly(live_api_key)

        with pytest.raises(ValidationError, match="connection"):
            client.voice.agents.create("Front desk", kind="websocket", connection="wss://x")

        with pytest.raises(ValidationError, match="connection"):
            client.voice.agents.update(AGENT_ID, connection=["wss://x"])

        client.close()

    def test_byo_agents_not_enabled_403(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents",
            method="POST",
            status_code=403,
            json=mock_error_response(
                "byo_agents_not_enabled", "Your own agents are not switched on for this workspace."
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.voice.agents.create(
                "Front desk", kind="websocket", connection={"url": "wss://agent.example.com"}
            )

        assert exc_info.value.code == "byo_agents_not_enabled"
        assert exc_info.value.status_code == 403

        client.close()

    def test_invalid_connection_400_is_validation_error(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}",
            method="PATCH",
            status_code=400,
            json=mock_error_response(
                "invalid_request", "connection.url: must start with wss://"
            ),
        )

        with pytest.raises(ValidationError) as exc_info:
            client.voice.agents.update(AGENT_ID, connection={"url": "ws://agent.example.com"})

        assert "connection.url" in str(exc_info.value)

        client.close()

    async def test_async_create_and_rotate(
        self, live_api_key, mock_websocket_agent, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents",
            method="POST",
            status_code=201,
            json={**mock_websocket_agent, "signingSecret": "whsec_agent_once"},
        )
        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}",
            method="PATCH",
            json={**mock_websocket_agent, "signingSecret": "whsec_rotated"},
        )

        created = await client.voice.agents.create(
            "Support line",
            kind="websocket",
            connection=VoiceAgentWebsocketConnectionInput(url="wss://agent.example.com/calls"),
        )
        rotated = await client.voice.agents.update(
            AGENT_ID, connection={"custom_parameters": None}, rotate_signing_secret=True
        )

        assert created.signing_secret == "whsec_agent_once"
        assert rotated.signing_secret == "whsec_rotated"
        first, second = httpx_mock.get_requests()
        assert _body(first) == {
            "name": "Support line",
            "kind": "websocket",
            "connection": {"url": "wss://agent.example.com/calls"},
        }
        assert _body(second) == {
            "connection": {"customParameters": None},
            "rotateSigningSecret": True,
        }

        await client.close()


@pytest.fixture
def mock_agent_test():
    return {
        "ok": True,
        "outcome": "ok",
        "message": "Your agent's server answered in 84 ms.",
        "status": 200,
        "latencyMs": 84,
        "signed": False,
        "steps": [
            {"step": "address", "ok": True, "detail": "sip.example.com points to a public server."},
            {
                "step": "connect",
                "ok": True,
                "detail": "Connected over TLS to sip.example.com:5061 in 41 ms.",
            },
            {"step": "reply", "ok": True, "detail": "SIP 200 OK"},
        ],
    }


class TestVoiceAgentsConnectionTest:
    def test_sends_empty_body_without_idempotency_key(
        self, live_api_key, mock_agent_test, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}/test", method="POST", json=mock_agent_test
        )

        result = client.voice.agents.test(AGENT_ID)

        assert isinstance(result, VoiceAgentTest)
        assert result.ok is True
        assert result.outcome == VoiceAgentTestOutcome.OK
        assert result.status == 200
        assert result.latency_ms == 84
        assert result.signed is False
        assert [step.step for step in result.steps] == ["address", "connect", "reply"]
        assert isinstance(result.steps[1], VoiceAgentTestStep)
        assert result.steps[1].step == VoiceAgentTestStepName.CONNECT
        assert result.steps[2].detail == "SIP 200 OK"

        request = httpx_mock.get_request()
        assert request.method == "POST"
        assert request.url.path == f"/api/v1/voice/agents/{AGENT_ID}/test"
        assert _body(request) == {}
        assert "Idempotency-Key" not in request.headers

        client.close()

    def test_sends_kind_connection_and_instructions(
        self, live_api_key, mock_agent_test, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}/test", method="POST", json=mock_agent_test
        )
        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}/test", method="POST", json=mock_agent_test
        )

        client.voice.agents.test(
            AGENT_ID,
            kind=VoiceAgentKind.CUSTOM_LLM,
            connection={
                "base_url": "https://llm.example.com/v1",
                "model": "support-1",
                "api_key": "sk_example",
            },
            instructions="Answer questions about opening hours.",
        )
        client.voice.agents.test(
            AGENT_ID,
            kind="sip",
            connection=VoiceAgentSipConnectionInput(
                uri="sip:+15125550100@sip.example.com", transport=SipTransport.TLS
            ),
        )

        first, second = httpx_mock.get_requests()
        assert _body(first) == {
            "kind": "custom_llm",
            "connection": {
                "baseUrl": "https://llm.example.com/v1",
                "model": "support-1",
                "apiKey": "sk_example",
            },
            "instructions": "Answer questions about opening hours.",
        }
        assert _body(second) == {
            "kind": "sip",
            "connection": {"uri": "sip:+15125550100@sip.example.com", "transport": "tls"},
        }
        assert "Idempotency-Key" not in first.headers

        client.close()

    def test_failed_test_parses_and_keeps_unknown_values(
        self, live_api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}/test",
            method="POST",
            json={
                "ok": False,
                "outcome": "certificate_expired",
                "message": "Your agent's certificate has expired.",
                "status": None,
                "latencyMs": None,
                "signed": True,
                "steps": [
                    {"step": "address", "ok": True, "detail": "agent.example.com is public."},
                    {"step": "handshake", "ok": False, "detail": "The certificate expired."},
                ],
            },
        )

        result = client.voice.agents.test(AGENT_ID)

        assert result.ok is False
        assert result.outcome == "certificate_expired"
        assert result.status is None
        assert result.latency_ms is None
        assert result.signed is True
        assert result.steps[1].step == "handshake"
        assert result.steps[1].ok is False

        client.close()

    def test_requires_id_and_dict_connection(self, live_api_key):
        client = Sendly(live_api_key)

        with pytest.raises(ValidationError):
            client.voice.agents.test("")

        with pytest.raises(ValidationError, match="connection"):
            client.voice.agents.test(AGENT_ID, connection="wss://agent.example.com")

        client.close()

    def test_rate_limited_429(self, live_api_key, mock_error_response, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}/test",
            method="POST",
            status_code=429,
            json=mock_error_response(
                "rate_limit_exceeded", "Too many agent tests. Try again in a minute."
            ),
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.voice.agents.test(AGENT_ID)

        assert exc_info.value.code == "rate_limit_exceeded"

        client.close()

    def test_agent_not_found_404(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}/test",
            method="POST",
            status_code=404,
            json=mock_error_response("agent_not_found", "Agent not found."),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.voice.agents.test(AGENT_ID)

        assert exc_info.value.code == "agent_not_found"

        client.close()

    async def test_async_test(self, live_api_key, mock_agent_test, httpx_mock: HTTPXMock):
        client = AsyncSendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}/test", method="POST", json=mock_agent_test
        )

        result = await client.voice.agents.test(
            AGENT_ID, kind="websocket", connection={"url": "wss://agent.example.com/calls"}
        )

        assert result.ok is True
        request = httpx_mock.get_request()
        assert _body(request) == {
            "kind": "websocket",
            "connection": {"url": "wss://agent.example.com/calls"},
        }
        assert "Idempotency-Key" not in request.headers

        await client.close()


class TestVoices:
    def test_list(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/voices",
            method="GET",
            json={
                "data": [
                    {"id": "ashley", "label": "Ashley (US, warm)", "language": "en"},
                    {"id": "diego", "label": "Diego (Spanish, MX)", "language": "es"},
                ]
            },
        )

        result = client.voice.voices.list()

        assert isinstance(result, VoiceListResponse)
        assert [v.id for v in result.data] == ["ashley", "diego"]
        assert isinstance(result.data[0], Voice)
        assert result.data[1].language == "es"
        assert set(Voice.model_fields) == {"id", "label", "language"}

        request = httpx_mock.get_request()
        assert request.method == "GET"
        assert request.url.path == "/api/v1/voice/voices"

        client.close()

    def test_voice_not_enabled_404(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/voice/voices",
            method="GET",
            status_code=404,
            json=mock_error_response("voice_not_enabled", "Voice is not enabled for your account."),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.voice.voices.list()

        assert exc_info.value.code == "voice_not_enabled"
        assert exc_info.value.status_code == 404

        client.close()


class TestAsyncVoice:
    async def test_async_numbers(
        self, live_api_key, mock_voice_number, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers", method="GET", json={"data": [mock_voice_number]}
        )
        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{ENCODED_PHONE}", method="GET", json=mock_voice_number
        )
        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{ENCODED_PHONE}", method="PATCH", json=mock_voice_number
        )
        httpx_mock.add_response(
            url=f"{BASE}/voice/numbers/{ENCODED_PHONE}/emergency-address",
            method="POST",
            json=mock_voice_number,
        )

        listing = await client.voice.numbers.list()
        fetched = await client.voice.numbers.get(PHONE)
        updated = await client.voice.numbers.update(
            PHONE, voice_mode=VoiceMode.AGENT, agent_id=AGENT_ID
        )
        registered = await client.voice.numbers.register_emergency_address(
            PHONE, street="500 Example Ave", city="Austin", state="TX", zip="78701"
        )

        assert listing.data[0].id == NUMBER_ID
        assert fetched.phone_number == PHONE
        assert updated.voice_mode == "agent"
        assert registered.emergency_address.status == "active"

        requests = httpx_mock.get_requests()
        assert [(r.method, r.url.raw_path) for r in requests] == [
            ("GET", b"/api/v1/voice/numbers"),
            ("GET", f"/api/v1/voice/numbers/{ENCODED_PHONE}".encode()),
            ("PATCH", f"/api/v1/voice/numbers/{ENCODED_PHONE}".encode()),
            ("POST", f"/api/v1/voice/numbers/{ENCODED_PHONE}/emergency-address".encode()),
        ]
        assert _body(requests[2]) == {"voiceMode": "agent", "agentId": AGENT_ID}
        assert AUTO_KEY.match(requests[3].headers["Idempotency-Key"])
        assert _body(requests[3]) == {
            "street": "500 Example Ave",
            "city": "Austin",
            "state": "TX",
            "zip": "78701",
        }

        await client.close()

    async def test_async_agents_and_voices(
        self, live_api_key, mock_agent, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents", method="GET", json={"data": [mock_agent]}
        )
        httpx_mock.add_response(
            url=f"{BASE}/voice/agents", method="POST", status_code=201, json=mock_agent
        )
        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}", method="GET", json=mock_agent
        )
        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}", method="PATCH", json=mock_agent
        )
        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}",
            method="DELETE",
            json={"id": AGENT_ID, "object": "voice_agent", "deleted": True},
        )
        httpx_mock.add_response(
            url=f"{BASE}/voice/voices",
            method="GET",
            json={"data": [{"id": "ashley", "label": "Ashley (US, warm)", "language": "en"}]},
        )

        listing = await client.voice.agents.list()
        created = await client.voice.agents.create(
            "Front desk", voice="ashley", tools={"send_sms": False}
        )
        fetched = await client.voice.agents.get(AGENT_ID)
        updated = await client.voice.agents.update(AGENT_ID, name="Reception")
        deleted = await client.voice.agents.delete(AGENT_ID)
        voices = await client.voice.voices.list()

        assert listing.data[0].id == AGENT_ID
        assert created.voice_label == "Ashley (US, warm)"
        assert fetched.id == AGENT_ID
        assert updated.id == AGENT_ID
        assert deleted.deleted is True
        assert voices.data[0].id == "ashley"

        requests = httpx_mock.get_requests()
        assert [(r.method, r.url.path) for r in requests] == [
            ("GET", "/api/v1/voice/agents"),
            ("POST", "/api/v1/voice/agents"),
            ("GET", f"/api/v1/voice/agents/{AGENT_ID}"),
            ("PATCH", f"/api/v1/voice/agents/{AGENT_ID}"),
            ("DELETE", f"/api/v1/voice/agents/{AGENT_ID}"),
            ("GET", "/api/v1/voice/voices"),
        ]
        assert AUTO_KEY.match(requests[1].headers["Idempotency-Key"])
        assert _body(requests[1]) == {
            "name": "Front desk",
            "voice": "ashley",
            "tools": {"sendSms": False},
        }
        assert _body(requests[3]) == {"name": "Reception"}

        await client.close()

    async def test_async_rejects_empty_inputs(self, live_api_key):
        client = AsyncSendly(live_api_key)

        with pytest.raises(ValidationError, match="number is required"):
            await client.voice.numbers.get("")

        with pytest.raises(ValidationError, match="zip is required"):
            await client.voice.numbers.register_emergency_address(
                PHONE, street="500 Example Ave", city="Austin", state="TX", zip=""
            )

        with pytest.raises(ValidationError, match="name is required"):
            await client.voice.agents.create("")

        with pytest.raises(ValidationError, match="id is required"):
            await client.voice.agents.delete("")

        await client.close()

    async def test_async_agent_in_use_409(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/voice/agents/{AGENT_ID}",
            method="DELETE",
            status_code=409,
            json=mock_error_response(
                "agent_in_use",
                "This agent answers 2 number(s). Point them elsewhere first.",
                numbers=[PHONE, "+15555550199"],
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            await client.voice.agents.delete(AGENT_ID)

        assert exc_info.value.code == "agent_in_use"
        assert exc_info.value.response.model_extra["numbers"] == [PHONE, "+15555550199"]

        await client.close()
