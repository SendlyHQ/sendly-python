import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.types import Contact, UpdatedContact

BASE = "https://sendly.live/api/v1"

PATCHED = {
    "id": "c1",
    "phone_number": "+15551234567",
    "name": "x",
    "email": None,
    "metadata": {},
    "line_type": None,
    "carrier_name": None,
    "line_type_checked_at": None,
    "invalid_reason": None,
    "invalidated_at": None,
    "user_marked_valid_at": None,
    "updated_at": "2026-01-02T00:00:00.000Z",
}


FETCHED = {
    "id": "c1",
    "phone_number": "+15551234567",
    "name": "x",
    "email": None,
    "metadata": {},
    "opted_out": True,
    "line_type": None,
    "carrier_name": None,
    "line_type_checked_at": None,
    "invalid_reason": None,
    "invalidated_at": None,
    "user_marked_valid_at": None,
    "created_at": "2026-01-01T00:00:00.000Z",
    "updated_at": "2026-01-02T00:00:00.000Z",
    "lists": [{"id": "lst_1", "name": "Newsletter"}],
}

MARKED_VALID = {
    "id": "c1",
    "userId": "u1",
    "organizationId": "org_1",
    "phoneNumber": "+15551234567",
    "name": "x",
    "email": None,
    "metadata": {},
    "optedOut": False,
    "optedOutAt": None,
    "optedOutKeyword": None,
    "optedInAt": None,
    "optedInMethod": None,
    "optedInSource": None,
    "lineType": "mobile",
    "carrierName": None,
    "lineTypeCheckedAt": None,
    "invalidReason": None,
    "invalidatedAt": None,
    "userMarkedValidAt": "2026-01-03T00:00:00.000Z",
    "createdAt": "2026-01-01T00:00:00.000Z",
    "updatedAt": "2026-01-03T00:00:00.000Z",
}


class TestContactUpdate:
    def test_reads_the_patch_response(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/contacts/c1", method="PATCH", json=PATCHED)

        contact = client.contacts.update("c1", name="x")

        assert isinstance(contact, UpdatedContact)
        assert contact.name == "x"
        assert contact.phone_number == "+15551234567"
        assert contact.updated_at == "2026-01-02T00:00:00.000Z"
        client.close()

    def test_does_not_claim_an_opt_out_status_the_response_lacks(
        self, api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/contacts/c1", method="PATCH", json=PATCHED)

        contact = client.contacts.update("c1", name="x")

        assert not hasattr(contact, "opted_out")
        assert not hasattr(contact, "created_at")
        assert not hasattr(contact, "lists")
        client.close()

    @pytest.mark.asyncio
    async def test_reads_the_patch_response_async(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/contacts/c1", method="PATCH", json=PATCHED)

        contact = await client.contacts.update("c1", name="x")

        assert contact.name == "x"
        assert not hasattr(contact, "opted_out")
        await client.close()


class TestContactGet:
    def test_reads_opt_out_status_and_creation_time(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(url=f"{BASE}/contacts/c1", method="GET", json=FETCHED)

        contact = client.contacts.get("c1")

        assert contact.opted_out is True
        assert contact.created_at == "2026-01-01T00:00:00.000Z"
        assert contact.lists == [{"id": "lst_1", "name": "Newsletter"}]
        client.close()

    def test_mark_valid_reads_the_stored_row(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/contacts/c1/mark-valid", method="POST", json=MARKED_VALID
        )

        contact = client.contacts.mark_valid("c1")

        assert contact.phone_number == "+15551234567"
        assert contact.opted_out is False
        assert contact.created_at == "2026-01-01T00:00:00.000Z"
        assert contact.user_marked_valid_at == "2026-01-03T00:00:00.000Z"
        client.close()

    def test_created_at_keeps_its_4_2_type(self):
        field = Contact.model_fields["created_at"]

        assert field.annotation is str
        assert field.is_required()
