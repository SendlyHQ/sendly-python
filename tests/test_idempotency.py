"""
Tests for automatic idempotency keys - generation, retry reuse, rotation
"""

import io
import re

import httpx
import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import ValidationError

BASE = "https://sendly.live/api/v1"
KEY_PATTERN = (
    r"^sendly-python-retry-"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def _key_of(request):
    """Extract the Idempotency-Key header from a captured request"""
    return request.headers.get("Idempotency-Key")


@pytest.fixture
def mock_whatsapp_message():
    return {
        "id": "msg_wa_123",
        "channel": "whatsapp",
        "message_format": "whatsapp",
        "to": "+15551234567",
        "from": "+15559876543",
        "text": "Hello!",
        "status": "queued",
        "segments": 1,
        "creditsUsed": 1,
        "whatsapp": {"kind": "text", "messageId": None},
        "createdAt": "2026-08-23T10:00:00Z",
    }


@pytest.fixture
def mock_rcs_message():
    return {
        "id": "msg_rcs_123",
        "channel": "rcs",
        "message_format": "rcs",
        "to": "+15551234567",
        "from": "Acme Coffee",
        "text": "Hello!",
        "status": "sent",
        "segments": 1,
        "creditsUsed": 2,
        "rcs": {
            "kind": "text",
            "agentId": "rcs_agent_123",
            "agentName": "Acme Coffee",
        },
        "createdAt": "2026-08-23T10:00:00Z",
        "metadata": {},
    }


@pytest.fixture
def mock_group_response():
    return {
        "id": "msg_group_123",
        "status": "sent",
        "to": ["+14155551234", "+14155555678"],
        "group_message_id": "grp_123",
    }


@pytest.fixture
def mock_media_file():
    return {
        "id": "med_123",
        "url": "https://cdn.sendly.live/media/med_123.jpg",
        "contentType": "image/jpeg",
        "sizeBytes": 16,
    }


class TestAutomaticKeyGeneration:
    """Test automatic idempotency key generation"""

    def test_post_gets_auto_generated_key(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test that POST requests get an auto-generated key with the right prefix"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        client.messages.send(to="+15551234567", text="Hello!")

        key = _key_of(httpx_mock.get_request())
        assert re.match(KEY_PATTERN, key)
        assert len(key) <= 255

        client.close()

    def test_get_has_no_key(self, api_key, mock_message_list, httpx_mock: HTTPXMock):
        """Test that GET requests do not get a key"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="GET",
            json=mock_message_list,
        )

        client.messages.list()

        assert _key_of(httpx_mock.get_request()) is None

        client.close()

    def test_delete_has_no_key(self, api_key, mock_cancelled_message, httpx_mock: HTTPXMock):
        """Test that DELETE requests do not get a key"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages/scheduled/msg_scheduled_123",
            method="DELETE",
            json=mock_cancelled_message,
        )

        client.messages.cancel_scheduled("msg_scheduled_123")

        assert _key_of(httpx_mock.get_request()) is None

        client.close()

    def test_batch_send_has_no_auto_key(self, api_key, mock_batch_response, httpx_mock: HTTPXMock):
        """Test that batch sends get no auto key (server dedupes by content)"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages/batch",
            method="POST",
            json=mock_batch_response,
        )

        client.messages.send_batch(messages=[{"to": "+15551234567", "text": "Hi!"}])

        assert _key_of(httpx_mock.get_request()) is None

        client.close()

    def test_media_upload_gets_auto_key(self, api_key, mock_media_file, httpx_mock: HTTPXMock):
        """Test that media uploads get an auto-generated key"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/media",
            method="POST",
            json=mock_media_file,
        )

        client.media.upload(io.BytesIO(b"fake-image-bytes"))

        assert re.match(KEY_PATTERN, _key_of(httpx_mock.get_request()))

        client.close()

    def test_distinct_keys_per_logical_request(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test that each logical request gets a distinct key"""
        client = Sendly(api_key)

        httpx_mock.add_response(url=f"{BASE}/messages", method="POST", json=mock_message)
        httpx_mock.add_response(url=f"{BASE}/messages", method="POST", json=mock_message)

        client.messages.send(to="+15551234567", text="First")
        client.messages.send(to="+15551234567", text="Second")

        requests = httpx_mock.get_requests()
        first = _key_of(requests[0])
        second = _key_of(requests[1])
        assert first is not None
        assert second is not None
        assert first != second

        client.close()


class TestRetryBehavior:
    """Test key reuse and rotation across retries"""

    def test_key_reused_after_timeout(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test that the key is reused when retrying after a timeout"""
        client = Sendly(api_key, max_retries=2)

        httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        message = client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        assert _key_of(requests[0]) == _key_of(requests[1])

        client.close()

    def test_key_reused_after_network_error(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test that the key is reused when retrying after a network error"""
        client = Sendly(api_key, max_retries=2)

        httpx_mock.add_exception(httpx.RequestError("Connection failed"))
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        message = client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        assert _key_of(requests[0]) == _key_of(requests[1])

        client.close()

    def test_key_rotated_after_5xx(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test that the auto key is rotated when retrying after a 5xx response"""
        client = Sendly(api_key, max_retries=2)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=500,
            json={"error": "internal_error", "message": "Server error"},
        )
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        message = client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        first = _key_of(requests[0])
        second = _key_of(requests[1])
        assert re.match(KEY_PATTERN, first)
        assert re.match(KEY_PATTERN, second)
        assert first != second

        client.close()

    def test_rotated_key_kept_across_subsequent_timeout(
        self, api_key, mock_message, httpx_mock: HTTPXMock
    ):
        """Test that the rotated key is kept across a later timeout (5xx then timeout)"""
        client = Sendly(api_key, max_retries=3)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=500,
            json={"error": "internal_error", "message": "Server error"},
        )
        httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        message = client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        requests = httpx_mock.get_requests()
        assert len(requests) == 3
        first = _key_of(requests[0])
        second = _key_of(requests[1])
        third = _key_of(requests[2])
        assert second != first
        assert third == second

        client.close()

    def test_key_kept_on_non_5xx_retry(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test that the key is kept when retrying a non-5xx HTTP error"""
        client = Sendly(api_key, max_retries=2)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=409,
            json={"error": "conflict", "message": "Resource busy"},
        )
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        message = client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        assert _key_of(requests[0]) == _key_of(requests[1])

        client.close()


class TestCallerSuppliedKeys:
    """Test caller-supplied idempotency keys"""

    def test_caller_key_sent_verbatim(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test that the caller's key is sent verbatim"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        client.messages.send(
            to="+15551234567",
            text="Hello!",
            idempotency_key="order-4821-shipped",
        )

        assert _key_of(httpx_mock.get_request()) == "order-4821-shipped"

        client.close()

    def test_caller_key_never_rotated_across_5xx(
        self, api_key, mock_message, httpx_mock: HTTPXMock
    ):
        """Test that the caller's key is never rotated, even across a 5xx retry"""
        client = Sendly(api_key, max_retries=2)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=500,
            json={"error": "internal_error", "message": "Server error"},
        )
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        client.messages.send(
            to="+15551234567",
            text="Hello!",
            idempotency_key="order-4821-shipped",
        )

        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        assert _key_of(requests[0]) == "order-4821-shipped"
        assert _key_of(requests[1]) == "order-4821-shipped"

        client.close()

    def test_caller_key_reused_across_timeout(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test that the caller's key is reused across a timeout retry"""
        client = Sendly(api_key, max_retries=2)

        httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        client.messages.send(
            to="+15551234567",
            text="Hello!",
            idempotency_key="signup-otp-user-99",
        )

        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        assert _key_of(requests[0]) == "signup-otp-user-99"
        assert _key_of(requests[1]) == "signup-otp-user-99"

        client.close()

    def test_caller_key_on_send_batch(self, api_key, mock_batch_response, httpx_mock: HTTPXMock):
        """Test that a caller key is sent on batch sends"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages/batch",
            method="POST",
            json=mock_batch_response,
        )

        client.messages.send_batch(
            messages=[{"to": "+15551234567", "text": "Hi!"}],
            idempotency_key="campaign-77-wave-1",
        )

        assert _key_of(httpx_mock.get_request()) == "campaign-77-wave-1"

        client.close()

    def test_caller_key_on_schedule(self, api_key, mock_scheduled_message, httpx_mock: HTTPXMock):
        """Test that a caller key is sent on scheduled sends"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages/schedule",
            method="POST",
            json=mock_scheduled_message,
        )

        client.messages.schedule(
            to="+15551234567",
            text="Reminder!",
            scheduled_at="2027-01-20T10:00:00Z",
            idempotency_key="reminder-visit-31",
        )

        assert _key_of(httpx_mock.get_request()) == "reminder-visit-31"

        client.close()

    def test_empty_key_falls_back_to_auto(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test that an empty-string key is ignored and a key is still auto-generated"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        client.messages.send(to="+15551234567", text="Hello!", idempotency_key="")

        assert re.match(KEY_PATTERN, _key_of(httpx_mock.get_request()))

        client.close()

    def test_whitespace_key_falls_back_to_auto(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test that a whitespace-only key is ignored and a key is still auto-generated"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        client.messages.send(to="+15551234567", text="Hello!", idempotency_key="   ")

        assert re.match(KEY_PATTERN, _key_of(httpx_mock.get_request()))

        client.close()

    def test_non_ascii_key_rejected_immediately(self, api_key, httpx_mock: HTTPXMock):
        """Test that a non-ASCII key raises immediately without a network call"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="printable ASCII"):
            client.messages.send(
                to="+15551234567",
                text="Hello!",
                idempotency_key="Заказ-42",
            )

        assert len(httpx_mock.get_requests()) == 0

        client.close()

    def test_overlong_key_rejected_immediately(self, api_key, httpx_mock: HTTPXMock):
        """Test that a key longer than 255 characters raises immediately"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="printable ASCII"):
            client.messages.send(
                to="+15551234567",
                text="Hello!",
                idempotency_key="k" * 256,
            )

        assert len(httpx_mock.get_requests()) == 0

        client.close()

    def test_caller_key_on_whatsapp_send(
        self, api_key, mock_whatsapp_message, httpx_mock: HTTPXMock
    ):
        """Test that a caller key is sent on the WhatsApp send branch"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_whatsapp_message,
        )

        client.messages.send(
            channel="whatsapp",
            to="+15551234567",
            from_="+15559876543",
            text="Hello!",
            idempotency_key="wa-hello-1",
        )

        assert _key_of(httpx_mock.get_request()) == "wa-hello-1"

        client.close()

    def test_caller_key_on_rcs_send(self, api_key, mock_rcs_message, httpx_mock: HTTPXMock):
        """Test that a caller key is sent on the RCS send branch"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_rcs_message,
        )

        client.messages.send(
            channel="rcs",
            to="+15551234567",
            text="Hello!",
            idempotency_key="rcs-hello-1",
        )

        assert _key_of(httpx_mock.get_request()) == "rcs-hello-1"

        client.close()

    def test_caller_key_on_send_group(self, api_key, mock_group_response, httpx_mock: HTTPXMock):
        """Test that a caller key is sent on group sends"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages/group",
            method="POST",
            json=mock_group_response,
        )

        client.messages.send_group(
            to=["+14155551234", "+14155555678"],
            text="Team sync at noon",
            idempotency_key="standup-ping-0823",
        )

        assert _key_of(httpx_mock.get_request()) == "standup-ping-0823"

        client.close()


class TestAsyncIdempotencyKeys:
    """Test idempotency keys on the async client"""

    @pytest.mark.asyncio
    async def test_post_gets_auto_generated_key(
        self, api_key, mock_message, httpx_mock: HTTPXMock
    ):
        """Test that async POST requests get an auto-generated key"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        await client.messages.send(to="+15551234567", text="Hello!")

        assert re.match(KEY_PATTERN, _key_of(httpx_mock.get_request()))

        await client.close()

    @pytest.mark.asyncio
    async def test_batch_send_has_no_auto_key(
        self, api_key, mock_batch_response, httpx_mock: HTTPXMock
    ):
        """Test that async batch sends get no auto key"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/messages/batch",
            method="POST",
            json=mock_batch_response,
        )

        await client.messages.send_batch(messages=[{"to": "+15551234567", "text": "Hi!"}])

        assert _key_of(httpx_mock.get_request()) is None

        await client.close()

    @pytest.mark.asyncio
    async def test_key_reused_after_network_error(
        self, api_key, mock_message, httpx_mock: HTTPXMock
    ):
        """Test that the async client reuses the key across a network-error retry"""
        client = AsyncSendly(api_key, max_retries=2)

        httpx_mock.add_exception(httpx.RequestError("Connection failed"))
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        message = await client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        assert _key_of(requests[0]) == _key_of(requests[1])

        await client.close()

    @pytest.mark.asyncio
    async def test_key_rotated_after_5xx(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test that the async client rotates the auto key after a 5xx response"""
        client = AsyncSendly(api_key, max_retries=2)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=500,
            json={"error": "internal_error", "message": "Server error"},
        )
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        message = await client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        first = _key_of(requests[0])
        second = _key_of(requests[1])
        assert re.match(KEY_PATTERN, first)
        assert re.match(KEY_PATTERN, second)
        assert first != second

        await client.close()

    @pytest.mark.asyncio
    async def test_caller_key_never_rotated_across_5xx(
        self, api_key, mock_message, httpx_mock: HTTPXMock
    ):
        """Test that the async client never rotates a caller key across a 5xx retry"""
        client = AsyncSendly(api_key, max_retries=2)

        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=500,
            json={"error": "internal_error", "message": "Server error"},
        )
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            json=mock_message,
        )

        await client.messages.send(
            to="+15551234567",
            text="Hello!",
            idempotency_key="order-4821-shipped",
        )

        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        assert _key_of(requests[0]) == "order-4821-shipped"
        assert _key_of(requests[1]) == "order-4821-shipped"

        await client.close()

    @pytest.mark.asyncio
    async def test_media_upload_gets_auto_key(
        self, api_key, mock_media_file, httpx_mock: HTTPXMock
    ):
        """Test that async media uploads get an auto-generated key"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url=f"{BASE}/media",
            method="POST",
            json=mock_media_file,
        )

        await client.media.upload(io.BytesIO(b"fake-image-bytes"))

        assert re.match(KEY_PATTERN, _key_of(httpx_mock.get_request()))

        await client.close()
