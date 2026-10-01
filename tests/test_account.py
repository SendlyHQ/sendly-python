"""
Tests for Account resource API-key management

These pin the paths the server actually serves: listing, fetching and usage
live under /account/keys, and revocation is a PATCH to
/account/keys/{id}/revoke.
"""

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.types import Account, ApiKey, CreditTransaction


@pytest.fixture
def mock_key():
    return {
        "id": "key_123",
        "name": "Production",
        "type": "test",
        "prefix": "sk_test_v1_abc...",
        "scopes": ["sms:send"],
        "isActive": True,
        "createdAt": "2026-01-20T10:00:00Z",
        "lastUsedAt": None,
        "expiresAt": None,
    }


@pytest.fixture
def mock_usage():
    return {
        "keyId": "key_123",
        "keyName": "Production",
        "summary": {"totalRequests": 2, "totalCredits": 4, "lastUsed": None},
        "recentRequests": [],
        "endpointBreakdown": [],
    }


class TestListApiKeys:
    def test_list_api_keys(self, api_key, mock_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys",
            method="GET",
            json={"keys": [mock_key]},
        )

        result = client.account.list_api_keys()

        assert len(result) == 1
        assert isinstance(result[0], ApiKey)
        assert result[0].id == "key_123"
        assert result[0].name == "Production"
        assert result[0].last_four is None

        client.close()

    @pytest.mark.asyncio
    async def test_list_api_keys_async(self, api_key, mock_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys",
            method="GET",
            json={"keys": [mock_key]},
        )

        result = await client.account.list_api_keys()

        assert len(result) == 1
        assert result[0].id == "key_123"

        await client.close()


class TestGetApiKey:
    def test_get_api_key(self, api_key, mock_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys/key_123",
            method="GET",
            json=mock_key,
        )

        result = client.account.get_api_key("key_123")

        assert isinstance(result, ApiKey)
        assert result.id == "key_123"
        assert result.last_four is None

        client.close()

    @pytest.mark.asyncio
    async def test_get_api_key_async(self, api_key, mock_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys/key_123",
            method="GET",
            json=mock_key,
        )

        result = await client.account.get_api_key("key_123")

        assert result.id == "key_123"

        await client.close()


class TestGetApiKeyUsage:
    def test_get_api_key_usage(self, api_key, mock_usage, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys/key_123/usage",
            method="GET",
            json=mock_usage,
        )

        result = client.account.get_api_key_usage("key_123")

        assert result["summary"]["totalRequests"] == 2

        client.close()

    @pytest.mark.asyncio
    async def test_get_api_key_usage_async(self, api_key, mock_usage, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys/key_123/usage",
            method="GET",
            json=mock_usage,
        )

        result = await client.account.get_api_key_usage("key_123")

        assert result["keyId"] == "key_123"

        await client.close()


class TestRevokeApiKey:
    def test_revoke_api_key_patches_revoke_path(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys/key_123/revoke",
            method="PATCH",
            json={"id": "key_123", "name": "Production", "revoked": True},
        )

        client.account.revoke_api_key("key_123")

        request = httpx_mock.get_request()
        assert request.method == "PATCH"
        assert str(request.url).endswith("/account/keys/key_123/revoke")

        client.close()

    def test_revoke_api_key_requires_id(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValueError, match="API key ID is required"):
            client.account.revoke_api_key("")

        client.close()

    @pytest.mark.asyncio
    async def test_revoke_api_key_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys/key_123/revoke",
            method="PATCH",
            json={"id": "key_123", "name": "Production", "revoked": True},
        )

        await client.account.revoke_api_key("key_123")

        request = httpx_mock.get_request()
        assert request.method == "PATCH"
        assert str(request.url).endswith("/account/keys/key_123/revoke")

        await client.close()


ACCOUNT_BODY = {
    "user": {"id": "user_1", "email": "a@b.co", "createdAt": "2026-01-01T00:00:00Z"},
    "organization": {"id": "org_1", "name": "Acme", "isPersonal": False},
    "credits": {"balance": 100, "reservedBalance": 0},
    "verification": None,
    "apiKey": {
        "id": "key_1",
        "name": "k",
        "type": "test",
        "scopes": [],
        "createdAt": "2026-01-01T00:00:00Z",
        "lastUsedAt": None,
    },
    "limits": {"messagesPerMinute": 60, "messagesPerDay": 100},
}


class TestGetAccount:
    def test_reads_the_user_block(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account", method="GET", json=ACCOUNT_BODY
        )

        account = client.account.get()

        assert account.id == "user_1"
        assert account.email == "a@b.co"
        assert account.created_at == "2026-01-01T00:00:00Z"
        assert account.organization["id"] == "org_1"
        assert account.credits == {"balance": 100, "reservedBalance": 0}
        assert account.api_key["id"] == "key_1"
        assert account.limits["messagesPerDay"] == 100
        assert account.verification is None
        client.close()

    def test_missing_credits_row_reads_as_numbers(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        body = {**ACCOUNT_BODY, "credits": {"balance": "0", "reservedBalance": "0"}}
        httpx_mock.add_response(url="https://sendly.live/api/v1/account", method="GET", json=body)

        account = client.account.get()

        assert account.credits == {"balance": 0, "reservedBalance": 0}
        client.close()

    @pytest.mark.asyncio
    async def test_reads_the_user_block_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account", method="GET", json=ACCOUNT_BODY
        )

        account = await client.account.get()

        assert account.id == "user_1"
        assert account.organization["name"] == "Acme"
        await client.close()


TRANSACTIONS_URL = "https://sendly.live/api/v1/credits/transactions"


class TestGetCreditTransactions:
    def test_unwraps_the_transactions_envelope(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{TRANSACTIONS_URL}?limit=10&offset=10",
            method="GET",
            json={
                "transactions": [
                    {
                        "id": "t1",
                        "amount": -2,
                        "balance_after": 98,
                        "type": "usage",
                        "description": "SMS to US",
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ]
            },
        )

        transactions = client.account.get_credit_transactions(limit=10, offset=10)

        assert len(transactions) == 1
        assert transactions[0].balance_after == 98
        assert transactions[0].created_at == "2026-01-01T00:00:00Z"
        assert httpx_mock.get_request().url.params["offset"] == "10"
        client.close()

    @pytest.mark.asyncio
    async def test_unwraps_the_transactions_envelope_async(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{TRANSACTIONS_URL}?limit=10&offset=10",
            method="GET",
            json={
                "transactions": [
                    {
                        "id": "t1",
                        "amount": -2,
                        "balance_after": 98,
                        "type": "usage",
                        "description": "SMS to US",
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ]
            },
        )

        transactions = await client.account.get_credit_transactions(limit=10, offset=10)

        assert len(transactions) == 1
        assert transactions[0].balance_after == 98
        await client.close()

    def test_filters_by_type(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{TRANSACTIONS_URL}?type=refund", method="GET", json={"transactions": []}
        )

        assert client.account.get_credit_transactions(type="refund") == []
        client.close()

    def test_every_recorded_type_parses(self, api_key, httpx_mock: HTTPXMock):
        from sendly.types import TransactionType

        client = Sendly(api_key)
        rows = [
            {
                "id": "t1",
                "amount": 50,
                "balance_after": 0,
                "type": "transfer",
                "description": "Transfer from Acme",
                "created_at": "2026-01-03T00:00:00Z",
            },
            {
                "id": "t2",
                "amount": 500,
                "balance_after": 550,
                "type": "admin_grant",
                "description": None,
                "created_at": "2026-01-02T00:00:00Z",
            },
            {
                "id": "t3",
                "amount": -2,
                "balance_after": 548,
                "type": "usage",
                "description": "SMS to US",
                "created_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": "t4",
                "amount": 10,
                "balance_after": 558,
                "type": "a_future_kind",
                "description": None,
                "created_at": "2026-01-01T00:00:00Z",
            },
        ]
        httpx_mock.add_response(url=TRANSACTIONS_URL, method="GET", json={"transactions": rows})

        transactions = client.account.get_credit_transactions()

        assert [t.type for t in transactions] == [
            TransactionType.TRANSFER,
            TransactionType.ADMIN_GRANT,
            TransactionType.USAGE,
            "a_future_kind",
        ]
        assert isinstance(transactions[3].type, TransactionType)
        assert transactions[3].type.value == "a_future_kind"
        assert transactions[3].type.name == "UNKNOWN"
        assert transactions[1].description is None
        client.close()


CREATED_KEY_BODY = {
    "id": "key_9",
    "name": "Prod",
    "key": "sk_live_v1_secret",
    "keyPrefix": "sk_live_v1_s",
    "type": "live",
    "createdAt": "2026-01-01T00:00:00Z",
    "expiresAt": None,
    "apiKey": {
        "id": "key_9",
        "name": "Prod",
        "type": "live",
        "prefix": "sk_live_v1_s...",
        "scopes": ["sms:send"],
        "permissions": ["sms:send"],
        "isActive": True,
        "isRevoked": False,
        "createdAt": "2026-01-01T00:00:00Z",
        "lastUsedAt": None,
        "expiresAt": None,
    },
}


class TestCreateApiKey:
    def test_sends_the_requested_type(self, api_key, httpx_mock: HTTPXMock):
        import json

        client = Sendly(api_key)
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys", method="POST", json=CREATED_KEY_BODY
        )

        result = client.account.create_api_key("Prod", type="live")

        assert json.loads(httpx_mock.get_request().content) == {"name": "Prod", "type": "live"}
        assert result["key"] == "sk_live_v1_secret"
        assert result["apiKey"]["id"] == "key_9"
        client.close()

    def test_sends_scopes(self, api_key, httpx_mock: HTTPXMock):
        import json

        client = Sendly(api_key)
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys", method="POST", json=CREATED_KEY_BODY
        )

        client.account.create_api_key("Prod", type="live", scopes=["sms:send"])

        assert json.loads(httpx_mock.get_request().content) == {
            "name": "Prod",
            "type": "live",
            "scopes": ["sms:send"],
        }
        client.close()

    def test_omits_type_when_not_given(self, api_key, httpx_mock: HTTPXMock):
        import json

        client = Sendly(api_key)
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys", method="POST", json=CREATED_KEY_BODY
        )

        client.account.create_api_key("Dev")

        assert "type" not in json.loads(httpx_mock.get_request().content)
        client.close()

    def test_rejects_an_unknown_type(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValueError):
            client.account.create_api_key("Prod", type="admin")

        client.close()

    @pytest.mark.asyncio
    async def test_sends_the_requested_type_async(self, api_key, httpx_mock: HTTPXMock):
        import json

        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys", method="POST", json=CREATED_KEY_BODY
        )

        result = await client.account.create_api_key("Prod", type="live", scopes=["sms:send"])

        assert json.loads(httpx_mock.get_request().content) == {
            "name": "Prod",
            "type": "live",
            "scopes": ["sms:send"],
        }
        assert result["apiKey"]["id"] == "key_9"
        await client.close()


REVOKED_KEY_BODY = {
    "id": "key_1",
    "name": "Old",
    "type": "live",
    "prefix": "sk_live_v1_a...",
    "scopes": ["sms:send"],
    "isActive": False,
    "createdAt": "2026-01-01T00:00:00Z",
    "lastUsedAt": None,
    "expiresAt": None,
    "revokedAt": "2026-02-01T00:00:00Z",
}


class TestGetApiKeyRevocation:
    def test_reads_revocation_and_scopes(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys/key_1", method="GET", json=REVOKED_KEY_BODY
        )

        key = client.account.get_api_key("key_1")

        assert key.is_revoked is True
        assert key.permissions == ["sms:send"]
        assert key.is_active is False
        assert key.revoked_at == "2026-02-01T00:00:00Z"
        client.close()

    def test_active_key_is_not_revoked(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        body = {**REVOKED_KEY_BODY, "isActive": True, "revokedAt": None}
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys/key_1", method="GET", json=body
        )

        key = client.account.get_api_key("key_1")

        assert key.is_revoked is False
        client.close()

    @pytest.mark.asyncio
    async def test_reads_revocation_and_scopes_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys/key_1", method="GET", json=REVOKED_KEY_BODY
        )

        key = await client.account.get_api_key("key_1")

        assert key.is_revoked is True
        assert key.permissions == ["sms:send"]
        await client.close()


class TestCreditTransactionModel:
    @pytest.mark.parametrize(
        "kind,description",
        [("transfer", "Transfer from Acme"), ("admin_grant", None), ("admin_seed", None)],
    )
    def test_accepts_rows_the_ledger_records(self, kind, description):
        from sendly.types import CreditTransaction

        transaction = CreditTransaction(
            id="t1",
            type=kind,
            amount=10,
            balanceAfter=10,
            description=description,
            createdAt="2026-01-01T00:00:00Z",
        )

        assert transaction.type.value == kind
        assert transaction.description == description


class TestGetCreditsBalances:
    def test_reads_reserved_and_available(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/credits",
            method="GET",
            json={
                "balance": 100,
                "reservedBalance": 10,
                "availableBalance": 90,
                "billingMode": "prepaid",
            },
        )

        credits = client.account.get_credits()

        assert credits.reserved_balance == 10
        assert credits.available_balance == 90
        client.close()


class TestFieldsTheApiDoesNotSend:
    @pytest.mark.parametrize("model, field", [(Account, "name"), (CreditTransaction, "message_id")])
    def test_description_says_the_field_is_always_none(self, model, field):
        assert "Not returned by the API; always None" in model.model_fields[field].description


class TestUnreadableAccountResponses:
    def test_account_without_an_email_raises_invalid_response(
        self, api_key, httpx_mock: HTTPXMock
    ):
        from sendly.errors import SendlyError

        client = Sendly(api_key)
        body = {**ACCOUNT_BODY, "user": {"id": "user_1", "createdAt": "2026-01-01T00:00:00Z"}}
        httpx_mock.add_response(url="https://sendly.live/api/v1/account", method="GET", json=body)

        with pytest.raises(SendlyError) as exc_info:
            client.account.get()

        assert exc_info.value.code == "invalid_response"
        client.close()

    def test_malformed_transaction_raises_invalid_response(
        self, api_key, httpx_mock: HTTPXMock
    ):
        from sendly.errors import SendlyError

        client = Sendly(api_key)
        row = {
            "id": "t1",
            "amount": "ten",
            "balance_after": 10,
            "type": "purchase",
            "description": None,
            "created_at": "2026-01-01T00:00:00Z",
        }
        httpx_mock.add_response(url=TRANSACTIONS_URL, method="GET", json={"transactions": [row]})

        with pytest.raises(SendlyError) as exc_info:
            client.account.get_credit_transactions()

        assert exc_info.value.code == "invalid_response"
        client.close()


class TestCreateApiKeyExpiry:
    def test_sends_expires_at(self, api_key, httpx_mock: HTTPXMock):
        import json

        client = Sendly(api_key)
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/account/keys",
            method="POST",
            json={
                **CREATED_KEY_BODY,
                "key": "sk_test_v1_secret",
                "keyPrefix": "sk_test_v1_s",
                "type": "test",
                "expiresAt": "2027-01-01T00:00:00.000Z",
                "apiKey": {
                    **CREATED_KEY_BODY["apiKey"],
                    "type": "test",
                    "prefix": "sk_test_v1_s...",
                    "expiresAt": "2027-01-01T00:00:00.000Z",
                },
            },
        )

        result = client.account.create_api_key("Prod", "2027-01-01T00:00:00Z")

        assert json.loads(httpx_mock.get_request().content) == {
            "name": "Prod",
            "expiresAt": "2027-01-01T00:00:00Z",
        }
        assert result["expiresAt"] == "2027-01-01T00:00:00.000Z"
        client.close()
