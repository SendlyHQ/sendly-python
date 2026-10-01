import json

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import SendlyError
from sendly.types import BatchStatus, MessageStatus, ScheduledMessageStatus, SenderType

BASE = "https://sendly.live/api/v1"

LIVE_SEND = {
    "id": "0b3c7c2e-1c1f-4a8e-9a55-0d6f1b2c3d4e",
    "to": "+15551234567",
    "from": "+15557654321",
    "text": "Hello!",
    "status": "queued",
    "direction": "outbound",
    "error": None,
    "segments": 1,
    "creditsUsed": 2,
    "senderType": "explicit",
    "createdAt": "2026-01-01T00:00:00.000Z",
    "metadata": {},
}


class TestSenderType:
    def test_explicit_sender_parses(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages", method="POST", status_code=201, json=LIVE_SEND
        )

        message = client.messages.send(to="+15551234567", text="Hello!", from_="+15557654321")

        assert message.sender_type == SenderType.EXPLICIT
        assert message.reported_direction == "outbound"
        client.close()

    def test_unknown_sender_type_does_not_fail_a_sent_message(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=201,
            json={**LIVE_SEND, "senderType": "shortcode"},
        )

        message = client.messages.send(to="+15551234567", text="Hello!")

        assert isinstance(message.sender_type, SenderType)
        assert message.sender_type.value == "shortcode"
        assert message.sender_type.name == "UNKNOWN"
        assert message.model_dump(mode="json")["sender_type"] == "shortcode"
        client.close()

    @pytest.mark.asyncio
    async def test_explicit_sender_parses_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages", method="POST", status_code=201, json=LIVE_SEND
        )

        message = await client.messages.send(to="+15551234567", text="Hello!")

        assert message.sender_type == SenderType.EXPLICIT
        await client.close()


def _scheduled(status):
    return {
        "id": f"schd_{status}",
        "to": "+15551234567",
        "text": "Reminder",
        "scheduledAt": "2026-01-02T00:00:00.000Z",
        "timezone": "UTC",
        "status": status,
        "creditsReserved": 2,
        "segments": 1,
        "senderType": "number_pool",
        "createdAt": "2026-01-01T00:00:00.000Z",
        "metadata": {},
    }


class TestScheduledStatuses:
    def test_delivery_receipt_statuses_parse(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages/scheduled",
            method="GET",
            json={
                "data": [_scheduled("delivered"), _scheduled("bounced"), _scheduled("weird")],
                "count": 3,
            },
        )

        result = client.messages.list_scheduled()

        assert [m.status for m in result.data] == [
            ScheduledMessageStatus.DELIVERED,
            ScheduledMessageStatus.BOUNCED,
            "weird",
        ]
        assert isinstance(result.data[2].status, ScheduledMessageStatus)
        assert result.data[2].status.value == "weird"
        assert result.data[2].status.name == "UNKNOWN"
        client.close()

    @pytest.mark.asyncio
    async def test_delivered_scheduled_message_parses_async(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages/scheduled/schd_delivered",
            method="GET",
            json=_scheduled("delivered"),
        )

        message = await client.messages.get_scheduled("schd_delivered")

        assert message.status == ScheduledMessageStatus.DELIVERED
        await client.close()


class TestGroupRecipients:
    def test_live_send_reports_each_recipient(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages/group",
            method="POST",
            status_code=201,
            json={
                "id": "msg_grp_1",
                "status": "sent",
                "to": [
                    {"phoneNumber": "+14155551234", "status": "queued"},
                    {"phoneNumber": "+14155555678", "status": "queued"},
                ],
                "group_message_id": "grp_1",
            },
        )

        group = client.messages.send_group(to=["+14155551234", "+14155555678"], text="Dinner?")

        assert group.to == ["+14155551234", "+14155555678"]
        assert group.recipients[0].phone_number == "+14155551234"
        assert group.recipients[0].status == "queued"
        assert group.group_message_id == "grp_1"
        client.close()

    def test_simulated_send_still_parses(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages/group",
            method="POST",
            status_code=201,
            json={
                "id": "msg_grp_2",
                "status": "delivered",
                "to": ["+14155551234", "+14155555678"],
                "simulated": True,
                "message": "Group message simulated (test key or verification pending).",
            },
        )

        group = client.messages.send_group(to=["+14155551234", "+14155555678"], text="Dinner?")

        assert group.to == ["+14155551234", "+14155555678"]
        assert group.recipients is None
        assert group.simulated is True
        client.close()

    @pytest.mark.asyncio
    async def test_live_send_reports_each_recipient_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages/group",
            method="POST",
            status_code=201,
            json={
                "id": "msg_grp_1",
                "status": "sent",
                "to": [
                    {"phoneNumber": "+14155551234", "status": "queued"},
                    {"phoneNumber": "+14155555678", "status": "sent"},
                ],
                "group_message_id": "grp_1",
            },
        )

        group = await client.messages.send_group(
            to=["+14155551234", "+14155555678"], text="Dinner?"
        )

        assert group.recipients[1].status == "sent"
        await client.close()


BATCH_ACCEPTED = {
    "batchId": "batch_1",
    "status": "processing",
    "total": 1001,
    "sent": 0,
    "failed": 0,
    "optedOutSkipped": 0,
    "invalidSkipped": 0,
    "creditsUsed": 0,
    "creditsRefunded": 0,
    "messages": [],
}


def _messages(count):
    return [{"to": "+15551234567", "text": f"Hello {i}"} for i in range(count)]


class TestBatchLimit:
    def test_send_batch_accepts_more_than_1000(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages/batch", method="POST", status_code=202, json=BATCH_ACCEPTED
        )

        batch = client.messages.send_batch(messages=_messages(1001))

        assert batch.batch_id == "batch_1"
        assert len(json.loads(httpx_mock.get_request().content)["messages"]) == 1001
        client.close()

    def test_send_batch_refuses_more_than_10000_before_sending(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(SendlyError):
            client.messages.send_batch(messages=_messages(10001))

        client.close()

    def test_preview_batch_accepts_more_than_1000(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages/batch/preview",
            method="POST",
            json={"total": 1001, "sendable": 1001, "blocked": 0, "creditsNeeded": 2002},
        )

        preview = client.messages.preview_batch(messages=_messages(1001))

        assert preview["total"] == 1001
        client.close()

    @pytest.mark.asyncio
    async def test_send_batch_accepts_more_than_1000_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages/batch", method="POST", status_code=202, json=BATCH_ACCEPTED
        )

        batch = await client.messages.send_batch(messages=_messages(1001))

        assert batch.batch_id == "batch_1"
        await client.close()

    @pytest.mark.asyncio
    async def test_preview_batch_accepts_more_than_1000_async(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages/batch/preview",
            method="POST",
            json={"total": 1001, "sendable": 1001, "blocked": 0, "creditsNeeded": 2002},
        )

        preview = await client.messages.preview_batch(messages=_messages(1001))

        assert preview["total"] == 1001
        await client.close()

    def test_request_model_allows_10000(self):
        from sendly.types import BatchMessageRequest

        request = BatchMessageRequest(messages=_messages(10000))

        assert len(request.messages) == 10000


def _page(ids, total, offset, has_more):
    return {
        "data": [
            {
                "id": i,
                "to": "+15551234567",
                "from": "+15557654321",
                "text": "Hi",
                "status": "failed",
                "direction": "inbound",
                "segments": 1,
                "creditsUsed": 0,
                "isSandbox": False,
                "createdAt": "2026-01-01T00:00:00.000Z",
            }
            for i in ids
        ],
        "pagination": {
            "total": total,
            "limit": 2,
            "offset": offset,
            "page": offset // 2 + 1,
            "totalPages": 2,
            "hasMore": has_more,
        },
        "count": len(ids),
    }


class TestListFilters:
    def test_list_sends_every_filter(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(method="GET", json=_page(["m1"], 57, 20, True))

        client.messages.list(
            limit=10,
            offset=20,
            status="failed",
            direction="inbound",
            to="+15551234567",
        )

        params = dict(httpx_mock.get_request().url.params)
        assert params == {
            "limit": "10",
            "offset": "20",
            "status": "failed",
            "direction": "inbound",
            "to": "+15551234567",
        }
        client.close()

    def test_list_sends_search_and_sandbox(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(method="GET", json=_page(["m1"], 1, 0, False))

        client.messages.list(q="invoice", sandbox=True, page=2)

        params = dict(httpx_mock.get_request().url.params)
        assert params == {"q": "invoice", "sandbox": "true", "page": "2"}
        client.close()

    def test_list_reports_the_total(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(method="GET", json=_page(["m1", "m2"], 57, 0, True))

        result = client.messages.list(limit=2)

        assert result.count == 2
        assert result.pagination.total == 57
        assert result.pagination.has_more is True
        client.close()

    def test_list_all_forwards_filters_and_pages_with_offset(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(method="GET", json=_page(["m1", "m2"], 3, 0, True))
        httpx_mock.add_response(method="GET", json=_page(["m3"], 3, 2, False))

        ids = [m.id for m in client.messages.list_all(batch_size=2, status="failed")]

        assert ids == ["m1", "m2", "m3"]
        first, second = httpx_mock.get_requests()
        assert dict(first.url.params) == {"limit": "2", "offset": "0", "status": "failed"}
        assert dict(second.url.params) == {"limit": "2", "offset": "2", "status": "failed"}
        client.close()

    def test_list_all_stops_when_the_api_says_there_are_no_more(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(method="GET", json=_page(["m1", "m2"], 2, 0, False))

        ids = [m.id for m in client.messages.list_all(batch_size=2)]

        assert ids == ["m1", "m2"]
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    @pytest.mark.asyncio
    async def test_list_sends_every_filter_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(method="GET", json=_page(["m1"], 57, 20, True))

        await client.messages.list(limit=10, offset=20, status="failed", direction="outbound")

        params = dict(httpx_mock.get_request().url.params)
        assert params == {
            "limit": "10",
            "offset": "20",
            "status": "failed",
            "direction": "outbound",
        }
        await client.close()

    @pytest.mark.asyncio
    async def test_list_all_forwards_filters_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(method="GET", json=_page(["m1", "m2"], 3, 0, True))
        httpx_mock.add_response(method="GET", json=_page(["m3"], 3, 2, False))

        ids = [m.id async for m in client.messages.list_all(batch_size=2, direction="inbound")]

        assert ids == ["m1", "m2", "m3"]
        first, second = httpx_mock.get_requests()
        assert dict(second.url.params) == {"limit": "2", "offset": "2", "direction": "inbound"}
        await client.close()


class TestStatusFiltersTakeEnumMembers:
    def test_list_sends_the_value_of_a_message_status(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(method="GET", json=_page(["m1"], 1, 0, False))

        client.messages.list(status=MessageStatus.FAILED)

        assert httpx_mock.get_request().url.params["status"] == "failed"
        client.close()

    def test_list_all_sends_the_value_of_a_message_status(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(method="GET", json=_page(["m1"], 1, 0, False))

        list(client.messages.list_all(status=MessageStatus.FAILED))

        assert httpx_mock.get_request().url.params["status"] == "failed"
        client.close()

    def test_list_scheduled_sends_the_value_of_a_status(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(method="GET", json={"data": [], "count": 0})

        client.messages.list_scheduled(status=ScheduledMessageStatus.SCHEDULED)

        assert httpx_mock.get_request().url.params["status"] == "scheduled"
        client.close()

    def test_list_batches_sends_the_value_of_a_status(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(method="GET", json={"data": [], "count": 0})

        client.messages.list_batches(status=BatchStatus.PARTIAL_FAILURE)

        assert httpx_mock.get_request().url.params["status"] == "partial_failure"
        client.close()

    def test_a_status_string_is_sent_as_is(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(method="GET", json=_page(["m1"], 1, 0, False))

        client.messages.list(status="delivered")

        assert httpx_mock.get_request().url.params["status"] == "delivered"
        client.close()

    @pytest.mark.asyncio
    async def test_async_list_and_list_all_send_the_value(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(method="GET", json=_page(["m1"], 1, 0, False), is_reusable=True)

        await client.messages.list(status=MessageStatus.DELIVERED)
        [m async for m in client.messages.list_all(status=MessageStatus.DELIVERED)]

        assert [r.url.params["status"] for r in httpx_mock.get_requests()] == [
            "delivered",
            "delivered",
        ]
        await client.close()

    @pytest.mark.asyncio
    async def test_async_list_scheduled_and_batches_send_the_value(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(method="GET", json={"data": [], "count": 0}, is_reusable=True)

        await client.messages.list_scheduled(status=ScheduledMessageStatus.CANCELLED)
        await client.messages.list_batches(status=BatchStatus.FAILED)

        assert [r.url.params["status"] for r in httpx_mock.get_requests()] == [
            "cancelled",
            "failed",
        ]
        await client.close()


class TestWhatsAppContentCheck:
    def test_empty_whatsapp_send_raises_the_documented_validation_error(
        self, api_key, httpx_mock: HTTPXMock
    ):
        from sendly.errors import ValidationError

        client = Sendly(api_key)

        with pytest.raises(ValidationError) as exc_info:
            client.messages.send(channel="whatsapp", to="+15551234567", from_="+15559876543")

        assert exc_info.value.code == "invalid_request"
        assert httpx_mock.get_requests() == []
        client.close()

    @pytest.mark.asyncio
    async def test_empty_whatsapp_send_raises_the_documented_validation_error_async(
        self, api_key, httpx_mock: HTTPXMock
    ):
        from sendly.errors import ValidationError

        client = AsyncSendly(api_key)

        with pytest.raises(ValidationError):
            await client.messages.send(
                channel="whatsapp", to="+15551234567", from_="+15559876543"
            )

        assert httpx_mock.get_requests() == []
        await client.close()


class TestPreviewBatchDocs:
    @pytest.mark.parametrize("key", ["canSend", "willSend"])
    def test_example_reads_only_keys_the_api_returns(self, key):
        from sendly.resources.messages import MessagesResource

        assert key not in (MessagesResource.preview_batch.__doc__ or "")


class TestBatchIdFromStatusAndList:
    def test_get_batch_reads_id(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages/batch/batch_1",
            method="GET",
            json={
                "id": "batch_1",
                "status": "completed",
                "total": 2,
                "queued": 0,
                "sent": 2,
                "delivered": 2,
                "failed": 0,
                "creditsReserved": 4,
                "creditsUsed": 4,
                "creditsRefunded": 0,
                "createdAt": "2026-01-01T00:00:00.000Z",
                "completedAt": "2026-01-01T00:01:00.000Z",
                "messages": [],
            },
        )

        batch = client.messages.get_batch("batch_1")

        assert batch.batch_id == "batch_1"
        client.close()
