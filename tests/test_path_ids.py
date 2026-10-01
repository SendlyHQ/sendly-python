import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import ValidationError

BASE = "https://sendly.live/api/v1"


class TestDotSegmentIds:
    @pytest.mark.parametrize("key_id", ["..", ".", ""])
    def test_refuses_a_key_id_that_would_delete_the_workspace(
        self, api_key, httpx_mock: HTTPXMock, key_id
    ):
        client = Sendly(api_key, max_retries=0)

        with pytest.raises(ValidationError):
            client.enterprise.workspaces.revoke_key("ws_1", key_id)

        assert httpx_mock.get_requests() == []
        client.close()

    def test_refuses_a_contact_id_that_would_delete_the_list(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=0)

        with pytest.raises(ValidationError):
            client.contacts.lists.remove_contact("lst_1", "..")

        assert httpx_mock.get_requests() == []
        client.close()

    def test_refuses_a_workspace_id_on_a_multipart_upload(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=0)

        with pytest.raises(ValidationError):
            client.business_upgrade.start("..", business_name="Acme")

        assert httpx_mock.get_requests() == []
        client.close()

    @pytest.mark.asyncio
    async def test_refuses_a_dot_segment_id_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key, max_retries=0)

        with pytest.raises(ValidationError):
            await client.enterprise.workspaces.revoke_key("ws_1", "..")
        with pytest.raises(ValidationError):
            await client.business_upgrade.start("..", business_name="Acme")

        assert httpx_mock.get_requests() == []
        await client.close()

    def test_still_sends_ordinary_ids_and_ids_that_contain_dots(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=0)
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces/ws_1/keys/key_1",
            method="DELETE",
            status_code=204,
        )
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces/ws_1/keys/...",
            method="DELETE",
            status_code=204,
        )
        httpx_mock.add_response(
            url=f"{BASE}/enterprise/workspaces/ws.1/keys/key.v2",
            method="DELETE",
            status_code=204,
        )

        client.enterprise.workspaces.revoke_key("ws_1", "key_1")
        client.enterprise.workspaces.revoke_key("ws_1", "...")
        client.enterprise.workspaces.revoke_key("ws.1", "key.v2")

        assert len(httpx_mock.get_requests()) == 3
        client.close()
