import json

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import SendlyError
from sendly.resources.campaigns import AsyncCampaignsResource, CampaignsResource
from sendly.types import Campaign, CampaignPreview, CampaignStatus

BASE = "https://sendly.live/api/v1"

ROW = {
    "id": "camp_1",
    "userId": "user_1",
    "organizationId": "org_1",
    "name": "Launch",
    "status": "completed",
    "messageText": "Hi {{name}}",
    "fromSender": None,
    "targetType": "contact_list",
    "targetListId": "lst_1",
    "manualRecipients": None,
    "excludeOptedOut": True,
    "sendNow": False,
    "scheduledAt": None,
    "timezone": "America/New_York",
    "batchId": "batch_1",
    "totalRecipients": 10,
    "estimatedCredits": 20,
    "sentCount": 10,
    "deliveredCount": 9,
    "failedCount": 1,
    "creditsUsed": 20,
    "creditsRefunded": 0,
    "createdAt": "2026-01-01T00:00:00.000Z",
    "updatedAt": "2026-01-02T00:00:00.000Z",
    "sentAt": "2026-01-01T10:00:00.000Z",
    "completedAt": "2026-01-01T10:05:00.000Z",
}

PUBLIC = {
    **ROW,
    "text": "Hi {{name}}",
    "contact_list_ids": ["lst_1"],
    "created_at": "2026-01-01T00:00:00.000Z",
    "updated_at": "2026-01-02T00:00:00.000Z",
}


class TestCampaignDecoding:
    def test_reads_counts_and_timestamps(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/campaigns/camp_1", method="GET", json=PUBLIC)

        campaign = client.campaigns.get("camp_1")

        assert campaign.text == "Hi {{name}}"
        assert campaign.contact_list_ids == ["lst_1"]
        assert campaign.recipient_count == 10
        assert campaign.sent_count == 10
        assert campaign.delivered_count == 9
        assert campaign.failed_count == 1
        assert campaign.estimated_credits == 20
        assert campaign.credits_used == 20
        assert campaign.started_at == "2026-01-01T10:00:00.000Z"
        assert campaign.completed_at == "2026-01-01T10:05:00.000Z"
        assert campaign.created_at == "2026-01-01T00:00:00.000Z"
        client.close()

    def test_reads_a_row_without_the_snake_case_twins(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/campaigns/camp_1", method="GET", json=ROW)

        campaign = client.campaigns.get("camp_1")

        assert campaign.text == "Hi {{name}}"
        assert campaign.contact_list_ids == ["lst_1"]
        assert campaign.created_at == "2026-01-01T00:00:00.000Z"
        assert campaign.updated_at == "2026-01-02T00:00:00.000Z"
        client.close()

    def test_list_reads_counts(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/campaigns",
            method="GET",
            json={"campaigns": [PUBLIC], "total": 1, "limit": 50, "offset": 0},
        )

        result = client.campaigns.list()

        assert result.campaigns[0].delivered_count == 9
        client.close()

    @pytest.mark.asyncio
    async def test_reads_counts_and_timestamps_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/campaigns/camp_1", method="GET", json=PUBLIC)

        campaign = await client.campaigns.get("camp_1")

        assert campaign.sent_count == 10
        assert campaign.started_at == "2026-01-01T10:00:00.000Z"
        await client.close()

    def test_completed_is_a_campaign_status(self):
        assert CampaignStatus("completed") == CampaignStatus.COMPLETED


SEND_RESULT = {
    "batchId": "batch_1",
    "status": "processing",
    "total": 2,
    "sent": 0,
    "failed": 0,
    "optedOutSkipped": 1,
    "invalidSkipped": 0,
    "creditsUsed": 4,
    "creditsRefunded": 0,
    "messages": [],
}


class TestCampaignSend:
    def test_returns_the_batch(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/campaigns/camp_1/send", method="POST", json=SEND_RESULT
        )

        result = client.campaigns.send("camp_1")

        assert result.batch_id == "batch_1"
        assert result.status == "processing"
        assert result.total == 2
        assert result.credits_used == 4
        assert result.opted_out_skipped == 1
        assert result.messages == []
        assert httpx_mock.get_request().content == b""
        client.close()

    def test_sends_from(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/campaigns/camp_1/send", method="POST", json=SEND_RESULT
        )

        client.campaigns.send("camp_1", from_="+15551234567")

        assert json.loads(httpx_mock.get_request().content) == {"from": "+15551234567"}
        client.close()

    @pytest.mark.asyncio
    async def test_returns_the_batch_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/campaigns/camp_1/send", method="POST", json=SEND_RESULT
        )

        result = await client.campaigns.send("camp_1", from_="+15551234567")

        assert result.batch_id == "batch_1"
        assert json.loads(httpx_mock.get_request().content) == {"from": "+15551234567"}
        await client.close()


PREVIEW = {
    "totalRecipients": 10,
    "estimatedCredits": 20,
    "optedOutCount": 1,
    "invalidCount": 0,
    "invalidNumberCount": 0,
    "landlineCount": 0,
    "sampleRecipients": [{"phone": "+15551234567", "name": "Ada"}],
    "blockedCount": 0,
    "sendableCount": 10,
    "byCountry": {"US": {"count": 10, "credits": 20, "allowed": True}},
    "warnings": [],
    "messagingProfile": {
        "canSendDomestic": True,
        "canSendInternational": False,
        "verificationType": "toll_free",
        "verificationStatus": "approved",
    },
    "recipientCount": 10,
    "currentBalance": 100,
    "hasEnoughCredits": True,
}


class TestCampaignPreview:
    def test_reads_the_preview(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/campaigns/camp_1/preview", method="GET", json=PREVIEW
        )

        preview = client.campaigns.preview("camp_1")

        assert preview.id == "camp_1"
        assert preview.recipient_count == 10
        assert preview.estimated_credits == 20
        assert preview.current_balance == 100
        assert preview.has_enough_credits is True
        assert preview.estimated_segments is None
        assert preview.sendable_count == 10
        assert preview.opted_out_count == 1
        assert preview.sample_recipients[0]["phone"] == "+15551234567"
        assert preview.by_country["US"]["count"] == 10
        client.close()

    @pytest.mark.asyncio
    async def test_reads_the_preview_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/campaigns/camp_1/preview", method="GET", json=PREVIEW
        )

        preview = await client.campaigns.preview("camp_1")

        assert preview.id == "camp_1"
        assert preview.has_enough_credits is True
        await client.close()


class TestFieldsTheApiDoesNotSend:
    @pytest.mark.parametrize(
        "model, field", [(Campaign, "template_id"), (CampaignPreview, "breakdown")]
    )
    def test_description_says_the_field_is_always_none(self, model, field):
        assert "Not returned by the API; always None" in model.model_fields[field].description


class TestOneContactListDocs:
    @pytest.mark.parametrize(
        "method",
        [
            CampaignsResource.create,
            CampaignsResource.update,
            AsyncCampaignsResource.create,
            AsyncCampaignsResource.update,
        ],
    )
    def test_contact_list_ids_is_documented_as_one_list(self, method):
        doc = method.__doc__ or ""

        assert "contact_list_ids: One contact list ID, in a one-element list" in doc
        assert "400 invalid_request" in doc


class TestUnreadableCampaignResponses:
    def test_malformed_campaign_raises_invalid_response(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/campaigns/camp_1", method="GET", json={**PUBLIC, "sentCount": "ten"}
        )

        with pytest.raises(SendlyError) as exc_info:
            client.campaigns.get("camp_1")

        assert exc_info.value.code == "invalid_response"
        client.close()

    def test_malformed_preview_raises_invalid_response(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/campaigns/camp_1/preview",
            method="GET",
            json={**PREVIEW, "estimatedCredits": "lots"},
        )

        with pytest.raises(SendlyError) as exc_info:
            client.campaigns.preview("camp_1")

        assert exc_info.value.code == "invalid_response"
        client.close()

    def test_send_result_without_a_batch_raises_invalid_response(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        body = {k: v for k, v in SEND_RESULT.items() if k != "batchId"}
        httpx_mock.add_response(url=f"{BASE}/campaigns/camp_1/send", method="POST", json=body)

        with pytest.raises(SendlyError) as exc_info:
            client.campaigns.send("camp_1")

        assert exc_info.value.code == "invalid_response"
        client.close()
