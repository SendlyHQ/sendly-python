"""
Tests for the WhatsApp extras: profile photo, conversational components,
calling, adding a number by code, the call channel and unconfirmed sends.
Fixtures mirror what the API handlers return.
"""

import io
import json
import re

import httpx
import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import NetworkError, NotFoundError, SendlyError, ValidationError
from sendly.errors import TimeoutError as SendlyTimeoutError
from sendly.types import (
    Call,
    CallChannel,
    WhatsAppCallingSettings,
    WhatsAppConversationalComponents,
    WhatsAppSenderListResponse,
    WhatsAppSenderProfile,
    WhatsAppSignup,
    WhatsAppSignupSession,
)

BASE = "https://sendly.live/api/v1"
PHONE = "+14155550123"
ENCODED = "%2B14155550123"
SIGNUP_ID = "5b0d8f3e-2c4a-4e1b-9a7d-6c5b4a3f2e1d"

PROFILE = {
    "phoneNumber": PHONE,
    "displayName": "Acme Coffee",
    "profilePhotoUrl": "https://media.example.com/acme.png",
    "category": "Restaurant",
    "about": "Fresh roasts daily",
    "description": None,
    "email": None,
    "website": "https://acme.example.com",
    "address": None,
}

COMPONENTS = {
    "phoneNumber": PHONE,
    "iceBreakers": ["What are your hours?", "Book a table"],
    "commands": [{"command": "menu", "description": "See today's menu"}],
}

VERIFYING = {
    "id": SIGNUP_ID,
    "status": "verifying",
    "phoneNumber": PHONE,
    "businessAccountId": "102938475610293",
    "failureReasons": None,
    "verificationMethod": "sms",
    "verificationAttemptsRemaining": 5,
    "updatedAt": "2026-09-30T10:00:00.000Z",
}

ACTIVE = {
    "id": SIGNUP_ID,
    "status": "active",
    "phoneNumber": PHONE,
    "businessAccountId": "102938475610293",
    "failureReasons": None,
    "updatedAt": "2026-09-30T10:02:00.000Z",
}

CALL = {
    "id": "6f1c2d3e-4a5b-4c6d-8e9f-0a1b2c3d4e5f",
    "object": "call",
    "kind": "pstn",
    "channel": "whatsapp",
    "direction": "inbound",
    "status": "completed",
    "handledBy": "dashboard",
    "agentId": None,
    "from": "+14155550188",
    "to": PHONE,
    "callerName": None,
    "calleeName": None,
    "startedAt": "2026-09-30T14:03:11.000Z",
    "answeredAt": "2026-09-30T14:03:15.000Z",
    "endedAt": "2026-09-30T14:05:00.000Z",
    "durationSecs": 105,
    "creditsCharged": 4,
    "billing": "settled",
    "hangupClass": "normal",
    "recordingStatus": None,
    "metadata": {},
}

PNG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 1, 2])


def _body(request):
    return json.loads(request.read().decode())


class TestProfilePhoto:
    def test_upload_sends_multipart_file_and_returns_profile(
        self, live_api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/profile/photo",
            method="POST",
            json=PROFILE,
        )

        profile = client.whatsapp.senders.upload_profile_photo(
            PHONE, io.BytesIO(PNG), content_type="image/png"
        )

        assert isinstance(profile, WhatsAppSenderProfile)
        assert profile.profile_photo_url == "https://media.example.com/acme.png"
        request = httpx_mock.get_request()
        assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
        assert b'name="file"' in request.content
        assert b"Content-Type: image/png" in request.content
        assert PNG in request.content
        client.close()

    def test_upload_accepts_bytes_and_defaults_to_jpeg(
        self, live_api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/profile/photo",
            method="POST",
            json=PROFILE,
        )

        client.whatsapp.senders.upload_profile_photo(PHONE, b"\xff\xd8\xff\xe0")

        request = httpx_mock.get_request()
        assert b"Content-Type: image/jpeg" in request.content
        assert b"\xff\xd8\xff\xe0" in request.content
        client.close()

    def test_upload_accepts_a_bytearray(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/profile/photo",
            method="POST",
            json=PROFILE,
        )

        client.whatsapp.senders.upload_profile_photo(
            PHONE, bytearray(PNG), content_type="image/png"
        )

        assert PNG in httpx_mock.get_request().content
        client.close()

    def test_upload_gives_the_file_part_a_filename(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/profile/photo",
            method="POST",
            json=PROFILE,
        )

        client.whatsapp.senders.upload_profile_photo(PHONE, PNG, content_type="image/png")

        assert re.search(
            rb'Content-Disposition: form-data; name="file"; filename="[^"]+"\r\n',
            httpx_mock.get_request().content,
        )
        client.close()

    def test_upload_too_large_raises_once(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/profile/photo",
            method="POST",
            status_code=413,
            json={
                "error": "whatsapp_profile_photo_too_large",
                "message": "The photo must be 5 MB or smaller.",
            },
        )

        with pytest.raises(SendlyError) as exc_info:
            client.whatsapp.senders.upload_profile_photo(PHONE, io.BytesIO(PNG))

        assert exc_info.value.code == "whatsapp_profile_photo_too_large"
        assert exc_info.value.status_code == 413
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_upload_rejects_invalid_phone(self, live_api_key):
        client = Sendly(live_api_key)
        with pytest.raises(ValidationError):
            client.whatsapp.senders.upload_profile_photo("not-a-number", io.BytesIO(PNG))
        client.close()

    def test_delete_returns_profile_without_photo(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/profile/photo",
            method="DELETE",
            json={**PROFILE, "profilePhotoUrl": None},
        )

        profile = client.whatsapp.senders.delete_profile_photo(PHONE)

        assert profile.profile_photo_url is None
        client.close()

    @pytest.mark.asyncio
    async def test_async_upload_and_delete(self, live_api_key, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/profile/photo",
            method="POST",
            json=PROFILE,
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/profile/photo",
            method="DELETE",
            json={**PROFILE, "profilePhotoUrl": None},
        )
        async with AsyncSendly(live_api_key) as client:
            uploaded = await client.whatsapp.senders.upload_profile_photo(
                PHONE, PNG, content_type="image/png"
            )
            removed = await client.whatsapp.senders.delete_profile_photo(PHONE)

        assert uploaded.display_name == "Acme Coffee"
        assert removed.profile_photo_url is None


class TestConversationalComponents:
    def test_get(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/conversational_components",
            method="GET",
            json=COMPONENTS,
        )

        result = client.whatsapp.senders.get_conversational_components(PHONE)

        assert isinstance(result, WhatsAppConversationalComponents)
        assert result.phone_number == PHONE
        assert result.ice_breakers == ["What are your hours?", "Book a table"]
        assert result.commands[0].command == "menu"
        assert result.commands[0].description == "See today's menu"
        client.close()

    def test_lists_left_out_of_the_body_read_as_empty(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/conversational_components",
            method="GET",
            json={"phoneNumber": PHONE},
        )

        result = client.whatsapp.senders.get_conversational_components(PHONE)

        assert result.ice_breakers == []
        assert result.commands == []
        client.close()

    def test_update_sends_only_the_lists_given(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/conversational_components",
            method="PATCH",
            json={**COMPONENTS, "commands": []},
        )

        result = client.whatsapp.senders.update_conversational_components(PHONE, commands=[])

        assert result.commands == []
        assert _body(httpx_mock.get_request()) == {"commands": []}
        client.close()

    def test_update_sends_both_lists(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/conversational_components",
            method="PATCH",
            json=COMPONENTS,
        )

        client.whatsapp.senders.update_conversational_components(
            PHONE,
            ice_breakers=COMPONENTS["iceBreakers"],
            commands=COMPONENTS["commands"],
        )

        assert _body(httpx_mock.get_request()) == {
            "iceBreakers": COMPONENTS["iceBreakers"],
            "commands": COMPONENTS["commands"],
        }
        client.close()

    def test_update_takes_the_commands_get_returned(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/conversational_components",
            method="PATCH",
            json=COMPONENTS,
        )
        current = WhatsAppConversationalComponents(**COMPONENTS)

        client.whatsapp.senders.update_conversational_components(
            PHONE,
            commands=[*current.commands, {"command": "quote", "description": "Get a price"}],
        )

        assert _body(httpx_mock.get_request()) == {
            "commands": [
                {"command": "menu", "description": "See today's menu"},
                {"command": "quote", "description": "Get a price"},
            ]
        }
        client.close()

    def test_update_needs_a_list(self, live_api_key):
        client = Sendly(live_api_key)
        with pytest.raises(ValidationError):
            client.whatsapp.senders.update_conversational_components(PHONE)
        client.close()

    @pytest.mark.asyncio
    async def test_async_get_and_update(self, live_api_key, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/conversational_components",
            method="GET",
            json=COMPONENTS,
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/conversational_components",
            method="PATCH",
            json={**COMPONENTS, "iceBreakers": []},
        )
        async with AsyncSendly(live_api_key) as client:
            current = await client.whatsapp.senders.get_conversational_components(PHONE)
            updated = await client.whatsapp.senders.update_conversational_components(
                PHONE, ice_breakers=[]
            )

        assert len(current.ice_breakers) == 2
        assert updated.ice_breakers == []
        assert _body(httpx_mock.get_requests()[1]) == {"iceBreakers": []}


class TestCalling:
    def test_set_calling(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/calling",
            method="PATCH",
            json={"phoneNumber": PHONE, "callingEnabled": True, "outboundCallingAllowed": False},
        )

        result = client.whatsapp.senders.set_calling(PHONE, enabled=True)

        assert isinstance(result, WhatsAppCallingSettings)
        assert result.calling_enabled is True
        assert result.outbound_calling_allowed is False
        assert _body(httpx_mock.get_request()) == {"enabled": True}
        client.close()

    def test_voice_not_enabled_raises_once(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/calling",
            method="PATCH",
            status_code=409,
            json={
                "error": "voice_not_enabled",
                "message": (
                    "Turn on calls for this number first, in its voice settings, so WhatsApp "
                    "calls have somewhere to ring."
                ),
            },
        )

        with pytest.raises(SendlyError) as exc_info:
            client.whatsapp.senders.set_calling(PHONE, enabled=True)

        assert exc_info.value.code == "voice_not_enabled"
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    @pytest.mark.asyncio
    async def test_async_set_calling_off(self, live_api_key, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/calling",
            method="PATCH",
            json={"phoneNumber": PHONE, "callingEnabled": False, "outboundCallingAllowed": False},
        )
        async with AsyncSendly(live_api_key) as client:
            result = await client.whatsapp.senders.set_calling(PHONE, enabled=False)

        assert result.calling_enabled is False
        assert _body(httpx_mock.get_request()) == {"enabled": False}


class TestSenderFields:
    def test_list_carries_account_name_and_calling(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders",
            method="GET",
            json={
                "senders": [
                    {
                        "phoneNumber": PHONE,
                        "displayName": "Acme Coffee",
                        "status": "active",
                        "qualityRating": "GREEN",
                        "businessAccountId": "102938475610293",
                        "businessName": "Acme Coffee LLC",
                        "callingEnabled": True,
                        "outboundCallingAllowed": False,
                        "createdAt": "2026-09-30T09:12:00.000Z",
                    },
                    {
                        "phoneNumber": "+14155550124",
                        "displayName": None,
                        "status": "pending",
                        "qualityRating": None,
                        "businessAccountId": None,
                        "businessName": None,
                        "callingEnabled": False,
                        "outboundCallingAllowed": False,
                        "createdAt": "2026-09-30T09:15:00.000Z",
                    },
                ]
            },
        )

        result = client.whatsapp.senders.list()

        assert isinstance(result, WhatsAppSenderListResponse)
        active, pending = result.senders
        assert active.business_account_id == "102938475610293"
        assert active.business_name == "Acme Coffee LLC"
        assert active.calling_enabled is True
        assert active.outbound_calling_allowed is False
        assert pending.business_account_id is None
        assert pending.business_name is None
        client.close()


class TestAddNumberByCode:
    def test_create_with_business_account_id(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup",
            method="POST",
            status_code=201,
            json={**VERIFYING, "verificationMethod": "voice"},
        )

        signup = client.whatsapp.signup.create(
            PHONE,
            business_account_id="102938475610293",
            verification_method="voice",
            display_name="Acme Coffee",
        )

        assert isinstance(signup, WhatsAppSignup)
        assert signup.status == "verifying"
        assert signup.verification_method == "voice"
        assert signup.verification_attempts_remaining == 5
        assert _body(httpx_mock.get_request()) == {
            "phoneNumber": PHONE,
            "businessAccountId": "102938475610293",
            "verificationMethod": "voice",
            "displayName": "Acme Coffee",
        }
        client.close()

    def test_create_omits_optional_fields(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup", method="POST", status_code=201, json=VERIFYING
        )

        client.whatsapp.signup.create(PHONE, business_account_id="102938475610293")

        assert _body(httpx_mock.get_request()) == {
            "phoneNumber": PHONE,
            "businessAccountId": "102938475610293",
        }
        client.close()

    def test_create_without_business_account_id_is_unchanged(
        self, live_api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup",
            method="POST",
            status_code=201,
            json={
                "id": "was_1",
                "connectUrl": "https://sendly.live/whatsapp/connect?token=abc",
                "status": "initiated",
            },
        )

        session = client.whatsapp.signup.create(PHONE)

        assert isinstance(session, WhatsAppSignupSession)
        assert _body(httpx_mock.get_request()) == {"phoneNumber": PHONE}
        client.close()

    def test_empty_business_account_id_is_refused_locally(self, live_api_key):
        client = Sendly(live_api_key)
        with pytest.raises(ValidationError):
            client.whatsapp.signup.create(PHONE, business_account_id="")
        client.close()

    @pytest.mark.parametrize("business_account_id", ["   ", 104996582519384])
    def test_blank_or_non_string_business_account_id_is_refused_locally(
        self, live_api_key, httpx_mock: HTTPXMock, business_account_id
    ):
        client = Sendly(live_api_key)
        with pytest.raises(
            ValidationError, match="business_account_id must be a non-empty string"
        ):
            client.whatsapp.signup.create(PHONE, business_account_id=business_account_id)
        client.close()

    def test_method_without_business_account_id_is_refused_locally(self, live_api_key):
        client = Sendly(live_api_key)
        with pytest.raises(ValidationError):
            client.whatsapp.signup.create(PHONE, verification_method="voice")  # type: ignore[call-overload]
        client.close()

    def test_account_not_found(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup",
            method="POST",
            status_code=404,
            json={
                "error": "whatsapp_business_account_not_found",
                "message": (
                    "There's no connected WhatsApp Business account with this id in your "
                    "workspace. Connect a number with the Facebook step first."
                ),
            },
        )

        with pytest.raises(SendlyError) as exc_info:
            client.whatsapp.signup.create(PHONE, business_account_id="999")

        assert exc_info.value.code == "whatsapp_business_account_not_found"
        client.close()

    def test_facebook_create_while_verifying_carries_the_signup_id(
        self, live_api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup",
            method="POST",
            status_code=409,
            json={
                "error": "whatsapp_verification_in_progress",
                "message": (
                    "This number is already being added to a connected WhatsApp Business account."
                    " Enter its verification code, or wait for that attempt to expire."
                ),
                "id": SIGNUP_ID,
            },
        )

        with pytest.raises(SendlyError) as exc_info:
            client.whatsapp.signup.create(PHONE)

        assert exc_info.value.code == "whatsapp_verification_in_progress"
        assert exc_info.value.response is not None
        assert exc_info.value.response.model_extra is not None
        assert exc_info.value.response.model_extra["id"] == SIGNUP_ID
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_verify(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/verify", method="POST", json=ACTIVE
        )

        signup = client.whatsapp.signup.verify(SIGNUP_ID, "123-456")

        assert signup.status == "active"
        assert signup.verification_method is None
        assert _body(httpx_mock.get_request()) == {"code": "123-456"}
        client.close()

    def test_verify_wrong_code_carries_attempts_remaining(
        self, live_api_key, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/verify",
            method="POST",
            status_code=422,
            json={
                "error": "whatsapp_verification_code_invalid",
                "message": "That code wasn't accepted. Check it, or request a new one.",
                "attemptsRemaining": 3,
            },
        )

        with pytest.raises(SendlyError) as exc_info:
            client.whatsapp.signup.verify(SIGNUP_ID, "000000")

        assert exc_info.value.code == "whatsapp_verification_code_invalid"
        assert exc_info.value.response is not None
        assert exc_info.value.response.attempts_remaining == 3
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_verify_requires_id(self, live_api_key):
        client = Sendly(live_api_key)
        with pytest.raises(ValidationError):
            client.whatsapp.signup.verify("", "123456")
        client.close()

    @pytest.mark.parametrize("method,args", [("verify", ("", "123456")), ("resend", ("",))])
    def test_empty_signup_id_is_refused_by_name(
        self, live_api_key, httpx_mock: HTTPXMock, method, args
    ):
        client = Sendly(live_api_key)
        with pytest.raises(ValidationError, match="A signup 'id' is required"):
            getattr(client.whatsapp.signup, method)(*args)
        client.close()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method,args", [("verify", ("", "123456")), ("resend", ("",))])
    async def test_async_empty_signup_id_is_refused_by_name(
        self, live_api_key, httpx_mock: HTTPXMock, method, args
    ):
        async with AsyncSendly(live_api_key) as client:
            with pytest.raises(ValidationError, match="A signup 'id' is required"):
                await getattr(client.whatsapp.signup, method)(*args)

    def test_signup_id_is_url_encoded(self, live_api_key, no_sleep, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/a%2Fb/verify", method="POST", json=ACTIVE
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/a%2Fb/resend", method="POST", json=VERIFYING
        )

        client.whatsapp.signup.verify("a/b", "482913")
        client.whatsapp.signup.resend("a/b")

        assert [r.url.raw_path for r in httpx_mock.get_requests()] == [
            b"/api/v1/whatsapp/signup/a%2Fb/verify",
            b"/api/v1/whatsapp/signup/a%2Fb/resend",
        ]
        client.close()

    @pytest.mark.asyncio
    async def test_async_signup_id_is_url_encoded(
        self, live_api_key, no_async_sleep, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/a%2Fb/verify", method="POST", json=ACTIVE
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/a%2Fb/resend", method="POST", json=VERIFYING
        )
        async with AsyncSendly(live_api_key) as client:
            await client.whatsapp.signup.verify("a/b", "482913")
            await client.whatsapp.signup.resend("a/b")

        assert [r.url.raw_path for r in httpx_mock.get_requests()] == [
            b"/api/v1/whatsapp/signup/a%2Fb/verify",
            b"/api/v1/whatsapp/signup/a%2Fb/resend",
        ]

    def test_resend_with_method(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/resend",
            method="POST",
            json={**VERIFYING, "verificationMethod": "voice"},
        )

        signup = client.whatsapp.signup.resend(SIGNUP_ID, verification_method="voice")

        assert signup.verification_method == "voice"
        assert _body(httpx_mock.get_request()) == {"verificationMethod": "voice"}
        client.close()

    def test_resend_without_method_sends_empty_body(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/resend", method="POST", json=VERIFYING
        )

        client.whatsapp.signup.resend(SIGNUP_ID)

        assert _body(httpx_mock.get_request()) == {}
        client.close()

    def test_resend_too_soon_is_not_retried(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/resend",
            method="POST",
            status_code=429,
            headers={"Retry-After": "12"},
            json={
                "error": "whatsapp_verification_resend_too_soon",
                "message": "Wait 12 seconds before requesting another code.",
                "retryAfter": 12,
            },
        )

        with pytest.raises(SendlyError) as exc_info:
            client.whatsapp.signup.resend(SIGNUP_ID)

        assert exc_info.value.code == "whatsapp_verification_resend_too_soon"
        assert exc_info.value.response is not None
        assert exc_info.value.response.retry_after == 12
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_get_while_verifying_returns_code(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}",
            method="GET",
            json={**VERIFYING, "verificationCode": "123456"},
        )

        signup = client.whatsapp.signup.get(SIGNUP_ID)

        assert signup.verification_code == "123456"
        assert signup.verification_attempts_remaining == 5
        client.close()

    @pytest.mark.asyncio
    async def test_async_create_verify_resend(self, live_api_key, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup", method="POST", status_code=201, json=VERIFYING
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/resend", method="POST", json=VERIFYING
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/verify", method="POST", json=ACTIVE
        )
        async with AsyncSendly(live_api_key) as client:
            created = await client.whatsapp.signup.create(
                PHONE, business_account_id="102938475610293"
            )
            await client.whatsapp.signup.resend(created.id, verification_method="sms")
            active = await client.whatsapp.signup.verify(created.id, "123456")

        assert isinstance(created, WhatsAppSignup)
        assert active.status == "active"
        requests = httpx_mock.get_requests()
        assert _body(requests[1]) == {"verificationMethod": "sms"}
        assert _body(requests[2]) == {"code": "123456"}


class TestSendUnconfirmed:
    def test_whatsapp_send_unconfirmed_is_raised_once(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/messages",
            method="POST",
            status_code=409,
            json={
                "error": "whatsapp_send_unconfirmed",
                "errorCode": "E024",
                "message": (
                    "We couldn't confirm whether WhatsApp accepted this message. It has been "
                    "marked failed and refunded, but it may still be delivered. Check before "
                    "sending it again, or it could arrive twice."
                ),
            },
        )

        with pytest.raises(SendlyError) as exc_info:
            client.messages.send(
                channel="whatsapp", to="+14155550199", from_=PHONE, text="Hi"
            )

        assert exc_info.value.code == "whatsapp_send_unconfirmed"
        assert exc_info.value.status_code == 409
        assert not isinstance(exc_info.value, (ValidationError, NotFoundError))
        assert len(httpx_mock.get_requests()) == 1
        client.close()


class TestCallChannel:
    def test_call_carries_channel(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(url=f"{BASE}/calls/{CALL['id']}", method="GET", json=CALL)

        call = client.calls.get(CALL["id"])

        assert isinstance(call, Call)
        assert call.channel == "whatsapp"
        assert call.channel == CallChannel.WHATSAPP
        client.close()

    def test_unknown_channel_is_kept(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/calls/{CALL['id']}", method="GET", json={**CALL, "channel": "satellite"}
        )

        call = client.calls.get(CALL["id"])

        assert call.channel == "satellite"
        client.close()

    def test_channel_is_optional(self, live_api_key, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        body = {k: v for k, v in CALL.items() if k != "channel"}
        httpx_mock.add_response(url=f"{BASE}/calls/{CALL['id']}", method="GET", json=body)

        call = client.calls.get(CALL["id"])

        assert call.channel is None
        client.close()

    def test_channel_values_match_the_api(self):
        assert [c.value for c in CallChannel] == ["phone", "whatsapp", "browser"]


SENDER_CALLS = {
    "upload_profile_photo": lambda senders, phone: senders.upload_profile_photo(phone, PNG),
    "delete_profile_photo": lambda senders, phone: senders.delete_profile_photo(phone),
    "get_conversational_components": lambda senders, phone: (
        senders.get_conversational_components(phone)
    ),
    "update_conversational_components": lambda senders, phone: (
        senders.update_conversational_components(phone, ice_breakers=[])
    ),
    "set_calling": lambda senders, phone: senders.set_calling(phone, enabled=True),
}


class TestSenderNumberIsCheckedLocally:
    @pytest.mark.parametrize("method", sorted(SENDER_CALLS))
    def test_sender_methods_refuse_a_number_without_country_code(
        self, live_api_key, no_sleep, httpx_mock: HTTPXMock, method
    ):
        client = Sendly(live_api_key)
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            SENDER_CALLS[method](client.whatsapp.senders, "4155550123")
        client.close()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", sorted(SENDER_CALLS))
    async def test_async_sender_methods_refuse_a_number_without_country_code(
        self, live_api_key, no_async_sleep, httpx_mock: HTTPXMock, method
    ):
        async with AsyncSendly(live_api_key) as client:
            with pytest.raises(ValidationError, match="Invalid phone number format"):
                await SENDER_CALLS[method](client.whatsapp.senders, "4155550123")


@pytest.fixture
def no_sleep(monkeypatch):
    calls = []
    monkeypatch.setattr("sendly.utils.http.time.sleep", lambda s: calls.append(s))
    return calls


@pytest.fixture
def no_async_sleep(monkeypatch):
    calls = []

    async def fake_sleep(s):
        calls.append(s)

    monkeypatch.setattr("sendly.utils.http.asyncio.sleep", fake_sleep)
    return calls


START_FAILED = {
    "error": "whatsapp_verification_start_failed",
    "message": (
        "WhatsApp couldn't start verifying this number. Any setup fee is refunded "
        "automatically. Please try again shortly."
    ),
}

ACTIVATION_PENDING = {
    "error": "whatsapp_activation_pending",
    "message": (
        "WhatsApp accepted the code, but we couldn't finish connecting the number. Our team "
        "has been alerted; check back shortly."
    ),
}

PHOTO_FAILED = {
    "error": "whatsapp_profile_update_failed",
    "message": (
        "The photo couldn't be uploaded. WhatsApp needs a square JPEG or PNG at least 192 "
        "pixels wide. Please try again shortly."
    ),
}


class TestServerErrorsOnCallsThatMustNotRepeat:
    def test_add_by_code_start_failed_is_sent_once(
        self, live_api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup",
            method="POST",
            status_code=502,
            json=START_FAILED,
            is_reusable=True,
        )

        with pytest.raises(SendlyError) as exc_info:
            client.whatsapp.signup.create(PHONE, business_account_id="104996582519384")

        assert exc_info.value.code == "whatsapp_verification_start_failed"
        assert exc_info.value.status_code == 502
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_add_by_code_500_is_sent_once(self, live_api_key, no_sleep, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup",
            method="POST",
            status_code=500,
            json={
                "error": "internal_error",
                "message": (
                    "Something went wrong asking WhatsApp for the code. Any setup fee is "
                    "refunded automatically. Please try again."
                ),
            },
            is_reusable=True,
        )

        with pytest.raises(SendlyError):
            client.whatsapp.signup.create(PHONE, business_account_id="104996582519384")

        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_verify_activation_pending_is_sent_once(
        self, live_api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/verify",
            method="POST",
            status_code=502,
            json=ACTIVATION_PENDING,
            is_reusable=True,
        )

        with pytest.raises(SendlyError) as exc_info:
            client.whatsapp.signup.verify(SIGNUP_ID, "482913")

        assert exc_info.value.code == "whatsapp_activation_pending"
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_photo_upload_failure_is_sent_once(
        self, live_api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/profile/photo",
            method="POST",
            status_code=502,
            json=PHOTO_FAILED,
            is_reusable=True,
        )

        with pytest.raises(SendlyError) as exc_info:
            client.whatsapp.senders.upload_profile_photo(PHONE, PNG, content_type="image/png")

        assert exc_info.value.code == "whatsapp_profile_update_failed"
        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_resend_keeps_the_normal_retry(self, live_api_key, no_sleep, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/resend",
            method="POST",
            status_code=502,
            json={
                "error": "whatsapp_verification_resend_failed",
                "message": (
                    "WhatsApp couldn't send another code right now. Please try again shortly."
                ),
            },
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/resend", method="POST", json=VERIFYING
        )

        signup = client.whatsapp.signup.resend(SIGNUP_ID)

        assert signup.status == "verifying"
        assert len(httpx_mock.get_requests()) == 2
        client.close()

    def test_facebook_signup_keeps_the_normal_retry(
        self, live_api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup",
            method="POST",
            status_code=503,
            headers={"Retry-After": "3600"},
            json={
                "error": "whatsapp_unavailable",
                "message": (
                    "WhatsApp connections are temporarily unavailable. You haven't been "
                    "charged. Please try again later."
                ),
                "retryAfter": 3600,
            },
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup",
            method="POST",
            status_code=201,
            json={
                "id": "was_1",
                "connectUrl": "https://sendly.live/whatsapp/connect?token=abc",
                "status": "initiated",
            },
        )

        session = client.whatsapp.signup.create(PHONE)

        assert session.status == "initiated"
        assert len(httpx_mock.get_requests()) == 2
        client.close()

    @pytest.mark.asyncio
    async def test_async_add_by_code_and_verify_are_sent_once(
        self, live_api_key, no_async_sleep, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup",
            method="POST",
            status_code=502,
            json=START_FAILED,
            is_reusable=True,
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/verify",
            method="POST",
            status_code=502,
            json=ACTIVATION_PENDING,
            is_reusable=True,
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/senders/{ENCODED}/profile/photo",
            method="POST",
            status_code=502,
            json=PHOTO_FAILED,
            is_reusable=True,
        )
        async with AsyncSendly(live_api_key) as client:
            with pytest.raises(SendlyError):
                await client.whatsapp.signup.create(
                    PHONE, business_account_id="104996582519384"
                )
            with pytest.raises(SendlyError):
                await client.whatsapp.signup.verify(SIGNUP_ID, "482913")
            with pytest.raises(SendlyError):
                await client.whatsapp.senders.upload_profile_photo(PHONE, PNG)

        assert len(httpx_mock.get_requests()) == 3

    @pytest.mark.asyncio
    async def test_async_resend_keeps_the_normal_retry(
        self, live_api_key, no_async_sleep, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/resend",
            method="POST",
            status_code=502,
            json={
                "error": "whatsapp_verification_resend_failed",
                "message": (
                    "WhatsApp couldn't send another code right now. Please try again shortly."
                ),
            },
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/resend", method="POST", json=VERIFYING
        )
        async with AsyncSendly(live_api_key) as client:
            signup = await client.whatsapp.signup.resend(SIGNUP_ID)

        assert signup.status == "verifying"
        assert len(httpx_mock.get_requests()) == 2

    @pytest.mark.asyncio
    async def test_async_facebook_signup_keeps_the_normal_retry(
        self, live_api_key, no_async_sleep, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup",
            method="POST",
            status_code=503,
            headers={"Retry-After": "3600"},
            json={
                "error": "whatsapp_unavailable",
                "message": (
                    "WhatsApp connections are temporarily unavailable. You haven't been "
                    "charged. Please try again later."
                ),
                "retryAfter": 3600,
            },
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup",
            method="POST",
            status_code=201,
            json={
                "id": "was_1",
                "connectUrl": "https://sendly.live/whatsapp/connect?token=abc",
                "status": "initiated",
            },
        )
        async with AsyncSendly(live_api_key) as client:
            session = await client.whatsapp.signup.create(PHONE)

        assert session.status == "initiated"
        assert len(httpx_mock.get_requests()) == 2


class TestTimeoutsAndNetworkErrorsOnCallsThatMustNotRepeat:
    def test_add_by_code_network_error_is_sent_once(
        self, live_api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_exception(
            httpx.ConnectError("Connection reset by peer"),
            url=f"{BASE}/whatsapp/signup",
            method="POST",
            is_reusable=True,
        )

        with pytest.raises(NetworkError):
            client.whatsapp.signup.create(PHONE, business_account_id="104996582519384")

        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_verify_timeout_is_sent_once(self, live_api_key, no_sleep, httpx_mock: HTTPXMock):
        client = Sendly(live_api_key)
        httpx_mock.add_exception(
            httpx.ReadTimeout("timed out"),
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/verify",
            method="POST",
            is_reusable=True,
        )

        with pytest.raises(SendlyTimeoutError):
            client.whatsapp.signup.verify(SIGNUP_ID, "482913")

        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_verify_network_error_is_sent_once(
        self, live_api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_exception(
            httpx.ConnectError("Connection reset by peer"),
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/verify",
            method="POST",
            is_reusable=True,
        )

        with pytest.raises(NetworkError):
            client.whatsapp.signup.verify(SIGNUP_ID, "482913")

        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_photo_upload_network_error_is_sent_once(
        self, live_api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_exception(
            httpx.ReadTimeout("timed out"),
            url=f"{BASE}/whatsapp/senders/{ENCODED}/profile/photo",
            method="POST",
            is_reusable=True,
        )

        with pytest.raises(httpx.ReadTimeout):
            client.whatsapp.senders.upload_profile_photo(PHONE, PNG)

        assert len(httpx_mock.get_requests()) == 1
        client.close()

    def test_verify_still_waits_out_a_429_the_api_never_ran(
        self, live_api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/verify",
            method="POST",
            status_code=429,
            headers={"Retry-After": "1"},
            json={
                "error": "too_many_concurrent_verifications",
                "message": "Too many API key checks are running at once. Try again in a moment.",
                "retryAfter": 1,
            },
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/verify", method="POST", json=ACTIVE
        )

        signup = client.whatsapp.signup.verify(SIGNUP_ID, "482913")

        assert signup.status == "active"
        assert len(httpx_mock.get_requests()) == 2
        client.close()

    @pytest.mark.asyncio
    async def test_async_verify_still_waits_out_a_429_the_api_never_ran(
        self, live_api_key, no_async_sleep, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/verify",
            method="POST",
            status_code=429,
            headers={"Retry-After": "1"},
            json={
                "error": "too_many_concurrent_verifications",
                "message": "Too many API key checks are running at once. Try again in a moment.",
                "retryAfter": 1,
            },
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/verify", method="POST", json=ACTIVE
        )
        async with AsyncSendly(live_api_key) as client:
            signup = await client.whatsapp.signup.verify(SIGNUP_ID, "482913")

        assert signup.status == "active"
        assert len(httpx_mock.get_requests()) == 2

    def test_resend_keeps_the_normal_retry_on_a_network_error(
        self, live_api_key, no_sleep, httpx_mock: HTTPXMock
    ):
        client = Sendly(live_api_key)
        httpx_mock.add_exception(
            httpx.ConnectError("Connection reset by peer"),
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/resend",
            method="POST",
        )
        httpx_mock.add_response(
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/resend", method="POST", json=VERIFYING
        )

        signup = client.whatsapp.signup.resend(SIGNUP_ID)

        assert signup.status == "verifying"
        assert len(httpx_mock.get_requests()) == 2
        client.close()

    @pytest.mark.asyncio
    async def test_async_add_by_code_and_verify_network_errors_are_sent_once(
        self, live_api_key, no_async_sleep, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_exception(
            httpx.ConnectError("Connection reset by peer"),
            url=f"{BASE}/whatsapp/signup",
            method="POST",
            is_reusable=True,
        )
        httpx_mock.add_exception(
            httpx.ReadTimeout("timed out"),
            url=f"{BASE}/whatsapp/signup/{SIGNUP_ID}/verify",
            method="POST",
            is_reusable=True,
        )
        async with AsyncSendly(live_api_key) as client:
            with pytest.raises(NetworkError):
                await client.whatsapp.signup.create(
                    PHONE, business_account_id="104996582519384"
                )
            with pytest.raises(SendlyTimeoutError):
                await client.whatsapp.signup.verify(SIGNUP_ID, "482913")

        assert len(httpx_mock.get_requests()) == 2


class TestExports:
    def test_new_types_are_exported_from_the_package(self):
        import sendly

        for name in (
            "CallChannel",
            "WhatsAppCallingSettings",
            "WhatsAppCommand",
            "WhatsAppConversationalComponents",
        ):
            assert name in sendly.__all__
            assert getattr(sendly, name) is getattr(sendly.types, name)

    def test_api_error_response_reads_attempts_remaining(self):
        from sendly.types import ApiErrorResponse

        response = ApiErrorResponse(
            error="whatsapp_verification_code_invalid",
            message="That code wasn't accepted. Check it, or request a new one.",
            attemptsRemaining=3,
        )

        assert response.attempts_remaining == 3
