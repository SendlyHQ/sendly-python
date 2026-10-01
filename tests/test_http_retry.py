import io

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import RateLimitError, SendlyError

BASE = "https://sendly.live/api/v1"


@pytest.fixture
def no_sleep(monkeypatch):
    calls = []
    monkeypatch.setattr("sendly.utils.http.time.sleep", lambda s: calls.append(s))
    return calls


@pytest.fixture
def no_async_sleep(monkeypatch):
    calls = []

    async def fake_sleep(s):
        calls.append(s)

    monkeypatch.setattr("sendly.utils.http.asyncio.sleep", fake_sleep)
    return calls


class TestFinalAnswersAreNotRetried:
    def test_conflict_is_sent_once(self, api_key, no_sleep, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/labels",
            method="POST",
            status_code=409,
            json={"error": "conflict", "message": "A label with this name already exists"},
            is_reusable=True,
        )

        with pytest.raises(SendlyError) as exc_info:
            client.labels.create(name="VIP")

        assert exc_info.value.status_code == 409
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_redirect_is_sent_once(self, api_key, no_sleep, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/drafts/drf_1/approve",
            method="POST",
            status_code=307,
            headers={"Location": "/api/v1/messages"},
            is_reusable=True,
        )

        with pytest.raises(SendlyError):
            client.drafts.approve("drf_1")

        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_max_attempts_exceeded_is_sent_once(
        self, api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/verify/ver_1/check",
            method="POST",
            status_code=429,
            json={
                "error": "max_attempts_exceeded",
                "message": "Maximum verification attempts exceeded",
            },
            is_reusable=True,
        )

        with pytest.raises(SendlyError) as exc_info:
            client.verify.check("ver_1", "123456")

        assert exc_info.value.code == "max_attempts_exceeded"
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    @pytest.mark.asyncio
    async def test_async_conflict_is_sent_once(
        self, api_key, no_async_sleep, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/labels",
            method="POST",
            status_code=409,
            json={"error": "conflict", "message": "A label with this name already exists"},
            is_reusable=True,
        )

        with pytest.raises(SendlyError):
            await client.labels.create(name="VIP")

        assert len(httpx_mock.get_requests()) == 1
        await client.close()


class TestServerErrorsBackOff:
    def test_503_then_success_waits_before_retrying(
        self, api_key, mock_message, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=503,
            json={"error": "service_unavailable", "message": "Try again"},
        )
        httpx_mock.add_response(url=f"{BASE}/messages", method="POST", json=mock_message)

        message = client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        assert len(httpx_mock.get_requests()) == 2
        assert len(no_sleep) == 1
        assert no_sleep[0] >= 1
        client.close()

    @pytest.mark.asyncio
    async def test_async_503_then_success_waits_before_retrying(
        self, api_key, mock_message, no_async_sleep, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=503,
            json={"error": "service_unavailable", "message": "Try again"},
        )
        httpx_mock.add_response(url=f"{BASE}/messages", method="POST", json=mock_message)

        message = await client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        assert len(httpx_mock.get_requests()) == 2
        assert len(no_async_sleep) == 1
        assert no_async_sleep[0] >= 1
        await client.close()

    def test_408_is_retried(self, api_key, mock_message, no_sleep, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=408,
            json={"error": "request_timeout", "message": "Request timeout"},
        )
        httpx_mock.add_response(url=f"{BASE}/messages", method="POST", json=mock_message)

        message = client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        assert len(httpx_mock.get_requests()) == 2
        client.close()

    def test_425_is_retried_after_a_backoff(
        self, api_key, mock_message, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=425,
            json={"error": "too_early", "message": "Too early"},
        )
        httpx_mock.add_response(url=f"{BASE}/messages", method="POST", json=mock_message)

        message = client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        assert len(httpx_mock.get_requests()) == 2
        assert len(no_sleep) == 1
        client.close()

    @pytest.mark.asyncio
    async def test_async_408_is_retried_after_a_backoff(
        self, api_key, mock_message, no_async_sleep, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=408,
            json={"error": "request_timeout", "message": "Request timeout"},
        )
        httpx_mock.add_response(url=f"{BASE}/messages", method="POST", json=mock_message)

        message = await client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        assert len(httpx_mock.get_requests()) == 2
        assert len(no_async_sleep) == 1
        await client.close()

    def test_rate_limit_still_waits_retry_after(
        self, api_key, mock_message, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=429,
            json={"error": "rate_limit_exceeded", "message": "Slow down", "retryAfter": 7},
        )
        httpx_mock.add_response(url=f"{BASE}/messages", method="POST", json=mock_message)

        message = client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        assert no_sleep == [7]
        client.close()

    def test_rate_limit_on_the_last_attempt_raises(
        self, api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=0)
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=429,
            json={"error": "rate_limit_exceeded", "message": "Slow down", "retryAfter": 7},
        )

        with pytest.raises(RateLimitError):
            client.messages.send(to="+15551234567", text="Hello!")

        client.close()


BUSY = {
    "error": "too_many_concurrent_verifications",
    "message": (
        "Too many API key checks are already running for this account "
        "from this address. Try again in 1 second."
    ),
    "retryAfter": 1,
}
LOCKED = {
    "error": "too_many_failed_key_attempts",
    "message": "Too many failed API key attempts. Try again in 240 seconds.",
    "retryAfter": 240,
}


class TestApiKeyCheck429s:
    def test_busy_key_check_is_retried_after_retry_after(
        self, api_key, mock_message, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages", method="POST", status_code=429, json=BUSY,
            headers={"Retry-After": "1"},
        )
        httpx_mock.add_response(url=f"{BASE}/messages", method="POST", json=mock_message)

        message = client.messages.send(to="+15551234567", text="Hello!")

        requests = httpx_mock.get_requests()
        assert message.id == "msg_test_123"
        assert no_sleep == [1]
        assert len(requests) == 2
        assert requests[0].headers["Idempotency-Key"] == requests[1].headers["Idempotency-Key"]
        client.close()

    def test_busy_key_check_raises_once_retries_run_out(
        self, api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=2)
        httpx_mock.add_response(
            url=f"{BASE}/messages", method="POST", status_code=429, json=BUSY,
            headers={"Retry-After": "1"}, is_reusable=True,
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.messages.send(to="+15551234567", text="Hello!")

        assert exc_info.value.code == "too_many_concurrent_verifications"
        assert exc_info.value.retry_after == 1
        assert no_sleep == [1, 1]
        assert len(httpx_mock.get_requests()) == 3
        client.close()

    def test_failed_key_lockout_is_raised_at_once(
        self, api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages", method="POST", status_code=429, json=LOCKED,
            headers={"Retry-After": "240"}, is_reusable=True,
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.messages.send(to="+15551234567", text="Hello!")

        assert exc_info.value.code == "too_many_failed_key_attempts"
        assert exc_info.value.retry_after == 240
        assert exc_info.value.message == LOCKED["message"]
        assert no_sleep == []
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    @pytest.mark.asyncio
    async def test_async_busy_key_check_is_retried_after_retry_after(
        self, api_key, mock_message, no_async_sleep, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages", method="POST", status_code=429, json=BUSY,
            headers={"Retry-After": "1"},
        )
        httpx_mock.add_response(url=f"{BASE}/messages", method="POST", json=mock_message)

        message = await client.messages.send(to="+15551234567", text="Hello!")

        requests = httpx_mock.get_requests()
        assert message.id == "msg_test_123"
        assert no_async_sleep == [1]
        assert len(requests) == 2
        assert requests[0].headers["Idempotency-Key"] == requests[1].headers["Idempotency-Key"]
        await client.close()

    @pytest.mark.asyncio
    async def test_async_failed_key_lockout_is_raised_at_once(
        self, api_key, no_async_sleep, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages", method="POST", status_code=429, json=LOCKED,
            headers={"Retry-After": "240"}, is_reusable=True,
        )

        with pytest.raises(RateLimitError) as exc_info:
            await client.messages.send(to="+15551234567", text="Hello!")

        assert exc_info.value.code == "too_many_failed_key_attempts"
        assert no_async_sleep == []
        assert len(httpx_mock.get_requests()) == 1
        await client.close()


MEDIA = {
    "id": "med_123",
    "url": "https://cdn.sendly.live/media/med_123.jpg",
    "contentType": "image/jpeg",
    "sizeBytes": 16,
}
DOC_URL = f"{BASE}/enterprise/verification-document/upload"


class TestApiKeyCheck429sOnUploads:
    def test_media_upload_retries_a_busy_key_check(
        self, api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/media", method="POST", status_code=429, json=BUSY,
            headers={"Retry-After": "1"},
        )
        httpx_mock.add_response(url=f"{BASE}/media", method="POST", json=MEDIA)

        media = client.media.upload(io.BytesIO(b"fake-image-bytes"))

        requests = httpx_mock.get_requests()
        assert media.id == "med_123"
        assert no_sleep == [1]
        assert len(requests) == 2
        assert requests[0].headers["Idempotency-Key"] == requests[1].headers["Idempotency-Key"]
        assert requests[0].content == requests[1].content
        client.close()

    def test_media_upload_raises_the_lockout_at_once(
        self, api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/media", method="POST", status_code=429, json=LOCKED,
            headers={"Retry-After": "240"}, is_reusable=True,
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.media.upload(io.BytesIO(b"fake-image-bytes"))

        assert exc_info.value.code == "too_many_failed_key_attempts"
        assert no_sleep == []
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    @pytest.mark.asyncio
    async def test_async_media_upload_retries_a_busy_key_check(
        self, api_key, no_async_sleep, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/media", method="POST", status_code=429, json=BUSY,
            headers={"Retry-After": "1"},
        )
        httpx_mock.add_response(url=f"{BASE}/media", method="POST", json=MEDIA)

        media = await client.media.upload(io.BytesIO(b"fake-image-bytes"))

        requests = httpx_mock.get_requests()
        assert media.id == "med_123"
        assert no_async_sleep == [1]
        assert len(requests) == 2
        assert requests[0].headers["Idempotency-Key"] == requests[1].headers["Idempotency-Key"]
        await client.close()

    def test_document_upload_retries_a_busy_key_check(
        self, api_key, no_sleep, tmp_path, httpx_mock: HTTPXMock
    ):
        doc = tmp_path / "ein-letter.pdf"
        doc.write_bytes(b"%PDF-1.4 fake")
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=DOC_URL, method="POST", status_code=429, json=BUSY,
            headers={"Retry-After": "1"},
        )
        httpx_mock.add_response(url=DOC_URL, method="POST", json={"url": "https://cdn.sendly.live/d/1"})

        result = client.enterprise.upload_verification_document(str(doc))

        requests = httpx_mock.get_requests()
        assert result == {"url": "https://cdn.sendly.live/d/1"}
        assert no_sleep == [1]
        assert len(requests) == 2
        assert requests[0].headers["Idempotency-Key"] == requests[1].headers["Idempotency-Key"]
        assert b"%PDF-1.4 fake" in requests[1].content
        client.close()

    def test_document_upload_raises_the_lockout_at_once(
        self, api_key, no_sleep, tmp_path, httpx_mock: HTTPXMock
    ):
        doc = tmp_path / "ein-letter.pdf"
        doc.write_bytes(b"%PDF-1.4 fake")
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=DOC_URL, method="POST", status_code=429, json=LOCKED,
            headers={"Retry-After": "240"}, is_reusable=True,
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.enterprise.upload_verification_document(str(doc))

        assert exc_info.value.code == "too_many_failed_key_attempts"
        assert no_sleep == []
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    @pytest.mark.asyncio
    async def test_async_document_upload_retries_a_busy_key_check(
        self, api_key, no_async_sleep, tmp_path, httpx_mock: HTTPXMock
    ):
        doc = tmp_path / "ein-letter.pdf"
        doc.write_bytes(b"%PDF-1.4 fake")
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=DOC_URL, method="POST", status_code=429, json=BUSY,
            headers={"Retry-After": "1"},
        )
        httpx_mock.add_response(url=DOC_URL, method="POST", json={"url": "https://cdn.sendly.live/d/1"})

        result = await client.enterprise.upload_verification_document(str(doc))

        requests = httpx_mock.get_requests()
        assert result == {"url": "https://cdn.sendly.live/d/1"}
        assert no_async_sleep == [1]
        assert len(requests) == 2
        assert requests[0].headers["Idempotency-Key"] == requests[1].headers["Idempotency-Key"]
        await client.close()


OTP_LIMITED = {
    "error": "rate_limit_exceeded",
    "message": "Too many OTPs sent to this phone number. Max 5 per 10 minutes.",
    "retryAfter": 600,
}


class TestLongRateLimitWaits:
    def test_a_rate_limit_longer_than_a_minute_is_raised_at_once(
        self, api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/verify", method="POST", status_code=429, json=OTP_LIMITED,
            is_reusable=True,
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.verify.send(to="+14155552671")

        assert exc_info.value.retry_after == 600
        assert no_sleep == []
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_a_rate_limit_of_a_minute_is_still_waited_out(
        self, api_key, mock_message, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages", method="POST", status_code=429,
            json={"error": "rate_limit_exceeded", "message": "Slow down", "retryAfter": 60},
        )
        httpx_mock.add_response(url=f"{BASE}/messages", method="POST", json=mock_message)

        message = client.messages.send(to="+15551234567", text="Hello!")

        assert message.id == "msg_test_123"
        assert no_sleep == [60]
        client.close()

    @pytest.mark.asyncio
    async def test_async_a_rate_limit_longer_than_a_minute_is_raised_at_once(
        self, api_key, no_async_sleep, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/verify", method="POST", status_code=429, json=OTP_LIMITED,
            is_reusable=True,
        )

        with pytest.raises(RateLimitError) as exc_info:
            await client.verify.send(to="+14155552671")

        assert exc_info.value.retry_after == 600
        assert no_async_sleep == []
        assert len(httpx_mock.get_requests()) == 1
        await client.close()


PROVISION_URL = f"{BASE}/enterprise/workspaces/provision"
PROVISION_PER_MINUTE = {
    "error": "provision_rate_limit",
    "message": "Max 120 provisions per minute.",
    "retryAfter": 42,
}
PROVISION_PER_HOUR = {
    "error": "provision_rate_limit",
    "message": "Max 1000 provisions per hour.",
    "retryAfter": 3100,
}
PROVISIONED = {"workspace": {"id": "ws_1", "name": "Acme"}}


class TestProvisioningLimit:
    def test_the_per_minute_limit_is_waited_out_and_retried_with_the_same_key(
        self, api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=PROVISION_URL, method="POST", status_code=429, json=PROVISION_PER_MINUTE
        )
        httpx_mock.add_response(url=PROVISION_URL, method="POST", status_code=201, json=PROVISIONED)

        result = client.enterprise.provision({"name": "Acme"})

        assert result["workspace"]["id"] == "ws_1"
        assert no_sleep == [42]
        first, second = httpx_mock.get_requests()
        assert first.headers["Idempotency-Key"] == second.headers["Idempotency-Key"]
        client.close()

    def test_the_hourly_limit_is_raised_at_once(
        self, api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=PROVISION_URL, method="POST", status_code=429, json=PROVISION_PER_HOUR,
            is_reusable=True,
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.enterprise.provision({"name": "Acme"})

        assert exc_info.value.code == "provision_rate_limit"
        assert exc_info.value.retry_after == 3100
        assert no_sleep == []
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    @pytest.mark.asyncio
    async def test_async_the_per_minute_limit_is_waited_out_and_retried(
        self, api_key, no_async_sleep, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=PROVISION_URL, method="POST", status_code=429, json=PROVISION_PER_MINUTE
        )
        httpx_mock.add_response(url=PROVISION_URL, method="POST", status_code=201, json=PROVISIONED)

        result = await client.enterprise.provision({"name": "Acme"})

        assert result["workspace"]["id"] == "ws_1"
        assert no_async_sleep == [42]
        await client.close()


class TestUploadsNeverWaitOverAMinute:
    def test_media_upload_raises_a_busy_429_over_a_minute_at_once(
        self, api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/media", method="POST", status_code=429,
            json={**BUSY, "retryAfter": 3600}, is_reusable=True,
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.media.upload(io.BytesIO(b"fake-image-bytes"))

        assert exc_info.value.code == "too_many_concurrent_verifications"
        assert no_sleep == []
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_document_upload_raises_a_busy_429_over_a_minute_at_once(
        self, api_key, no_sleep, tmp_path, httpx_mock: HTTPXMock
    ):
        doc = tmp_path / "ein-letter.pdf"
        doc.write_bytes(b"%PDF-1.4 fake")
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=DOC_URL, method="POST", status_code=429,
            json={**BUSY, "retryAfter": 3600}, is_reusable=True,
        )

        with pytest.raises(RateLimitError):
            client.enterprise.upload_verification_document(str(doc))

        assert no_sleep == []
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    @pytest.mark.asyncio
    async def test_async_document_upload_raises_a_busy_429_over_a_minute_at_once(
        self, api_key, no_async_sleep, tmp_path, httpx_mock: HTTPXMock
    ):
        doc = tmp_path / "ein-letter.pdf"
        doc.write_bytes(b"%PDF-1.4 fake")
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=DOC_URL, method="POST", status_code=429,
            json={**BUSY, "retryAfter": 3600}, is_reusable=True,
        )

        with pytest.raises(RateLimitError):
            await client.enterprise.upload_verification_document(str(doc))

        assert no_async_sleep == []
        assert len(httpx_mock.get_requests()) == 1
        await client.close()
