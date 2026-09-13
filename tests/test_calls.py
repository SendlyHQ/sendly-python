"""
Tests for voice calls (create, list, get, hangup, recording)
"""

import json
import re

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import (
    AuthenticationError,
    InsufficientCreditsError,
    NotFoundError,
    SendlyError,
    ValidationError,
)
from sendly.types import (
    Call,
    CallBilling,
    CallDirection,
    CallHandledBy,
    CallKind,
    CallListResponse,
    CallRecording,
    CallStatus,
    CallTranscriptLine,
    OwnedNumbersResponse,
)

BASE = "https://sendly.live/api/v1"
AUTO_KEY = re.compile(r"^sendly-python-retry-[0-9a-f-]{36}$")
CALL_ID = "6f1c2d3e-4a5b-4c6d-8e9f-0a1b2c3d4e5f"
AGENT_ID = "3c4d5e6f-7081-4293-a4b5-c6d7e8f90a1b"


def _body(httpx_mock: HTTPXMock):
    return json.loads(httpx_mock.get_request().read().decode())


@pytest.fixture
def mock_call():
    return {
        "id": CALL_ID,
        "object": "call",
        "kind": "pstn",
        "direction": "outbound",
        "status": "ringing",
        "handledBy": "agent",
        "agentId": AGENT_ID,
        "from": "+15555550188",
        "to": "+15555550123",
        "callerName": "Front Desk",
        "calleeName": "+15555550123",
        "startedAt": "2026-09-12T14:03:11.000Z",
        "answeredAt": None,
        "endedAt": None,
        "durationSecs": 0,
        "creditsCharged": 0,
        "billing": "metered",
        "hangupClass": None,
        "recordingStatus": None,
        "metadata": {"crmId": "lead_8812"},
    }


@pytest.fixture
def mock_completed_call(mock_call):
    return {
        **mock_call,
        "status": "completed",
        "answeredAt": "2026-09-12T14:03:19.000Z",
        "endedAt": "2026-09-12T14:05:02.000Z",
        "durationSecs": 103,
        "creditsCharged": 20,
        "billing": "settled",
        "hangupClass": "agent_agent_hangup",
        "recordingStatus": "ready",
    }


class TestCallsCreate:
    def test_create(self, live_api_key, mock_call, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls", method="POST", status_code=201, json=mock_call
        )

        result = client.calls.create(
            to="+15555550123",
            agent_id=AGENT_ID,
            from_="+15555550188",
            context="You are calling Jordan to confirm the 3pm appointment on Tuesday.",
            metadata={"crmId": "lead_8812"},
        )

        assert isinstance(result, Call)
        assert result.id == CALL_ID
        assert result.object == "call"
        assert result.status == "ringing"
        assert result.status == CallStatus.RINGING
        assert result.kind == CallKind.PSTN
        assert result.direction == CallDirection.OUTBOUND
        assert result.handled_by == CallHandledBy.AGENT
        assert result.agent_id == AGENT_ID
        assert result.from_ == "+15555550188"
        assert result.to == "+15555550123"
        assert result.caller_name == "Front Desk"
        assert result.callee_name == "+15555550123"
        assert result.started_at == "2026-09-12T14:03:11.000Z"
        assert result.answered_at is None
        assert result.ended_at is None
        assert result.duration_secs == 0
        assert result.credits_charged == 0
        assert result.billing == CallBilling.METERED
        assert result.hangup_class is None
        assert result.recording_status is None
        assert result.metadata == {"crmId": "lead_8812"}
        assert result.transcript is None

        request = httpx_mock.get_request()
        assert request.method == "POST"
        assert request.url.path == "/api/v1/calls"
        assert AUTO_KEY.match(request.headers["Idempotency-Key"])
        assert json.loads(request.read().decode()) == {
            "to": "+15555550123",
            "agentId": AGENT_ID,
            "from": "+15555550188",
            "context": "You are calling Jordan to confirm the 3pm appointment on Tuesday.",
            "metadata": {"crmId": "lead_8812"},
        }

        client.close()

    def test_create_minimal_omits_optional_keys(
        self, live_api_key, mock_call, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls", method="POST", status_code=201, json=mock_call
        )

        client.calls.create(to="+15555550123", agent_id=AGENT_ID)

        body = _body(httpx_mock)
        assert body == {"to": "+15555550123", "agentId": AGENT_ID}
        assert "from" not in body
        assert "context" not in body
        assert "metadata" not in body

        client.close()

    def test_create_with_explicit_idempotency_key(
        self, live_api_key, mock_call, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls", method="POST", status_code=201, json=mock_call
        )

        client.calls.create(to="+15555550123", agent_id=AGENT_ID, idempotency_key="call-lead-8812")

        assert httpx_mock.get_request().headers["Idempotency-Key"] == "call-lead-8812"

        client.close()

    def test_create_defaults_metadata_to_empty_dict(
        self, live_api_key, mock_call, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        payload = dict(mock_call)
        del payload["metadata"]
        httpx_mock.add_response(url=f"{BASE}/calls", method="POST", status_code=201, json=payload)

        result = client.calls.create(to="+15555550123", agent_id=AGENT_ID)

        assert result.metadata == {}

        client.close()

    def test_create_rejects_empty_to_before_request(self, live_api_key):
        client = Sendly(live_api_key)

        with pytest.raises(ValidationError, match="to is required"):
            client.calls.create(to="", agent_id=AGENT_ID)

        with pytest.raises(ValidationError, match="to is required"):
            client.calls.create(to="   ", agent_id=AGENT_ID)

        client.close()

    def test_create_rejects_empty_agent_id_before_request(self, live_api_key):
        client = Sendly(live_api_key)

        with pytest.raises(ValidationError, match="agent_id is required"):
            client.calls.create(to="+15555550123", agent_id="")

        client.close()

    def test_create_rejects_non_dict_metadata_before_request(self, live_api_key):
        client = Sendly(live_api_key)

        with pytest.raises(ValidationError, match="metadata"):
            client.calls.create(to="+15555550123", agent_id=AGENT_ID, metadata="crmId=lead")

        client.close()

    def test_create_does_not_validate_phone_format(
        self, live_api_key, mock_call, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls", method="POST", status_code=201, json=mock_call
        )

        client.calls.create(to="5555550123", agent_id=AGENT_ID)

        assert _body(httpx_mock)["to"] == "5555550123"

        client.close()

    def test_create_insufficient_credits_402(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/calls",
            method="POST",
            status_code=402,
            json=mock_error_response(
                "insufficient_credits",
                "Calls cost 10 credits a minute. Current balance: 4.",
                creditsNeeded=10,
                currentBalance=4,
            ),
        )

        with pytest.raises(InsufficientCreditsError) as exc_info:
            client.calls.create(to="+15555550123", agent_id=AGENT_ID)

        assert exc_info.value.code == "insufficient_credits"
        assert exc_info.value.status_code == 402
        assert exc_info.value.credits_needed == 10
        assert exc_info.value.current_balance == 4

        client.close()

    def test_create_e911_required_428(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/calls",
            method="POST",
            status_code=428,
            json=mock_error_response(
                "e911_required",
                "Register an emergency address for this number before placing calls. "
                "It's required by US law.",
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.calls.create(to="+15555550123", agent_id=AGENT_ID)

        assert exc_info.value.code == "e911_required"
        assert exc_info.value.status_code == 428

        client.close()

    def test_create_lines_busy_409(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/calls",
            method="POST",
            status_code=409,
            json=mock_error_response(
                "lines_busy", "Your workspace's lines are all in use. Try again in a moment."
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.calls.create(to="+15555550123", agent_id=AGENT_ID)

        assert exc_info.value.code == "lines_busy"
        assert exc_info.value.status_code == 409

        client.close()

    def test_create_agent_required_400(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/calls",
            method="POST",
            status_code=400,
            json=mock_error_response(
                "agent_required",
                "Calls placed over the API are answered by an AI agent. Pass agentId.",
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.calls.create(to="+15555550123", agent_id="agent")

        assert exc_info.value.code == "agent_required"
        assert not isinstance(exc_info.value, ValidationError)

        client.close()

    def test_create_live_key_required_403(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/calls",
            method="POST",
            status_code=403,
            json=mock_error_response("live_key_required", "Phone calls need a live API key."),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.calls.create(to="+15555550123", agent_id=AGENT_ID)

        assert exc_info.value.code == "live_key_required"
        assert exc_info.value.status_code == 403
        assert not isinstance(exc_info.value, AuthenticationError)

        client.close()

    def test_create_voice_not_enabled_404(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/calls",
            method="POST",
            status_code=404,
            json=mock_error_response("voice_not_enabled", "Voice is not enabled for your account."),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.calls.create(to="+15555550123", agent_id=AGENT_ID)

        assert exc_info.value.code == "voice_not_enabled"
        assert exc_info.value.status_code == 404
        assert not isinstance(exc_info.value, NotFoundError)

        client.close()


class TestCallsList:
    def test_list(self, api_key, mock_call, mock_completed_call, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls",
            method="GET",
            json={
                "data": [mock_call, mock_completed_call],
                "pagination": {"total": 132, "limit": 50, "offset": 0, "hasMore": True},
            },
        )

        result = client.calls.list()

        assert isinstance(result, CallListResponse)
        assert len(result.data) == 2
        assert result.data[0].status == CallStatus.RINGING
        assert result.data[1].status == CallStatus.COMPLETED
        assert result.data[1].billing == CallBilling.SETTLED
        assert result.data[1].duration_secs == 103
        assert result.data[1].hangup_class == "agent_agent_hangup"
        assert result.pagination.total == 132
        assert result.pagination.limit == 50
        assert result.pagination.offset == 0
        assert result.pagination.has_more is True

        request = httpx_mock.get_request()
        assert request.method == "GET"
        assert request.url.path == "/api/v1/calls"
        assert str(request.url.query, "utf-8") == ""
        assert "Idempotency-Key" not in request.headers

        client.close()

    def test_list_encodes_filters(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            method="GET",
            url=re.compile(rf"^{re.escape(BASE)}/calls\?.*$"),
            json={
                "data": [],
                "pagination": {"total": 0, "limit": 20, "offset": 40, "hasMore": False},
            },
        )

        result = client.calls.list(
            limit=20,
            offset=40,
            status=CallStatus.COMPLETED,
            direction="outbound",
            kind=CallKind.PSTN,
            agent_id=AGENT_ID,
            to="+15555550123",
            from_="+15555550188",
        )

        assert result.data == []
        assert result.pagination.has_more is False

        params = httpx_mock.get_request().url.params
        assert params["limit"] == "20"
        assert params["offset"] == "40"
        assert params["status"] == "completed"
        assert params["direction"] == "outbound"
        assert params["kind"] == "pstn"
        assert params["agentId"] == AGENT_ID
        assert params["to"] == "+15555550123"
        assert params["from"] == "+15555550188"
        assert "from_" not in params
        assert "agent_id" not in params

        client.close()

    def test_list_omits_unset_filters(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            method="GET",
            url=f"{BASE}/calls?status=ringing",
            json={
                "data": [],
                "pagination": {"total": 0, "limit": 50, "offset": 0, "hasMore": False},
            },
        )

        client.calls.list(status="ringing")

        assert dict(httpx_mock.get_request().url.params) == {"status": "ringing"}

        client.close()

    def test_list_invalid_request_400(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            method="GET",
            url=f"{BASE}/calls?limit=500",
            status_code=400,
            json=mock_error_response("invalid_request", "limit must be between 1 and 100"),
        )

        with pytest.raises(ValidationError) as exc_info:
            client.calls.list(limit=500)

        assert exc_info.value.code == "invalid_request"

        client.close()

    def test_list_invalid_response(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(url=f"{BASE}/calls", method="GET", json={"calls": []})

        with pytest.raises(SendlyError) as exc_info:
            client.calls.list()

        assert exc_info.value.code == "invalid_response"

        client.close()


class TestCallsGet:
    def test_get_agent_call_with_transcript(
        self, api_key, mock_completed_call, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}",
            method="GET",
            json={
                **mock_completed_call,
                "transcript": [
                    {"speaker": "agent", "text": "Hi Jordan, this is Front Desk.", "atMs": 0},
                    {"speaker": "caller", "text": "Yes, 3pm works.", "atMs": 4200},
                ],
            },
        )

        result = client.calls.get(CALL_ID)

        assert isinstance(result, Call)
        assert result.id == CALL_ID
        assert result.status == CallStatus.COMPLETED
        assert result.recording_status == "ready"
        assert result.transcript is not None
        assert len(result.transcript) == 2
        assert isinstance(result.transcript[0], CallTranscriptLine)
        assert result.transcript[0].speaker == "agent"
        assert result.transcript[1].speaker == "caller"
        assert result.transcript[1].text == "Yes, 3pm works."
        assert result.transcript[1].at_ms == 4200

        request = httpx_mock.get_request()
        assert request.method == "GET"
        assert request.url.path == f"/api/v1/calls/{CALL_ID}"
        assert "Idempotency-Key" not in request.headers

        client.close()

    def test_get_agent_call_with_empty_transcript(
        self, api_key, mock_completed_call, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}",
            method="GET",
            json={**mock_completed_call, "transcript": []},
        )

        result = client.calls.get(CALL_ID)

        assert result.transcript == []

        client.close()

    def test_get_dashboard_call_has_no_transcript(
        self, api_key, mock_completed_call, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}",
            method="GET",
            json={
                **mock_completed_call,
                "direction": "inbound",
                "handledBy": "dashboard",
                "agentId": None,
                "hangupClass": "caller_hung_up",
            },
        )

        result = client.calls.get(CALL_ID)

        assert result.handled_by == CallHandledBy.DASHBOARD
        assert result.direction == CallDirection.INBOUND
        assert result.agent_id is None
        assert result.transcript is None

        client.close()

    def test_get_internal_call_has_no_numbers(self, api_key, mock_call, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}",
            method="GET",
            json={
                **mock_call,
                "kind": "internal",
                "handledBy": "dashboard",
                "agentId": None,
                "from": None,
                "to": None,
                "callerName": "Sam",
                "calleeName": "Lee",
                "billing": "unbilled",
                "metadata": {},
            },
        )

        result = client.calls.get(CALL_ID)

        assert result.kind == CallKind.INTERNAL
        assert result.from_ is None
        assert result.to is None
        assert result.billing == CallBilling.UNBILLED
        assert result.metadata == {}

        client.close()

    def test_get_percent_encodes_id(self, api_key, mock_call, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls/call%2Fwith%20space", method="GET", json=mock_call
        )

        client.calls.get("call/with space")

        assert httpx_mock.get_request().url.raw_path == b"/api/v1/calls/call%2Fwith%20space"

        client.close()

    def test_get_rejects_empty_id_before_request(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="id is required"):
            client.calls.get("")

        client.close()

    def test_get_not_found_404(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/calls/other",
            method="GET",
            status_code=404,
            json=mock_error_response(
                "call_not_found", "No call with that id is in this workspace."
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.calls.get("other")

        assert exc_info.value.code == "call_not_found"
        assert exc_info.value.status_code == 404

        client.close()

    def test_get_insufficient_permissions_403(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}",
            method="GET",
            status_code=403,
            json=mock_error_response("insufficient_permissions", "Missing scope calls:read"),
        )

        with pytest.raises(AuthenticationError) as exc_info:
            client.calls.get(CALL_ID)

        assert exc_info.value.code == "insufficient_permissions"

        client.close()


class TestCallsHangup:
    def test_hangup_ringing_becomes_cancelled(
        self, live_api_key, mock_call, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}/hangup",
            method="POST",
            json={
                **mock_call,
                "status": "cancelled",
                "endedAt": "2026-09-12T14:03:30.000Z",
                "billing": "settled",
                "hangupClass": "caller_cancelled",
            },
        )

        result = client.calls.hangup(CALL_ID)

        assert isinstance(result, Call)
        assert result.status == CallStatus.CANCELLED
        assert result.hangup_class == "caller_cancelled"
        assert result.billing == CallBilling.SETTLED
        assert result.credits_charged == 0

        request = httpx_mock.get_request()
        assert request.method == "POST"
        assert request.url.path == f"/api/v1/calls/{CALL_ID}/hangup"
        assert AUTO_KEY.match(request.headers["Idempotency-Key"])
        assert json.loads(request.read().decode()) == {}

        client.close()

    def test_hangup_active_becomes_completed(
        self, live_api_key, mock_completed_call, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}/hangup",
            method="POST",
            json={**mock_completed_call, "hangupClass": "normal"},
        )

        result = client.calls.hangup(CALL_ID, idempotency_key="hangup-1")

        assert result.status == CallStatus.COMPLETED
        assert result.hangup_class == "normal"
        assert httpx_mock.get_request().headers["Idempotency-Key"] == "hangup-1"

        client.close()

    def test_hangup_rejects_empty_id_before_request(self, live_api_key):
        client = Sendly(live_api_key)

        with pytest.raises(ValidationError, match="id is required"):
            client.calls.hangup("")

        client.close()

    def test_hangup_not_found_404(self, live_api_key, mock_error_response, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/calls/other/hangup",
            method="POST",
            status_code=404,
            json=mock_error_response(
                "call_not_found", "No call with that id is in this workspace."
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.calls.hangup("other")

        assert exc_info.value.code == "call_not_found"

        client.close()

    def test_hangup_forbidden_403(self, live_api_key, mock_error_response, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}/hangup",
            method="POST",
            status_code=403,
            json=mock_error_response("forbidden", "Your role can't end calls."),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.calls.hangup(CALL_ID)

        assert exc_info.value.code == "forbidden"
        assert exc_info.value.status_code == 403

        client.close()


class TestCallsRecording:
    def test_recording_ready(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}/recording",
            method="GET",
            json={
                "callId": CALL_ID,
                "status": "ready",
                "url": "https://sendly.live/recordings/signed?sig=abc",
                "expiresAt": "2026-09-12T14:10:00.000Z",
                "contentType": "audio/ogg",
            },
        )

        result = client.calls.recording(CALL_ID)

        assert isinstance(result, CallRecording)
        assert result.call_id == CALL_ID
        assert result.status == "ready"
        assert result.url == "https://sendly.live/recordings/signed?sig=abc"
        assert result.expires_at == "2026-09-12T14:10:00.000Z"
        assert result.content_type == "audio/ogg"

        request = httpx_mock.get_request()
        assert request.method == "GET"
        assert request.url.path == f"/api/v1/calls/{CALL_ID}/recording"
        assert "Idempotency-Key" not in request.headers

        client.close()

    def test_recording_none_has_no_url(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}/recording",
            method="GET",
            json={
                "callId": CALL_ID,
                "status": "none",
                "url": None,
                "expiresAt": None,
                "contentType": None,
            },
        )

        result = client.calls.recording(CALL_ID)

        assert result.status == "none"
        assert result.url is None
        assert result.expires_at is None
        assert result.content_type is None

        client.close()

    def test_recording_in_progress_has_no_url(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}/recording",
            method="GET",
            json={"callId": CALL_ID, "status": "recording"},
        )

        result = client.calls.recording(CALL_ID)

        assert result.status == "recording"
        assert result.url is None
        assert result.expires_at is None

        client.close()

    def test_recording_rejects_empty_id_before_request(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="id is required"):
            client.calls.recording("")

        client.close()

    def test_recording_not_found_404(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/calls/other/recording",
            method="GET",
            status_code=404,
            json=mock_error_response(
                "call_not_found", "No call with that id is in this workspace."
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.calls.recording("other")

        assert exc_info.value.code == "call_not_found"

        client.close()


class TestNumbersVoiceFields:
    def test_owned_numbers_expose_voice_fields(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/numbers",
            method="GET",
            json={
                "numbers": [
                    {
                        "id": "num_123",
                        "phoneNumber": "+15555550188",
                        "status": "active",
                        "source": "purchased",
                        "countryCode": "US",
                        "phoneNumberType": "local",
                        "monthlyCostCents": 150,
                        "voiceEnabled": True,
                        "voiceMode": "agent",
                    },
                    {
                        "id": "num_456",
                        "phoneNumber": "+15555550199",
                        "status": "active",
                        "source": "purchased",
                        "countryCode": "US",
                        "phoneNumberType": "toll_free",
                        "monthlyCostCents": 200,
                    },
                ]
            },
        )

        result = client.numbers.list()

        assert isinstance(result, OwnedNumbersResponse)
        assert result.numbers[0].voice_enabled is True
        assert result.numbers[0].voice_mode == "agent"
        assert result.numbers[1].voice_enabled is None
        assert result.numbers[1].voice_mode is None

        client.close()


class TestAsyncCalls:
    async def test_async_create(self, live_api_key, mock_call, httpx_mock: HTTPXMock):
        client = AsyncSendly(live_api_key)

        httpx_mock.add_response(
            url=f"{BASE}/calls", method="POST", status_code=201, json=mock_call
        )

        result = await client.calls.create(
            to="+15555550123",
            agent_id=AGENT_ID,
            from_="+15555550188",
            metadata={"crmId": "lead_8812"},
        )

        assert isinstance(result, Call)
        assert result.status == CallStatus.RINGING
        assert result.metadata == {"crmId": "lead_8812"}

        request = httpx_mock.get_request()
        assert AUTO_KEY.match(request.headers["Idempotency-Key"])
        assert json.loads(request.read().decode()) == {
            "to": "+15555550123",
            "agentId": AGENT_ID,
            "from": "+15555550188",
            "metadata": {"crmId": "lead_8812"},
        }

        await client.close()

    async def test_async_create_rejects_empty_to(self, live_api_key):
        client = AsyncSendly(live_api_key)

        with pytest.raises(ValidationError, match="to is required"):
            await client.calls.create(to="", agent_id=AGENT_ID)

        await client.close()

    async def test_async_list_get_hangup_recording(
        self, live_api_key, mock_call, mock_completed_call, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(live_api_key)

        httpx_mock.add_response(
            method="GET",
            url=f"{BASE}/calls?direction=outbound&limit=10",
            json={
                "data": [mock_call],
                "pagination": {"total": 1, "limit": 10, "offset": 0, "hasMore": False},
            },
        )
        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}",
            method="GET",
            json={**mock_completed_call, "transcript": []},
        )
        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}/hangup",
            method="POST",
            json={**mock_completed_call, "hangupClass": "normal"},
        )
        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL_ID}/recording",
            method="GET",
            json={
                "callId": CALL_ID,
                "status": "ready",
                "url": "https://sendly.live/recordings/signed?sig=abc",
                "expiresAt": "2026-09-12T14:10:00.000Z",
                "contentType": "audio/ogg",
            },
        )

        listing = await client.calls.list(direction=CallDirection.OUTBOUND, limit=10)
        fetched = await client.calls.get(CALL_ID)
        ended = await client.calls.hangup(CALL_ID)
        recording = await client.calls.recording(CALL_ID)

        assert listing.pagination.has_more is False
        assert listing.data[0].id == CALL_ID
        assert fetched.transcript == []
        assert ended.hangup_class == "normal"
        assert recording.url is not None

        requests = httpx_mock.get_requests()
        assert [(r.method, r.url.path) for r in requests] == [
            ("GET", "/api/v1/calls"),
            ("GET", f"/api/v1/calls/{CALL_ID}"),
            ("POST", f"/api/v1/calls/{CALL_ID}/hangup"),
            ("GET", f"/api/v1/calls/{CALL_ID}/recording"),
        ]
        assert dict(requests[0].url.params) == {"direction": "outbound", "limit": "10"}
        assert AUTO_KEY.match(requests[2].headers["Idempotency-Key"])
        assert json.loads(requests[2].read().decode()) == {}

        await client.close()

    async def test_async_insufficient_credits_402(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/calls",
            method="POST",
            status_code=402,
            json=mock_error_response(
                "insufficient_credits",
                "Calls cost 10 credits a minute. Current balance: 4.",
                creditsNeeded=10,
                currentBalance=4,
            ),
        )

        with pytest.raises(InsufficientCreditsError) as exc_info:
            await client.calls.create(to="+15555550123", agent_id=AGENT_ID)

        assert exc_info.value.credits_needed == 10
        assert exc_info.value.current_balance == 4

        await client.close()

    async def test_async_voice_not_enabled_404(
        self, live_api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(live_api_key, max_retries=0)

        httpx_mock.add_response(
            url=f"{BASE}/calls",
            method="GET",
            status_code=404,
            json=mock_error_response("voice_not_enabled", "Voice is not enabled for your account."),
        )

        with pytest.raises(SendlyError) as exc_info:
            await client.calls.list()

        assert exc_info.value.code == "voice_not_enabled"
        assert exc_info.value.status_code == 404

        await client.close()
