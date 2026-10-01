import json

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, EnterpriseWebhook, Sendly
from sendly.errors import NotFoundError

BASE = "https://sendly.live/api/v1"

INHERITED = {
    "verificationId": "bv_2",
    "status": "submitted",
    "type": "toll_free",
    "tollFreeNumber": "+18885550100",
    "inheritedFrom": "ws_1",
    "newNumber": True,
}


def _body(httpx_mock):
    return json.loads(httpx_mock.get_request().content)


class TestInheritVerification:
    def test_asks_for_a_new_number(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces/ws_2/verification/inherit",
            method="POST",
            status_code=201,
            json=INHERITED,
        )

        result = client.enterprise.workspaces.inherit_verification(
            "ws_2", "ws_1", purchase_new_number=True
        )

        assert _body(httpx_mock)["purchaseNewNumber"] is True
        assert result["newNumber"] is True
        client.close()

    def test_default_call_omits_the_flag(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces/ws_2/verification/inherit",
            method="POST",
            status_code=201,
            json={k: v for k, v in INHERITED.items() if k != "newNumber"},
        )

        client.enterprise.workspaces.inherit_verification("ws_2", "ws_1")

        assert "purchaseNewNumber" not in _body(httpx_mock)
        client.close()

    @pytest.mark.asyncio
    async def test_asks_for_a_new_number_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces/ws_2/verification/inherit",
            method="POST",
            status_code=201,
            json=INHERITED,
        )

        await client.enterprise.workspaces.inherit_verification(
            "ws_2", "ws_1", purchase_new_number=True
        )

        assert _body(httpx_mock)["purchaseNewNumber"] is True
        await client.close()


CREDIT_TOTALS = {
    "period": "30d",
    "totalBalance": 500,
    "totalLifetime": 1500,
    "totalUsed": 1000,
    "workspaceCount": 3,
}


class TestCreditAnalytics:
    def test_reads_the_totals(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/analytics/credits", method="GET", json=CREDIT_TOTALS
        )

        credits = client.enterprise.analytics.credits()

        assert credits.total_balance == 500
        assert credits.total_lifetime == 1500
        assert credits.total_used == 1000
        assert credits.workspace_count == 3
        assert credits.data == []
        client.close()

    @pytest.mark.asyncio
    async def test_reads_the_totals_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/analytics/credits?period=7d",
            method="GET",
            json={**CREDIT_TOTALS, "period": "7d"},
        )

        credits = await client.enterprise.analytics.credits(period="7d")

        assert credits.total_used == 1000
        await client.close()


ADDRESS = {
    "street": "1 Main St",
    "city": "Austin",
    "state": "TX",
    "zip": "78701",
    "country": "US",
}


class TestAsyncSubmitVerification:
    @pytest.mark.asyncio
    async def test_sends_the_callers_keys(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces/ws_1/verification/submit",
            method="POST",
            json={"verificationId": "bv_1", "status": "submitted"},
        )

        await client.enterprise.workspaces.submit_verification(
            "ws_1", businessName="Acme", address=ADDRESS
        )

        assert _body(httpx_mock) == {"businessName": "Acme", "address": ADDRESS}
        await client.close()

    @pytest.mark.asyncio
    async def test_positional_data_drops_empty_values(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces/ws_1/verification/submit",
            method="POST",
            json={"verificationId": "bv_1", "status": "submitted"},
        )

        await client.enterprise.workspaces.submit_verification(
            "ws_1", {"businessName": "Acme", "website": None}
        )

        assert _body(httpx_mock) == {"businessName": "Acme"}
        await client.close()

    @pytest.mark.asyncio
    async def test_resubmit_sends_only_what_changed(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces/ws_1/verification/submit",
            method="POST",
            json={"verificationId": "bv_1", "status": "submitted"},
        )

        await client.enterprise.workspaces.resubmit_verification(
            "ws_1", contact={"email": "new@acme.test"}
        )

        assert _body(httpx_mock) == {"contact": {"email": "new@acme.test"}}
        await client.close()


WORKSPACE = {
    "id": "ws_1",
    "name": "Acme",
    "slug": "acme",
    "createdAt": "2026-01-01T00:00:00.000Z",
    "verification": {
        "status": "verified",
        "type": "toll_free",
        "tollFreeNumber": "+18885551234",
        "businessName": "Acme LLC",
    },
    "credits": 250,
    "keyCount": 2,
}


class TestGetWorkspace:
    def test_reads_verification_and_credits(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces/ws_1", method="GET", json=WORKSPACE
        )

        workspace = client.enterprise.workspaces.get("ws_1")

        assert workspace.verification_status == "verified"
        assert workspace.verification_type == "toll_free"
        assert workspace.toll_free_number == "+18885551234"
        assert workspace.business_name == "Acme LLC"
        assert workspace.credit_balance == 250
        assert workspace.key_count == 2
        assert workspace.created_at == "2026-01-01T00:00:00.000Z"
        client.close()

    def test_workspace_without_verification(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces/ws_1",
            method="GET",
            json={**WORKSPACE, "verification": None, "credits": 0},
        )

        workspace = client.enterprise.workspaces.get("ws_1")

        assert workspace.verification_status is None
        assert workspace.toll_free_number is None
        assert workspace.credit_balance == 0
        client.close()

    @pytest.mark.asyncio
    async def test_reads_verification_and_credits_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces/ws_1", method="GET", json=WORKSPACE
        )

        workspace = await client.enterprise.workspaces.get("ws_1")

        assert workspace.verification_status == "verified"
        assert workspace.credit_balance == 250
        await client.close()


class TestEnterpriseWebhook:
    def test_set_returns_the_signing_secret(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/webhooks",
            method="POST",
            json={
                "url": "https://example.com/hook",
                "events": None,
                "workspaces": None,
                "signingSecret": "whsec_1",
            },
        )

        webhook = client.enterprise.webhooks.set("https://example.com/hook")

        assert webhook.url == "https://example.com/hook"
        assert webhook.signing_secret == "whsec_1"
        client.close()

    def test_set_sends_events_and_workspaces(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/webhooks",
            method="POST",
            json={
                "url": "https://example.com/hook",
                "events": ["message.delivered"],
                "workspaces": ["ws_1"],
            },
        )

        webhook = client.enterprise.webhooks.set(
            "https://example.com/hook", events=["message.delivered"], workspaces=["ws_1"]
        )

        assert _body(httpx_mock) == {
            "url": "https://example.com/hook",
            "events": ["message.delivered"],
            "workspaces": ["ws_1"],
        }
        assert webhook.events == ["message.delivered"]
        assert webhook.signing_secret is None
        client.close()

    def test_get_reads_the_webhook(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/webhooks",
            method="GET",
            json={"url": "https://example.com/hook", "events": None, "workspaces": ["ws_1"]},
        )

        webhook = client.enterprise.webhooks.get()

        assert webhook.url == "https://example.com/hook"
        assert webhook.workspaces == ["ws_1"]
        assert webhook.signing_secret is None
        client.close()

    def test_get_without_a_webhook_raises_not_found(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/webhooks",
            method="GET",
            json={"url": None, "events": None, "workspaces": None},
        )

        with pytest.raises(NotFoundError) as exc_info:
            client.enterprise.webhooks.get()

        assert exc_info.value.code == "not_found"
        client.close()

    def test_url_keeps_its_4_2_type(self):
        field = EnterpriseWebhook.model_fields["url"]

        assert field.annotation is str
        assert field.is_required()

    @pytest.mark.asyncio
    async def test_set_returns_the_signing_secret_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/webhooks",
            method="POST",
            json={
                "url": "https://example.com/hook",
                "events": None,
                "workspaces": ["ws_1"],
                "signingSecret": "whsec_1",
            },
        )

        webhook = await client.enterprise.webhooks.set(
            "https://example.com/hook", workspaces=["ws_1"]
        )

        assert webhook.signing_secret == "whsec_1"
        assert _body(httpx_mock)["workspaces"] == ["ws_1"]
        await client.close()

    @pytest.mark.asyncio
    async def test_get_without_a_webhook_raises_not_found_async(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/webhooks",
            method="GET",
            json={"url": None, "events": None, "workspaces": None},
        )

        with pytest.raises(NotFoundError):
            await client.enterprise.webhooks.get()

        await client.close()
