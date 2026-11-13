import json

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.types import LabelListResponse, SuggestRepliesResponse

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


SUGGESTIONS = {
    "suggestions": [
        {"text": "Yes, we open at 9am.", "tone": "professional"},
        {"text": "We sure are! See you at 9.", "tone": "friendly"},
    ],
    "basedOnMessageId": "msg_in_1",
    "model": "gpt-4o-mini",
}


class TestSuggestReplies:
    def test_posts_and_returns_the_suggestions(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/conversations/conv_1/suggest-replies", method="POST", json=SUGGESTIONS
        )

        result = client.conversations.suggest_replies("conv_1")

        assert isinstance(result, SuggestRepliesResponse)
        assert [s.text for s in result.suggestions] == [
            "Yes, we open at 9am.",
            "We sure are! See you at 9.",
        ]
        assert result.suggestions[1].tone == "friendly"
        assert result.based_on_message_id == "msg_in_1"
        assert result.model == "gpt-4o-mini"
        assert result.disabled is None
        request = httpx_mock.get_request()
        assert request.method == "POST"
        assert request.url.path == "/api/v1/conversations/conv_1/suggest-replies"
        client.close()

    def test_encodes_the_id(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/conversations/conv%2Fweird/suggest-replies",
            method="POST",
            json={"suggestions": []},
        )

        result = client.conversations.suggest_replies("conv/weird")

        assert result.suggestions == []
        assert result.based_on_message_id is None
        client.close()

    def test_enterprise_policy_turned_off(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/conversations/conv_1/suggest-replies",
            method="POST",
            json={"suggestions": [], "disabled": True, "reason": "enterprise_policy"},
        )

        result = client.conversations.suggest_replies("conv_1")

        assert result.suggestions == []
        assert result.disabled is True
        assert result.reason == "enterprise_policy"
        client.close()

    @pytest.mark.asyncio
    async def test_posts_and_returns_the_suggestions_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/conversations/conv_1/suggest-replies", method="POST", json=SUGGESTIONS
        )

        result = await client.conversations.suggest_replies("conv_1")

        assert isinstance(result, SuggestRepliesResponse)
        assert result.suggestions[0].tone == "professional"
        assert result.based_on_message_id == "msg_in_1"
        await client.close()


class TestListByLabel:
    EMPTY = {"data": [], "pagination": {"total": 0, "limit": 20, "offset": 0, "hasMore": False}}

    def test_sends_the_label_filter(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/conversations?status=active&label=lbl_1", method="GET", json=self.EMPTY
        )

        client.conversations.list(status="active", label="lbl_1")

        assert httpx_mock.get_request().url.params["label"] == "lbl_1"
        client.close()

    def test_omits_the_label_when_unset(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/conversations", method="GET", json=self.EMPTY)

        client.conversations.list()

        assert "label" not in httpx_mock.get_request().url.params
        client.close()

    async def test_sends_the_label_filter_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/conversations?label=lbl_1", method="GET", json=self.EMPTY
        )

        await client.conversations.list(label="lbl_1")

        assert httpx_mock.get_request().url.params["label"] == "lbl_1"
        await client.close()
