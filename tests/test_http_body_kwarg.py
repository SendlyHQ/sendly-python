"""
HTTP smoke tests for the body= kwarg fix (3.33.0).

Regression guard: the contacts, campaigns, templates, and webhooks resources
previously called ``self._http.request(..., json=body)``, but the HTTP client's
``request()`` only accepts ``body=``. That raised ``TypeError`` at runtime on
every write method. These tests drive one write method per fixed resource
through the real ``request()`` path (transport mocked with pytest_httpx) and
assert no ``TypeError`` is raised and the payload actually reaches the wire.
"""

import json

from pytest_httpx import HTTPXMock

from sendly import Sendly
from sendly.types import ImportContactItem

BASE = "https://sendly.live/api/v1"


def _now() -> str:
    return "2026-06-01T10:00:00Z"


class TestContactsBodyKwarg:
    def test_import_contacts_sends_body(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/contacts/import",
            method="POST",
            json={"imported": 1, "skippedDuplicates": 0, "errors": [], "totalErrors": 0},
        )

        # Must not raise TypeError (the pre-3.33.0 bug).
        result = client.contacts.import_contacts(
            [ImportContactItem(phone="+15551234567", name="Ada")],
            list_id="list_1",
        )

        assert result.imported == 1
        sent = json.loads(httpx_mock.get_request().read().decode())
        assert sent["listId"] == "list_1"
        assert sent["contacts"][0]["phone"] == "+15551234567"
        client.close()

    def test_lookup_sends_body(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/contacts/lookup",
            method="POST",
            json={"alreadyRunning": False},
        )

        result = client.contacts.check_numbers(list_id="list_1", force=True)

        assert result == {"alreadyRunning": False}
        sent = json.loads(httpx_mock.get_request().read().decode())
        assert sent == {"listId": "list_1", "force": True}
        client.close()

    def test_bulk_mark_valid_sends_body(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/contacts/bulk-mark-valid",
            method="POST",
            json={"cleared": 3},
        )

        result = client.contacts.bulk_mark_valid(ids=["c1", "c2", "c3"])

        assert result.cleared == 3
        sent = json.loads(httpx_mock.get_request().read().decode())
        assert sent == {"ids": ["c1", "c2", "c3"]}
        client.close()


class TestCampaignsBodyKwarg:
    def test_create_sends_body(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/campaigns",
            method="POST",
            json={
                "id": "cmp_1",
                "name": "Promo",
                "text": "Hi {{name}}",
                "status": "draft",
                "created_at": _now(),
                "updated_at": _now(),
            },
        )

        campaign = client.campaigns.create(
            name="Promo",
            text="Hi {{name}}",
            contact_list_ids=["list_1"],
        )

        assert campaign.id == "cmp_1"
        sent = json.loads(httpx_mock.get_request().read().decode())
        assert sent["name"] == "Promo"
        assert sent["contactListIds"] == ["list_1"]
        client.close()


class TestTemplatesBodyKwarg:
    def test_create_sends_body(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/templates",
            method="POST",
            json={
                "id": "tpl_1",
                "name": "Welcome",
                "text": "Hi {{name}}",
                "variables": [{"name": "name", "required": True}],
                "is_preset": False,
                "status": "draft",
                "version": 1,
                "created_at": _now(),
                "updated_at": _now(),
            },
        )

        template = client.templates.create(name="Welcome", text="Hi {{name}}")

        assert template.id == "tpl_1"
        sent = json.loads(httpx_mock.get_request().read().decode())
        assert sent == {"name": "Welcome", "text": "Hi {{name}}"}
        client.close()


class TestWebhooksBodyKwarg:
    def test_create_sends_body(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/webhooks",
            method="POST",
            json={
                "id": "whk_1",
                "url": "https://example.com/hook",
                "events": ["message.delivered"],
                "isActive": True,
                "createdAt": _now(),
                "updatedAt": _now(),
                "secret": "whsec_test",
            },
        )

        webhook = client.webhooks.create(
            url="https://example.com/hook",
            events=["message.delivered"],
        )

        assert webhook.secret == "whsec_test"
        sent = json.loads(httpx_mock.get_request().read().decode())
        assert sent["url"] == "https://example.com/hook"
        assert sent["events"] == ["message.delivered"]
        client.close()
