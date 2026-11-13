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


class TestUploadVerificationDocument:
    URL = f"{BASE}/enterprise/verification-document/upload"

    def test_guesses_the_type_from_the_extension(
        self, api_key, tmp_path, httpx_mock: HTTPXMock
    ):
        doc = tmp_path / "ein-letter.pdf"
        doc.write_bytes(b"%PDF-1.4 fake")
        client = Sendly(api_key)
        httpx_mock.add_response(url=self.URL, method="POST", json={"url": "u", "id": "upload_1"})

        client.enterprise.upload_verification_document(str(doc), verification_id="bv_1")

        content = httpx_mock.get_request().content
        assert b'filename="ein-letter.pdf"\r\nContent-Type: application/pdf' in content
        assert b'name="verificationId"\r\n\r\nbv_1' in content
        client.close()

    def test_sends_the_content_type_given(self, api_key, tmp_path, httpx_mock: HTTPXMock):
        doc = tmp_path / "scan"
        doc.write_bytes(b"\x89PNG fake")
        client = Sendly(api_key)
        httpx_mock.add_response(url=self.URL, method="POST", json={"url": "u", "id": "upload_1"})

        result = client.enterprise.upload_verification_document(
            str(doc), content_type="image/png"
        )

        assert result == {"url": "u", "id": "upload_1"}
        content = httpx_mock.get_request().content
        assert b'filename="scan"\r\nContent-Type: image/png' in content
        client.close()

    async def test_sends_the_content_type_given_async(
        self, api_key, tmp_path, httpx_mock: HTTPXMock
    ):
        doc = tmp_path / "scan"
        doc.write_bytes(b"\x89PNG fake")
        client = AsyncSendly(api_key)
        httpx_mock.add_response(url=self.URL, method="POST", json={"url": "u", "id": "upload_1"})

        await client.enterprise.upload_verification_document(str(doc), content_type="image/png")

        content = httpx_mock.get_request().content
        assert b'filename="scan"\r\nContent-Type: image/png' in content
        await client.close()


WORKSPACE_PAGE = {
    "workspaces": [
        {
            "id": "ws_1",
            "name": "Acme East",
            "slug": None,
            "status": "active",
            "verificationStatus": "verified",
            "verificationType": "toll_free",
            "tollFreeNumber": "+18885550100",
            "creditBalance": 1200,
            "keyCount": 2,
            "messages30d": 40,
            "delivered30d": 38,
            "failed30d": 2,
            "createdAt": "2026-10-01T00:00:00Z",
        }
    ],
    "pagination": {"total": 41, "limit": 20, "page": 2, "totalPages": 3, "hasMore": True},
    "summary": {"totalCredits": 1200, "pendingVerifications": []},
    "maxWorkspaces": 100,
    "workspacesUsed": 41,
}


class TestListWorkspaces:
    def test_sends_the_filters(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(method="GET", json=WORKSPACE_PAGE)

        result = client.enterprise.workspaces.list(
            limit=20,
            page=2,
            search="acme",
            status="active",
            verification="unverified",
            sort="credits_desc",
            tags=["tag_1", "tag_2"],
        )

        request = httpx_mock.get_request()
        assert request.url.path == "/api/v1/enterprise/workspaces"
        assert dict(request.url.params) == {
            "limit": "20",
            "page": "2",
            "search": "acme",
            "status": "active",
            "verification": "unverified",
            "sort": "credits_desc",
            "tags": "tag_1,tag_2",
        }
        assert result.workspaces[0].slug is None
        assert result.workspaces[0].credit_balance == 1200
        assert result.pagination.total_pages == 3
        assert result.pagination.has_more is True
        client.close()

    def test_without_filters_sends_no_query(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces", method="GET", json=WORKSPACE_PAGE
        )

        client.enterprise.workspaces.list()

        assert not httpx_mock.get_request().url.params
        client.close()

    async def test_compact_list_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces?compact=true&tags=tag_1",
            method="GET",
            json={
                "workspaces": [{"id": "ws_1", "name": "Acme East", "creditBalance": 1200}],
                "summary": {"totalCredits": 1200, "pendingVerifications": []},
                "maxWorkspaces": 100,
                "workspacesUsed": 1,
            },
        )

        result = await client.enterprise.workspaces.list(compact=True, tags="tag_1")

        assert result.workspaces[0].credit_balance == 1200
        assert result.workspaces[0].created_at is None
        assert result.pagination is None
        await client.close()


FIXTURE_SUMMARY = {
    "totalCredits": 1500,
    "pendingVerifications": [
        {"id": "00000000-0000-4000-8000-000000000011", "name": "Bright Smiles Dental"}
    ],
    "verificationBreakdown": {
        "verified": 1,
        "pending": 1,
        "submitted": 0,
        "rejected": 0,
        "unverified": 0,
    },
}

FIXTURE_WORKSPACE_PAGE = {
    "workspaces": [
        {
            "id": "00000000-0000-4000-8000-000000000011",
            "name": "Bright Smiles Dental",
            "slug": "bright-smiles-dental",
            "status": "active",
            "suspendedAt": None,
            "suspendReason": None,
            "verificationStatus": "pending",
            "rejectionReason": None,
            "verificationType": "toll_free",
            "tollFreeNumber": None,
            "creditBalance": 0,
            "keyCount": 1,
            "messages30d": 0,
            "delivered30d": 0,
            "failed30d": 0,
            "monthlyMessageQuota": None,
            "messagesThisMonth": 0,
            "quotaResetAt": None,
            "createdAt": "2026-01-08T00:00:00.000Z",
            "tags": [
                {
                    "id": "00000000-0000-4000-8000-000000000030",
                    "enterpriseAccountId": "00000000-0000-4000-8000-000000000031",
                    "name": "dental",
                    "color": "#6366f1",
                    "createdAt": "2026-01-01T00:00:00.000Z",
                }
            ],
        },
        {
            "id": "00000000-0000-4000-8000-000000000010",
            "name": "Acme Clinics",
            "slug": "acme-clinics",
            "status": "active",
            "suspendedAt": None,
            "suspendReason": None,
            "verificationStatus": "verified",
            "rejectionReason": None,
            "verificationType": "toll_free",
            "tollFreeNumber": "+15555550100",
            "creditBalance": 1500,
            "keyCount": 1,
            "messages30d": 120,
            "delivered30d": 118,
            "failed30d": 2,
            "monthlyMessageQuota": None,
            "messagesThisMonth": 40,
            "quotaResetAt": None,
            "createdAt": "2026-01-01T00:00:00.000Z",
            "tags": [],
        },
    ],
    "pagination": {"total": 2, "limit": 50, "page": 1, "totalPages": 1, "hasMore": False},
    "summary": FIXTURE_SUMMARY,
    "maxWorkspaces": 25,
    "workspacesUsed": 2,
}

FIXTURE_COMPACT_WORKSPACES = {
    "workspaces": [
        {
            "id": "00000000-0000-4000-8000-000000000011",
            "name": "Bright Smiles Dental",
            "creditBalance": 0,
        },
        {
            "id": "00000000-0000-4000-8000-000000000010",
            "name": "Acme Clinics",
            "creditBalance": 1500,
        },
    ],
    "summary": FIXTURE_SUMMARY,
    "maxWorkspaces": 25,
    "workspacesUsed": 2,
}


def _assert_fixture_summary(summary):
    assert summary.total_credits == 1500
    assert len(summary.pending_verifications) == 1
    assert summary.pending_verifications[0].id == "00000000-0000-4000-8000-000000000011"
    assert summary.pending_verifications[0].name == "Bright Smiles Dental"
    breakdown = summary.verification_breakdown
    assert (breakdown.verified, breakdown.pending, breakdown.submitted) == (1, 1, 0)
    assert (breakdown.rejected, breakdown.unverified) == (0, 0)


class TestListWorkspacesSummary:
    def test_reads_the_full_list_and_its_summary(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces", method="GET", json=FIXTURE_WORKSPACE_PAGE
        )

        result = client.enterprise.workspaces.list()

        assert [w.name for w in result.workspaces] == ["Bright Smiles Dental", "Acme Clinics"]
        assert result.workspaces[1].toll_free_number == "+15555550100"
        assert result.pagination.total == 2
        assert result.max_workspaces == 25
        _assert_fixture_summary(result.summary)
        client.close()

    async def test_reads_the_compact_list_and_its_summary_async(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces?compact=true",
            method="GET",
            json=FIXTURE_COMPACT_WORKSPACES,
        )

        result = await client.enterprise.workspaces.list(compact=True)

        assert result.workspaces[1].credit_balance == 1500
        assert result.pagination is None
        _assert_fixture_summary(result.summary)
        await client.close()

    def test_summary_is_none_when_the_api_leaves_it_out(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        body = {k: v for k, v in FIXTURE_WORKSPACE_PAGE.items() if k != "summary"}
        httpx_mock.add_response(url=f"{BASE}/enterprise/workspaces", method="GET", json=body)

        assert client.enterprise.workspaces.list().summary is None
        client.close()
