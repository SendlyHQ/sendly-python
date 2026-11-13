"""
Tests for the short codes resource against the bodies the API sends
"""

import json

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import SendlyError, ValidationError
from sendly.types import (
    ShortCodeApplicationInput,
    ShortCodeApplicationView,
    ShortCodeListResponse,
    ShortCodePreflight,
    ShortCodeSubmitInput,
)

BASE = "https://sendly.live/api/v1"

LEASE = {
    "monthlyCents": 100000,
    "minimumTermMonths": 3,
    "state": "not_started",
    "billingEnabled": False,
    "startedAt": None,
    "nextChargeAt": None,
    "paidThrough": None,
    "termEndsAt": None,
    "endsAt": None,
    "cancelRequestedAt": None,
    "pastDue": None,
    "dueMonths": 0,
    "dueCents": 0,
}

APPLICATION = {
    "id": "sc_1",
    "shortCode": None,
    "countryCode": "US",
    "status": "requested",
    "reviewStatus": "awaiting_review",
    "reviewNote": None,
    "orderType": "new",
    "codeType": "random",
    "contentProviderSameAsBrand": True,
    "sampleMessages": ["Acme: your order shipped. Reply STOP to opt out."],
    "useCase": "Order and delivery alerts",
    "optInFlow": "Customers text JOIN to the code after checkout.",
    "expectedMonthlyVolume": "50000",
    "expectedDailyVolume": "2000",
    "helpResponse": None,
    "stopConfirmation": None,
    "optInConfirmation": None,
    "privacyPolicyUrl": "https://acme.example/privacy",
    "termsUrl": "https://acme.example/terms",
    "messageFrequency": "Up to 4 messages per order",
    "campaignKeyword": "JOIN",
    "requestedDigits": None,
    "losingProvider": None,
    "brandContactName": "Ada Lovelace",
    "brandContactEmail": "ada@acme.example",
    "brandContactPhone": "+15125550100",
    "contentProviderLegalName": None,
    "contentProviderEin": None,
    "contentProviderContactName": None,
    "contentProviderContactEmail": None,
    "contentProviderContactPhone": None,
    "brandRegistrationStatus": "not_started",
    "contentProviderRegistrationStatus": "not_started",
    "submittedAt": "2026-09-01T10:00:00.000Z",
    "reviewedAt": None,
    "filedAt": None,
    "activatedAt": None,
    "registryRevettingDueAt": None,
    "createdAt": "2026-08-30T10:00:00.000Z",
    "updatedAt": "2026-09-01T10:00:00.000Z",
}

VIEW = {
    "enabled": True,
    "application": APPLICATION,
    "prefill": {
        "source": "tendlc",
        "legalName": "Acme Holdings LLC",
        "address": {"city": "Austin", "postalCode": "78701"},
        "contact": {"email": "ada@acme.example"},
    },
    "editable": False,
    "lockMessage": "Sendly is reviewing this application.",
    "canStartNewApplication": False,
    "generatedDefaults": None,
    "requiredDocuments": ["order_brief", "brand_registration"],
    "missingDocuments": ["brand_registration"],
    "documents": [
        {
            "kind": "order_brief",
            "templateReady": True,
            "signedAt": "2026-09-02T10:00:00.000Z",
            "signedByName": "Ada Lovelace",
            "awaitingSignature": False,
        }
    ],
    "quote": {
        "codeType": "random",
        "monthlyUsd": 1000,
        "setupUsd": 999,
        "currency": "USD",
        "autoBilled": False,
        "setupCents": 99900,
        "monthlyCents": 100000,
        "minimumTermMonths": 3,
        "setupChargedAt": "submit",
        "leaseStartsAt": "go_live",
    },
    "billing": {
        "setupFee": {
            "amountCents": 99900,
            "status": "paid",
            "chargedAt": "submit",
            "paidAt": "2026-09-01T10:00:00.000Z",
            "refundedCents": 0,
            "refundedAt": None,
        },
        "lease": {**LEASE, "startsAt": "go_live"},
        "terms": {
            "version": "2026-09",
            "acceptedVersion": "2026-09",
            "acceptedAt": "2026-09-01T10:00:00.000Z",
        },
        "refundPolicy": "full_refund_before_filing",
        "exempt": None,
        "charges": [
            {
                "id": "scc_1",
                "kind": "setup",
                "amountCents": 99900,
                "status": "paid",
                "paidAt": "2026-09-01T10:00:00.000Z",
                "refundedCents": 0,
                "refundedAt": None,
                "periodStart": None,
                "periodEnd": None,
                "createdAt": "2026-09-01T10:00:00.000Z",
            }
        ],
    },
    "verification": {"verified": True, "state": "verified", "href": "/verify"},
    "carriers": {
        "approved": 1,
        "total": 4,
        "overall": "in_progress",
        "byCarrier": [
            {
                "carrier": "ATT",
                "label": "AT&T",
                "status": "approved",
                "updatedAt": "2026-09-10T10:00:00.000Z",
            },
            {"carrier": "TMOBILE", "label": "T-Mobile", "status": "in_review", "updatedAt": None},
        ],
    },
}


EMPTY_PREFLIGHT = {
    "ok": True,
    "issues": [],
    "requiredDocuments": [],
    "missingDocuments": [],
    "documents": [],
}


def _body(request):
    return json.loads(request.read().decode())


class TestShortCodesList:
    def test_list(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/short_codes",
            method="GET",
            json={
                "shortCodes": [
                    {
                        "id": "sc_1",
                        "shortCode": "55123",
                        "countryCode": "US",
                        "status": "active",
                        "reviewStatus": "filed",
                        "useCase": "Order and delivery alerts",
                        "createdAt": "2026-08-30T10:00:00.000Z",
                        "billing": {
                            "setupFee": {"status": "paid", "amountCents": 99900},
                            "lease": {**LEASE, "state": "running"},
                        },
                    }
                ]
            },
        )

        result = client.short_codes.list()

        assert isinstance(result, ShortCodeListResponse)
        code = result.short_codes[0]
        assert code.short_code == "55123"
        assert code.status == "active"
        assert code.review_status == "filed"
        assert code.billing.setup_fee.status == "paid"
        assert code.billing.lease.state == "running"
        client.close()

    def test_not_enabled_404(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key, max_retries=0)
        httpx_mock.add_response(
            url=f"{BASE}/short_codes",
            method="GET",
            status_code=404,
            json={"error": "short_codes_not_enabled", "message": "Short codes are not enabled"},
        )

        with pytest.raises(SendlyError) as exc:
            client.short_codes.list()
        assert exc.value.code == "short_codes_not_enabled"
        assert exc.value.status_code == 404
        client.close()


class TestShortCodeApplication:
    def test_get(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/short_codes/application", method="GET", json=VIEW)

        view = client.short_codes.application.get()

        assert isinstance(view, ShortCodeApplicationView)
        assert view.application.id == "sc_1"
        assert view.application.review_status == "awaiting_review"
        assert view.application.sample_messages == [
            "Acme: your order shipped. Reply STOP to opt out."
        ]
        assert view.prefill.source == "tendlc"
        assert view.prefill.legal_name == "Acme Holdings LLC"
        assert view.prefill.address.postal_code == "78701"
        assert view.lock_message == "Sendly is reviewing this application."
        assert view.missing_documents == ["brand_registration"]
        assert view.documents[0].signed_by_name == "Ada Lovelace"
        assert view.quote.setup_cents == 99900
        assert view.billing.setup_fee.status == "paid"
        assert view.billing.lease.starts_at == "go_live"
        assert view.billing.terms.accepted_version == "2026-09"
        assert view.billing.charges[0].kind == "setup"
        assert view.verification.verified is True
        assert view.carriers.by_carrier[1].label == "T-Mobile"
        assert view.carriers.by_carrier[1].updated_at is None
        client.close()

    def test_update_sends_only_set_fields_and_the_key(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/short_codes/application",
            method="PUT",
            json={**VIEW, "editable": True, "ignoredFields": ["status"]},
        )

        view = client.short_codes.application.update(
            {
                "use_case": "Delivery alerts for Acme orders",
                "messageFrequency": "4 messages per month",
                "terms_url": None,
            },
            idempotency_key="sc-save-1",
        )

        request = httpx_mock.get_request()
        assert request.headers["Idempotency-Key"] == "sc-save-1"
        assert _body(request) == {
            "useCase": "Delivery alerts for Acme orders",
            "messageFrequency": "4 messages per month",
            "termsUrl": None,
        }
        assert view.editable is True
        assert view.ignored_fields == ["status"]
        client.close()

    def test_update_accepts_a_model(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/short_codes/application", method="PUT", json=VIEW)

        client.short_codes.application.update(
            ShortCodeApplicationInput(code_type="vanity", requested_digits="55123")
        )

        assert _body(httpx_mock.get_request()) == {"codeType": "vanity", "requestedDigits": "55123"}
        client.close()

    def test_update_rejects_a_non_mapping(self, api_key):
        client = Sendly(api_key)
        with pytest.raises(ValidationError):
            client.short_codes.application.update("use case")  # type: ignore[arg-type]
        client.close()

    def test_check(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/short_codes/application/preflight",
            method="POST",
            json={
                "ok": False,
                "issues": [{"path": "helpResponse", "message": "Add a HELP reply."}],
                "requiredDocuments": ["order_brief"],
                "missingDocuments": ["order_brief"],
                "documents": [],
            },
        )

        result = client.short_codes.application.check({"campaign_keyword": "JOIN"})

        assert isinstance(result, ShortCodePreflight)
        assert result.ok is False
        assert result.issues[0].path == "helpResponse"
        assert result.missing_documents == ["order_brief"]
        assert _body(httpx_mock.get_request()) == {"campaignKeyword": "JOIN"}
        client.close()

    def test_check_with_nothing_sends_an_empty_body(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/short_codes/application/preflight",
            method="POST",
            json=EMPTY_PREFLIGHT,
        )

        assert client.short_codes.application.check().ok is True
        client.close()

    def test_submit(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/short_codes/application/submit",
            method="POST",
            json={
                **VIEW,
                "submitted": True,
                "alreadySubmitted": False,
                "notified": True,
                "payment": {"status": "paid", "charged": True},
            },
        )

        result = client.short_codes.application.submit(
            {"help_response": "Acme alerts: help at acme.example. Msg&data rates may apply."},
            accept_terms=True,
            idempotency_key="sc-submit-1",
        )

        request = httpx_mock.get_request()
        assert request.headers["Idempotency-Key"] == "sc-submit-1"
        assert _body(request) == {
            "helpResponse": "Acme alerts: help at acme.example. Msg&data rates may apply.",
            "acceptTerms": True,
        }
        assert result.submitted is True
        assert result.already_submitted is False
        assert result.payment.charged is True
        client.close()

    def test_submit_with_a_submit_input(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/short_codes/application/submit",
            method="POST",
            json={**VIEW, "submitted": True, "alreadySubmitted": True, "notified": False},
        )

        result = client.short_codes.application.submit(ShortCodeSubmitInput(accept_terms=True))

        assert _body(httpx_mock.get_request()) == {"acceptTerms": True}
        assert result.already_submitted is True
        assert result.payment is None
        client.close()


class TestAsyncShortCodes:
    async def test_async_list_and_get(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/short_codes", method="GET", json={"shortCodes": []})
        httpx_mock.add_response(url=f"{BASE}/short_codes/application", method="GET", json=VIEW)

        assert (await client.short_codes.list()).short_codes == []
        view = await client.short_codes.application.get()
        assert view.application.use_case == "Order and delivery alerts"
        await client.close()

    async def test_async_update_check_submit(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/short_codes/application", method="PUT", json=VIEW)
        httpx_mock.add_response(
            url=f"{BASE}/short_codes/application/preflight",
            method="POST",
            json=EMPTY_PREFLIGHT,
        )
        httpx_mock.add_response(
            url=f"{BASE}/short_codes/application/submit",
            method="POST",
            json={**VIEW, "submitted": True, "alreadySubmitted": False, "notified": True},
        )

        await client.short_codes.application.update({"use_case": "Alerts"}, idempotency_key="k1")
        assert (await client.short_codes.application.check()).ok is True
        await client.short_codes.application.submit(accept_terms=True, idempotency_key="k2")

        put, _, submit = httpx_mock.get_requests()
        assert put.method == "PUT"
        assert put.headers["Idempotency-Key"] == "k1"
        assert _body(put) == {"useCase": "Alerts"}
        assert submit.headers["Idempotency-Key"] == "k2"
        assert _body(submit) == {"acceptTerms": True}
        await client.close()
