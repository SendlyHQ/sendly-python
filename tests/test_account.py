"""
Tests for Account resource API-key management

These pin the paths the server actually serves: listing, fetching and usage
live under /account/keys, and revocation is a PATCH to
/account/keys/{id}/revoke.
"""

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.types import ApiKey


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
