import json

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.types import LabelListResponse

BASE = "https://sendly.live/api/v1"

LABEL_ROWS = {
    "data": [
        {
            "id": "lbl_1",
            "userId": "user_1",
            "organizationId": "org_1",
            "name": "VIP",
            "color": "#6b7280",
            "description": None,
            "createdAt": "2026-01-01T00:00:00Z",
        }
    ]
}


class TestAddLabels:
    def test_returns_the_conversation_labels(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/conversations/conv_1/labels", method="POST", json=LABEL_ROWS
        )

        result = client.conversations.add_labels("conv_1", ["lbl_1"])

        assert isinstance(result, LabelListResponse)
        assert result.data[0].id == "lbl_1"
        assert result.data[0].name == "VIP"
        assert json.loads(httpx_mock.get_request().content) == {"labelIds": ["lbl_1"]}
        client.close()

    @pytest.mark.asyncio
    async def test_returns_the_conversation_labels_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/conversations/conv_1/labels", method="POST", json=LABEL_ROWS
        )

        result = await client.conversations.add_labels("conv_1", ["lbl_1"])

        assert result.data[0].id == "lbl_1"
        await client.close()


class TestRemoveLabel:
    def test_no_content_returns_none(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/conversations/conv_1/labels/lbl_1", method="DELETE", status_code=204
        )

        assert client.conversations.remove_label("conv_1", "lbl_1") is None
        client.close()

    @pytest.mark.asyncio
    async def test_no_content_returns_none_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/conversations/conv_1/labels/lbl_1", method="DELETE", status_code=204
        )

        assert await client.conversations.remove_label("conv_1", "lbl_1") is None
        await client.close()
