import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import SendlyError
from sendly.resources.webhooks import AsyncWebhooksResource, WebhooksResource
from sendly.types import DeliveryStatus, WebhookDelivery, WebhookRecoveryPreview

BASE = "https://sendly.live/api/v1"

DELIVERY = {
    "id": "del_1",
    "webhook_id": "whk_1",
    "event_id": "evt_1",
    "event_type": "message.sent",
    "status": "delivered",
    "success": True,
    "response_status_code": 200,
    "http_status": 200,
    "response_time": 85,
    "response_time_ms": 85,
    "response_body": "ok",
    "error_message": None,
    "error_code": None,
    "attempt_number": 1,
    "max_attempts": 6,
    "next_retry_at": None,
    "created_at": "2026-01-01T00:00:00.000Z",
    "delivered_at": "2026-01-01T00:00:01.000Z",
}


class TestGetDeliveries:
    def test_unwraps_the_deliveries_envelope(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/deliveries",
            method="GET",
            json={"deliveries": [DELIVERY], "pagination": {"limit": 50, "offset": 0}},
        )

        deliveries = client.webhooks.get_deliveries("whk_1")

        assert len(deliveries) == 1
        assert isinstance(deliveries[0], WebhookDelivery)
        assert deliveries[0].event_id == "evt_1"
        assert deliveries[0].attempt_number == 1
        assert deliveries[0].response_status_code == 200
        assert deliveries[0].response_time_ms == 85
        client.close()

    def test_sends_limit_offset_and_status(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/deliveries?limit=25&offset=50&status=failed",
            method="GET",
            json={"deliveries": [], "pagination": {"limit": 25, "offset": 50}},
        )

        assert client.webhooks.get_deliveries("whk_1", limit=25, offset=50, status="failed") == []
        client.close()

    def test_sends_the_value_of_a_delivery_status(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            method="GET", json={"deliveries": [], "pagination": {"limit": 50, "offset": 0}}
        )

        client.webhooks.get_deliveries("whk_1", status=DeliveryStatus.FAILED)

        assert httpx_mock.get_request().url.params["status"] == "failed"
        client.close()

    @pytest.mark.asyncio
    async def test_sends_the_value_of_a_delivery_status_async(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            method="GET", json={"deliveries": [], "pagination": {"limit": 50, "offset": 0}}
        )

        await client.webhooks.get_deliveries("whk_1", status=DeliveryStatus.PENDING)

        assert httpx_mock.get_request().url.params["status"] == "pending"
        await client.close()

    @pytest.mark.asyncio
    async def test_unwraps_the_deliveries_envelope_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/deliveries?offset=50",
            method="GET",
            json={"deliveries": [DELIVERY], "pagination": {"limit": 50, "offset": 50}},
        )

        deliveries = await client.webhooks.get_deliveries("whk_1", offset=50)

        assert deliveries[0].event_id == "evt_1"
        await client.close()


ROTATION_BODY = {
    "success": True,
    "id": "whk_1",
    "secret": "whsec_x",
    "new_secret": "whsec_x",
    "new_secret_version": 2,
    "grace_period_hours": 24,
    "rotated_at": "2026-01-01T00:00:00.000Z",
    "message": "Webhook secret rotated successfully. Save this secret - it won't be shown again.",
}


class TestRotateSecret:
    def test_reads_the_rotation(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/rotate-secret", method="POST", json=ROTATION_BODY
        )

        rotation = client.webhooks.rotate_secret("whk_1")

        assert rotation.new_secret == "whsec_x"
        assert rotation.secret == "whsec_x"
        assert rotation.new_secret_version == 2
        assert rotation.grace_period_hours == 24
        assert rotation.rotated_at == "2026-01-01T00:00:00.000Z"
        assert rotation.webhook is None
        assert rotation.old_secret_expires_at is None
        client.close()

    @pytest.mark.asyncio
    async def test_reads_the_rotation_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/rotate-secret", method="POST", json=ROTATION_BODY
        )

        rotation = await client.webhooks.rotate_secret("whk_1")

        assert rotation.new_secret == "whsec_x"
        await client.close()

    def test_unreadable_rotation_keeps_the_secret_on_the_error(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/rotate-secret",
            method="POST",
            json={**ROTATION_BODY, "new_secret_version": "two"},
        )

        with pytest.raises(SendlyError) as exc_info:
            client.webhooks.rotate_secret("whk_1")

        assert exc_info.value.code == "invalid_response"
        assert exc_info.value.response.model_extra["new_secret"] == "whsec_x"
        client.close()


TEST_SUCCESS_BODY = {
    "success": True,
    "message": "Test webhook delivered successfully in 120ms",
    "delivery": {
        "id": "del_9",
        "delivery_id": "del_9",
        "webhook_url": "https://example.com/hook",
        "event_type": "webhook.test",
        "status": "delivered",
        "response_time": 120,
        "status_code": 200,
        "response_body": "ok",
        "delivered_at": "2026-01-01T00:00:00.000Z",
    },
}


class TestTestWebhook:
    def test_reads_status_code_and_timing_from_the_delivery(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/test", method="POST", json=TEST_SUCCESS_BODY
        )

        result = client.webhooks.test("whk_1")

        assert result.success is True
        assert result.status_code == 200
        assert result.response_time_ms == 120
        assert result.error is None
        client.close()

    @pytest.mark.asyncio
    async def test_reads_status_code_and_timing_from_the_delivery_async(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/test", method="POST", json=TEST_SUCCESS_BODY
        )

        result = await client.webhooks.test("whk_1")

        assert result.status_code == 200
        assert result.response_time_ms == 120
        await client.close()

    def test_a_failed_test_still_raises(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/test",
            method="POST",
            status_code=400,
            json={"success": False, "message": "Test webhook failed: timeout"},
        )

        with pytest.raises(SendlyError) as exc_info:
            client.webhooks.test("whk_1")

        assert "timeout" in exc_info.value.message
        assert len(httpx_mock.get_requests()) == 1
        client.close()


class TestCreateValidation:
    def test_http_url_raises_a_plain_value_error(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValueError) as exc_info:
            client.webhooks.create(url="http://example.com/hook", events=["message.sent"])

        assert type(exc_info.value) is ValueError
        assert str(exc_info.value) == "Webhook URL must be HTTPS"
        client.close()

    def test_empty_events_raise_a_plain_value_error(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValueError) as exc_info:
            client.webhooks.create(url="https://example.com/hook", events=[])

        assert type(exc_info.value) is ValueError
        assert str(exc_info.value) == "At least one event type is required"
        client.close()

    def test_a_sendly_error_handler_listed_first_does_not_take_it(self, api_key):
        client = Sendly(api_key)

        try:
            client.webhooks.create(url="http://example.com/hook", events=["message.sent"])
            branch = "none"
        except SendlyError:
            branch = "api error"
        except ValueError:
            branch = "bad input"

        assert branch == "bad input"
        client.close()

    @pytest.mark.asyncio
    async def test_http_url_raises_a_plain_value_error_async(self, api_key):
        client = AsyncSendly(api_key)

        with pytest.raises(ValueError) as exc_info:
            await client.webhooks.create(url="http://example.com/hook", events=["message.sent"])

        assert type(exc_info.value) is ValueError
        assert str(exc_info.value) == "Webhook URL must be HTTPS"
        await client.close()

    def test_create_documents_the_value_error(self):
        doc = WebhooksResource.create.__doc__ or ""

        assert "ValueError: If the URL is not HTTPS or events are empty" in doc
        assert "ValidationError" not in doc


class TestBackfillDocs:
    @pytest.mark.parametrize("resource", [WebhooksResource, AsyncWebhooksResource])
    def test_backfill_says_to_dedupe_on_the_event_id(self, resource):
        doc = resource.backfill.__doc__ or ""
        if "WebhooksResource.backfill" in doc:
            doc = WebhooksResource.backfill.__doc__ or ""

        assert "fresh IDs" not in doc
        assert "event.id" in doc


class TestWebhookDeliveryModel:
    def test_event_id_is_a_required_str(self):
        field = WebhookDelivery.model_fields["event_id"]

        assert field.annotation is str
        assert field.is_required()


class TestUnreadableWebhookResponses:
    def test_malformed_delivery_raises_invalid_response(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        delivery = {k: v for k, v in DELIVERY.items() if k != "event_type"}
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/deliveries",
            method="GET",
            json={"deliveries": [delivery], "pagination": {"limit": 50, "offset": 0}},
        )

        with pytest.raises(SendlyError) as exc_info:
            client.webhooks.get_deliveries("whk_1")

        assert exc_info.value.code == "invalid_response"
        client.close()


class TestOlderResponseShapes:
    def test_test_result_without_a_delivery_reads_the_top_level_fields(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/test",
            method="POST",
            json={"success": True, "statusCode": 204, "responseTimeMs": 40},
        )

        result = client.webhooks.test("whk_1")

        assert result.success is True
        assert result.status_code == 204
        assert result.response_time_ms == 40
        client.close()

    def test_rotation_with_a_nested_webhook_reads_it(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        webhook = {
            "id": "whk_1",
            "url": "https://example.com/hook",
            "events": ["message.sent"],
            "is_active": True,
            "created_at": "2026-01-01T00:00:00.000Z",
            "updated_at": "2026-01-01T00:00:00.000Z",
        }
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/rotate-secret",
            method="POST",
            json={
                "webhook": webhook,
                "newSecret": "whsec_x",
                "oldSecretExpiresAt": "2026-01-02T00:00:00.000Z",
                "message": "Rotated",
            },
        )

        rotation = client.webhooks.rotate_secret("whk_1")

        assert rotation.new_secret == "whsec_x"
        assert rotation.webhook is not None
        assert rotation.webhook.is_active is True
        assert rotation.webhook.created_at == "2026-01-01T00:00:00.000Z"
        client.close()


RECOVERY_PREVIEW_BODY = {
    "circuitState": "open",
    "circuitOpenedAt": "2026-01-01T08:00:00.000Z",
    "failureCount": 12,
    "auditFailures": {
        "total": 3,
        "byStatus": {"failed": 2, "cancelled": 1},
        "byEventType": {"message.delivered": 2, "message.opt_out": 1},
    },
    "missingFromMessages": {"total": 4, "byEventType": {"message.sent": 4}},
    "histogram": [{"bucket": "2026-01-01T08:00:00.000Z", "missing": 4, "failed": 3}],
    "samples": [
        {
            "id": "msg_1",
            "toMasked": "+1555***4567",
            "eventType": "message.delivered",
            "occurredAt": "2026-01-01T08:30:00.000Z",
        }
    ],
    "windowSuggestion": {
        "since": "2026-01-01T08:00:00.000Z",
        "until": "2026-01-01T10:00:00.000Z",
    },
    "since": "2025-12-31T10:00:00.000Z",
    "until": "2026-01-01T10:00:00.000Z",
}


class TestRecoveryPreview:
    def test_sends_the_window_and_reads_the_preview(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(method="GET", json=RECOVERY_PREVIEW_BODY)

        preview = client.webhooks.recovery_preview(
            "whk_1",
            since="2025-12-31T10:00:00.000Z",
            until="2026-01-01T10:00:00.000Z",
            event_types=["message.delivered", "message.failed"],
        )

        request = httpx_mock.get_request()
        assert request.method == "GET"
        assert request.url.path == "/api/v1/webhooks/whk_1/recovery-preview"
        assert request.url.params["since"] == "2025-12-31T10:00:00.000Z"
        assert request.url.params["until"] == "2026-01-01T10:00:00.000Z"
        assert request.url.params["event_types"] == "message.delivered,message.failed"
        assert isinstance(preview, WebhookRecoveryPreview)
        assert preview.circuit_state == "open"
        assert preview.circuit_opened_at == "2026-01-01T08:00:00.000Z"
        assert preview.failure_count == 12
        assert preview.audit_failures.by_status == {"failed": 2, "cancelled": 1}
        assert preview.audit_failures.by_event_type["message.opt_out"] == 1
        assert preview.missing_from_messages.total == 4
        assert preview.histogram[0].missing == 4
        assert preview.samples[0].to_masked == "+1555***4567"
        assert preview.samples[0].occurred_at == "2026-01-01T08:30:00.000Z"
        assert preview.window_suggestion is not None
        assert preview.window_suggestion.since == "2026-01-01T08:00:00.000Z"
        client.close()

    def test_sends_no_query_without_options(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/recovery-preview",
            method="GET",
            json={**RECOVERY_PREVIEW_BODY, "circuitOpenedAt": None, "windowSuggestion": None},
        )

        preview = client.webhooks.recovery_preview("whk_1")

        assert preview.circuit_opened_at is None
        assert preview.window_suggestion is None
        client.close()

    @pytest.mark.asyncio
    async def test_reads_the_preview_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_1/recovery-preview?event_types=message.sent",
            method="GET",
            json=RECOVERY_PREVIEW_BODY,
        )

        preview = await client.webhooks.recovery_preview("whk_1", event_types=["message.sent"])

        assert preview.missing_from_messages.by_event_type == {"message.sent": 4}
        await client.close()

    def test_rejects_an_id_that_is_not_whk_prefixed(self, api_key):
        client = Sendly(api_key)
        with pytest.raises(ValueError):
            client.webhooks.recovery_preview("bad")
        client.close()


STORED_WEBHOOK = {
    "id": "whk_placeholder1",
    "url": "https://localhost/sendly-contract-capture",
    "events": ["message.received"],
    "description": "Contract capture",
    "mode": "test",
    "is_active": True,
    "failure_count": 0,
    "circuit_state": "closed",
    "api_version": "2024-01",
    "metadata": {"purpose": "contract-capture"},
    "created_at": "2026-01-01T00:00:00.000Z",
    "updated_at": "2026-01-01T00:00:00.000Z",
    "total_deliveries": 0,
    "successful_deliveries": 0,
    "success_rate": 0,
    "last_delivery_at": None,
}


class TestStoredMetadata:
    def test_get_reads_object_metadata(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_placeholder1", method="GET", json=STORED_WEBHOOK
        )

        webhook = client.webhooks.get("whk_placeholder1")

        assert webhook.metadata == {"purpose": "contract-capture"}
        client.close()

    @pytest.mark.parametrize("stored", [["a", 1], "note", 7, True, None])
    def test_list_reads_metadata_that_is_not_an_object_as_empty(
        self, api_key, httpx_mock: HTTPXMock, stored
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks",
            method="GET",
            json=[{**STORED_WEBHOOK, "metadata": stored}],
        )

        webhooks = client.webhooks.list()

        assert webhooks[0].id == "whk_placeholder1"
        assert webhooks[0].metadata == {}
        client.close()

    @pytest.mark.asyncio
    async def test_get_reads_array_metadata_as_empty_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks/whk_placeholder1",
            method="GET",
            json={**STORED_WEBHOOK, "metadata": [1, 2]},
        )

        webhook = await client.webhooks.get("whk_placeholder1")

        assert webhook.metadata == {}
        await client.close()
