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
from sendly.errors import SendlyError, ValidationError
from sendly.types import (
    DeletedVoiceAgent,
    EmergencyAddress,
    Voice,
    VoiceAgent,
    VoiceAgentListResponse,
    VoiceAgentTools,
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
