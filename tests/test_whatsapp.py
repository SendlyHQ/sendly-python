"""
Tests for WhatsApp resource (signup, senders, templates, window) and
messages.send with channel='whatsapp'
"""

import json

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly, Sendly
from sendly.errors import NotFoundError, SendlyError, ValidationError
from sendly.types import (
    WhatsAppMessage,
    WhatsAppSenderListResponse,
    WhatsAppSignup,
    WhatsAppSignupSession,
    WhatsAppTemplate,
    WhatsAppTemplateDeletedResponse,
    WhatsAppTemplateListResponse,
    WhatsAppWindow,
)


@pytest.fixture
def mock_signup_session():
    return {
        "id": "was_123",
        "connectUrl": "https://sendly.live/whatsapp/connect/was_123",
        "status": "initiated",
    }


@pytest.fixture
def mock_signup():
    return {
        "id": "was_123",
        "status": "active",
        "phoneNumber": "+15559876543",
        "businessAccountId": "1122334455667788",
        "failureReasons": None,
        "updatedAt": "2026-07-30T10:00:00Z",
    }


@pytest.fixture
def mock_sender():
    return {
        "phoneNumber": "+15559876543",
        "displayName": "Acme Inc",
        "status": "active",
        "qualityRating": "GREEN",
        "createdAt": "2026-07-30T10:00:00Z",
    }


@pytest.fixture
def mock_template():
    return {
        "id": "wat_123",
        "name": "order_shipped",
        "language": "en_US",
        "category": "UTILITY",
        "status": "PENDING",
        "qualityRating": None,
        "rejectionReason": None,
        "createdAt": "2026-07-30T10:00:00Z",
        "updatedAt": "2026-07-30T10:00:00Z",
    }


@pytest.fixture
def mock_whatsapp_message():
    return {
        "id": "msg_wa_123",
        "channel": "whatsapp",
        "message_format": "whatsapp",
        "to": "+15551234567",
        "from": "+15559876543",
        "text": "Your table is ready!",
        "status": "queued",
        "segments": 1,
        "creditsUsed": 1,
        "whatsapp": {"kind": "text", "messageId": None},
        "createdAt": "2026-07-30T10:00:00Z",
    }


class TestSignupCreate:
    def test_create_signup(self, api_key, mock_signup_session, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/signup",
            method="POST",
            status_code=201,
            json=mock_signup_session,
        )

        result = client.whatsapp.signup.create("+15559876543")

        assert isinstance(result, WhatsAppSignupSession)
        assert result.id == "was_123"
        assert result.connect_url == "https://sendly.live/whatsapp/connect/was_123"
        assert result.status == "initiated"

        request = httpx_mock.get_request()
        body = request.read().decode()
        assert '"phoneNumber"' in body
        assert "+15559876543" in body

        client.close()

    def test_create_signup_invalid_phone(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Invalid phone number format"):
            client.whatsapp.signup.create("15559876543")

        client.close()

    def test_create_signup_not_eligible_400(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/signup",
            method="POST",
            status_code=400,
            json=mock_error_response(
                "number_not_eligible", "Number is not eligible for WhatsApp"
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.whatsapp.signup.create("+15559876543")

        assert exc_info.value.code == "number_not_eligible"

        client.close()


class TestSignupGet:
    def test_get_signup(self, api_key, mock_signup, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/signup/was_123",
            method="GET",
            json=mock_signup,
        )

        result = client.whatsapp.signup.get("was_123")

        assert isinstance(result, WhatsAppSignup)
        assert result.status == "active"
        assert result.phone_number == "+15559876543"
        assert result.business_account_id == "1122334455667788"
        assert result.failure_reasons is None
        assert result.updated_at == "2026-07-30T10:00:00Z"

        client.close()

    def test_get_signup_failed(self, api_key, mock_signup, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/signup/was_123",
            method="GET",
            json={
                **mock_signup,
                "status": "failed",
                "businessAccountId": None,
                "failureReasons": ["Display name rejected"],
            },
        )

        result = client.whatsapp.signup.get("was_123")

        assert result.status == "failed"
        assert result.business_account_id is None
        assert result.failure_reasons == ["Display name rejected"]

        client.close()

    def test_get_signup_requires_id(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="A signup 'id' is required"):
            client.whatsapp.signup.get("")

        client.close()

    def test_get_signup_not_found_404(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/signup/was_missing",
            method="GET",
            status_code=404,
            json=mock_error_response("not_found", "Not found"),
        )

        with pytest.raises(NotFoundError):
            client.whatsapp.signup.get("was_missing")

        client.close()


class TestSendersList:
    def test_list_senders(self, api_key, mock_sender, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/senders",
            method="GET",
            json={"senders": [mock_sender]},
        )

        result = client.whatsapp.senders.list()

        assert isinstance(result, WhatsAppSenderListResponse)
        assert len(result.senders) == 1
        sender = result.senders[0]
        assert sender.phone_number == "+15559876543"
        assert sender.display_name == "Acme Inc"
        assert sender.status == "active"
        assert sender.quality_rating == "GREEN"
        assert sender.created_at == "2026-07-30T10:00:00Z"

        client.close()

    def test_list_senders_empty(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/senders",
            method="GET",
            json={"senders": []},
        )

        result = client.whatsapp.senders.list()

        assert result.senders == []

        client.close()


class TestTemplatesList:
    def test_list_templates(self, api_key, mock_template, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/templates",
            method="GET",
            json={"templates": [mock_template]},
        )

        result = client.whatsapp.templates.list()

        assert isinstance(result, WhatsAppTemplateListResponse)
        assert len(result.templates) == 1
        template = result.templates[0]
        assert template.id == "wat_123"
        assert template.name == "order_shipped"
        assert template.language == "en_US"
        assert template.category == "UTILITY"
        assert template.status == "PENDING"
        assert template.quality_rating is None
        assert template.rejection_reason is None

        client.close()


class TestTemplatesCreate:
    def test_create_template(self, api_key, mock_template, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/templates",
            method="POST",
            status_code=201,
            json=mock_template,
        )

        result = client.whatsapp.templates.create(
            sender="+15559876543",
            name="order_shipped",
            language="en_US",
            category="UTILITY",
            body="Hi {{1}}, your order {{2}} has shipped!",
            examples={"1": "Sam", "2": "#4821"},
        )

        assert isinstance(result, WhatsAppTemplate)
        assert result.status == "PENDING"
        assert result.warnings is None

        request = httpx_mock.get_request()
        payload = json.loads(request.read().decode())
        assert payload["sender"] == "+15559876543"
        assert payload["name"] == "order_shipped"
        assert payload["language"] == "en_US"
        assert payload["category"] == "UTILITY"
        assert payload["body"] == "Hi {{1}}, your order {{2}} has shipped!"
        assert payload["examples"] == {"1": "Sam", "2": "#4821"}
        assert "footer" not in payload
        assert "header" not in payload
        assert "buttons" not in payload

        client.close()

    def test_create_template_with_all_fields(
        self, api_key, mock_template, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/templates",
            method="POST",
            status_code=201,
            json={**mock_template, "category": "MARKETING", "warnings": ["No opt-out button"]},
        )

        result = client.whatsapp.templates.create(
            sender="+15559876543",
            name="spring_sale",
            language="en_US",
            category="MARKETING",
            body="Hi {{1}}, our spring sale is on!",
            footer="Reply STOP to opt out",
            header="Spring Sale",
            buttons=[{"type": "quick_reply", "text": "Stop promotions"}],
            examples={"1": "Sam"},
        )

        assert result.warnings == ["No opt-out button"]

        request = httpx_mock.get_request()
        payload = json.loads(request.read().decode())
        assert payload["footer"] == "Reply STOP to opt out"
        assert payload["header"] == "Spring Sale"
        assert payload["buttons"] == [{"type": "quick_reply", "text": "Stop promotions"}]

        client.close()

    def test_create_template_invalid_sender(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Invalid phone number format"):
            client.whatsapp.templates.create(
                sender="not-a-number",
                name="order_shipped",
                language="en_US",
                category="UTILITY",
                body="Hi {{1}}!",
            )

        client.close()

    def test_create_template_rejected_400(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/templates",
            method="POST",
            status_code=400,
            json=mock_error_response(
                "template_invalid", "Every body placeholder needs an example value"
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.whatsapp.templates.create(
                sender="+15559876543",
                name="order_shipped",
                language="en_US",
                category="UTILITY",
                body="Hi {{1}}!",
            )

        assert exc_info.value.code == "template_invalid"

        client.close()


class TestTemplatesUpdate:
    def test_update_template(self, api_key, mock_template, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/templates/wat_123",
            method="PATCH",
            json=mock_template,
        )

        result = client.whatsapp.templates.update(
            "wat_123",
            body="Hi {{1}}, your order {{2}} is on its way!",
            examples={"1": "Sam", "2": "#4821"},
        )

        assert isinstance(result, WhatsAppTemplate)
        assert result.status == "PENDING"

        request = httpx_mock.get_request()
        payload = json.loads(request.read().decode())
        assert payload["body"] == "Hi {{1}}, your order {{2}} is on its way!"
        assert payload["examples"] == {"1": "Sam", "2": "#4821"}
        assert "footer" not in payload
        assert "header" not in payload
        assert "buttons" not in payload

        client.close()

    def test_update_template_requires_id(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="A template 'id' is required"):
            client.whatsapp.templates.update("", body="Hi!")

        client.close()

    def test_update_template_not_editable_400(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/templates/wat_123",
            method="PATCH",
            status_code=400,
            json=mock_error_response(
                "template_not_editable", "Only APPROVED or REJECTED templates can be edited"
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.whatsapp.templates.update("wat_123", body="Hi!")

        assert exc_info.value.code == "template_not_editable"

        client.close()


class TestTemplatesDelete:
    def test_delete_template(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/templates/wat_123",
            method="DELETE",
            json={"id": "wat_123", "deleted": True},
        )

        result = client.whatsapp.templates.delete("wat_123")

        assert isinstance(result, WhatsAppTemplateDeletedResponse)
        assert result.id == "wat_123"
        assert result.deleted is True

        client.close()

    def test_delete_template_requires_id(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="A template 'id' is required"):
            client.whatsapp.templates.delete("")

        client.close()

    def test_delete_template_not_found_404(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/templates/wat_missing",
            method="DELETE",
            status_code=404,
            json=mock_error_response("not_found", "Not found"),
        )

        with pytest.raises(NotFoundError):
            client.whatsapp.templates.delete("wat_missing")

        client.close()


class TestWindow:
    def test_window_open(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/window?from=%2B15559876543&to=%2B15551234567",
            method="GET",
            json={"open": True, "expiresAt": "2026-07-31T10:00:00Z"},
        )

        result = client.whatsapp.window(from_="+15559876543", to="+15551234567")

        assert isinstance(result, WhatsAppWindow)
        assert result.open is True
        assert result.expires_at == "2026-07-31T10:00:00Z"

        client.close()

    def test_window_closed(self, api_key, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/window?from=%2B15559876543&to=%2B15551234567",
            method="GET",
            json={"open": False, "expiresAt": None},
        )

        result = client.whatsapp.window(from_="+15559876543", to="+15551234567")

        assert result.open is False
        assert result.expires_at is None

        client.close()

    def test_window_invalid_numbers(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Invalid phone number format"):
            client.whatsapp.window(from_="invalid", to="+15551234567")

        with pytest.raises(ValidationError, match="Invalid phone number format"):
            client.whatsapp.window(from_="+15559876543", to="invalid")

        client.close()


class TestWhatsAppSend:
    def test_send_text(self, api_key, mock_whatsapp_message, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_whatsapp_message,
        )

        message = client.messages.send(
            channel="whatsapp",
            to="+15551234567",
            from_="+15559876543",
            text="Your table is ready!",
        )

        assert isinstance(message, WhatsAppMessage)
        assert message.id == "msg_wa_123"
        assert message.channel == "whatsapp"
        assert message.from_ == "+15559876543"
        assert message.text == "Your table is ready!"
        assert message.status.value == "queued"
        assert message.segments == 1
        assert message.whatsapp.kind == "text"
        assert message.whatsapp.template is None
        assert message.whatsapp.message_id is None

        request = httpx_mock.get_request()
        payload = json.loads(request.read().decode())
        assert payload["channel"] == "whatsapp"
        assert payload["to"] == "+15551234567"
        assert payload["from"] == "+15559876543"
        assert payload["text"] == "Your table is ready!"
        assert "mediaUrls" not in payload
        assert "template" not in payload

        client.close()

    def test_send_media_with_caption(
        self, api_key, mock_whatsapp_message, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json={
                **mock_whatsapp_message,
                "text": None,
                "whatsapp": {"kind": "media", "messageId": None},
            },
        )

        message = client.messages.send(
            channel="whatsapp",
            to="+15551234567",
            from_="+15559876543",
            text="Here is the menu",
            media_urls=["https://example.com/menu.jpg"],
        )

        assert message.whatsapp.kind == "media"
        assert message.text is None

        request = httpx_mock.get_request()
        payload = json.loads(request.read().decode())
        assert payload["mediaUrls"] == ["https://example.com/menu.jpg"]
        assert payload["text"] == "Here is the menu"

        client.close()

    def test_send_template(self, api_key, mock_whatsapp_message, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json={
                **mock_whatsapp_message,
                "text": None,
                "creditsUsed": 2,
                "whatsapp": {
                    "kind": "template",
                    "template": {
                        "name": "order_shipped",
                        "language": "en_US",
                        "category": "utility",
                    },
                    "messageId": None,
                },
            },
        )

        message = client.messages.send(
            channel="whatsapp",
            to="+15551234567",
            from_="+15559876543",
            template={
                "name": "order_shipped",
                "language": "en_US",
                "variables": {"1": "Acme Inc", "2": "#4821"},
            },
        )

        assert message.whatsapp.kind == "template"
        assert message.whatsapp.template is not None
        assert message.whatsapp.template.name == "order_shipped"
        assert message.whatsapp.template.category == "utility"
        assert message.credits_used == 2

        request = httpx_mock.get_request()
        payload = json.loads(request.read().decode())
        assert payload["template"] == {
            "name": "order_shipped",
            "language": "en_US",
            "variables": {"1": "Acme Inc", "2": "#4821"},
        }
        assert "text" not in payload

        client.close()

    def test_send_requires_from(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Phone number is required"):
            client.messages.send(
                channel="whatsapp",
                to="+15551234567",
                text="Hello!",
            )

        client.close()

    def test_send_requires_body(self, api_key):
        client = Sendly(api_key)

        with pytest.raises(SendlyError) as exc_info:
            client.messages.send(
                channel="whatsapp",
                to="+15551234567",
                from_="+15559876543",
            )

        assert exc_info.value.code == "invalid_request"
        assert "Provide 'text', 'media_urls', or 'template'" in str(exc_info.value)

        client.close()

    def test_send_window_closed_422(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=422,
            json=mock_error_response(
                "whatsapp_window_closed",
                "No open 24-hour window - send an approved template instead",
            ),
        )

        with pytest.raises(SendlyError) as exc_info:
            client.messages.send(
                channel="whatsapp",
                to="+15551234567",
                from_="+15559876543",
                text="Hello!",
            )

        assert exc_info.value.code == "whatsapp_window_closed"

        client.close()

    def test_send_sms_unchanged(self, api_key, mock_message, httpx_mock: HTTPXMock):
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_message,
        )

        message = client.messages.send(to="+15551234567", text="Test message")

        assert message.id == "msg_test_123"

        request = httpx_mock.get_request()
        payload = json.loads(request.read().decode())
        assert "channel" not in payload

        client.close()


class TestAsyncWhatsApp:
    async def test_async_create_signup(
        self, api_key, mock_signup_session, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/signup",
            method="POST",
            status_code=201,
            json=mock_signup_session,
        )

        result = await client.whatsapp.signup.create("+15559876543")

        assert isinstance(result, WhatsAppSignupSession)
        assert result.connect_url == "https://sendly.live/whatsapp/connect/was_123"

        await client.close()

    async def test_async_get_signup(self, api_key, mock_signup, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/signup/was_123",
            method="GET",
            json=mock_signup,
        )

        result = await client.whatsapp.signup.get("was_123")

        assert isinstance(result, WhatsAppSignup)
        assert result.status == "active"

        await client.close()

    async def test_async_list_senders(self, api_key, mock_sender, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/senders",
            method="GET",
            json={"senders": [mock_sender]},
        )

        result = await client.whatsapp.senders.list()

        assert isinstance(result, WhatsAppSenderListResponse)
        assert result.senders[0].display_name == "Acme Inc"

        await client.close()

    async def test_async_create_template(
        self, api_key, mock_template, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/templates",
            method="POST",
            status_code=201,
            json=mock_template,
        )

        result = await client.whatsapp.templates.create(
            sender="+15559876543",
            name="order_shipped",
            language="en_US",
            category="UTILITY",
            body="Hi {{1}}, your order {{2}} has shipped!",
            examples={"1": "Sam", "2": "#4821"},
        )

        assert isinstance(result, WhatsAppTemplate)
        assert result.status == "PENDING"

        request = httpx_mock.get_request()
        payload = json.loads(request.read().decode())
        assert payload["sender"] == "+15559876543"

        await client.close()

    async def test_async_window(self, api_key, httpx_mock: HTTPXMock):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/whatsapp/window?from=%2B15559876543&to=%2B15551234567",
            method="GET",
            json={"open": False, "expiresAt": None},
        )

        result = await client.whatsapp.window(from_="+15559876543", to="+15551234567")

        assert result.open is False

        await client.close()

    async def test_async_send_whatsapp(
        self, api_key, mock_whatsapp_message, httpx_mock: HTTPXMock
    ):
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_whatsapp_message,
        )

        message = await client.messages.send(
            channel="whatsapp",
            to="+15551234567",
            from_="+15559876543",
            text="Your table is ready!",
        )

        assert isinstance(message, WhatsAppMessage)
        assert message.whatsapp.kind == "text"

        await client.close()
