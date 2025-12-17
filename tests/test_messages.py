"""
Tests for Messages resource (send, list, get, list_all)
"""

import pytest
from pytest_httpx import HTTPXMock

from sendly import Sendly
from sendly.errors import (
    AuthenticationError,
    InsufficientCreditsError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from sendly.types import Message, MessageListResponse


class TestMessagesSend:
    """Test messages.send() method"""

    def test_send_basic_message(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test sending a basic SMS message"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_message,
        )

        message = client.messages.send(to="+15551234567", text="Test message")

        assert isinstance(message, Message)
        assert message.id == "msg_test_123"
        assert message.to == "+15551234567"
        assert message.text == "Test message"
        assert message.status.value == "queued"

        client.close()

    def test_send_with_sender_id(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test sending message with custom sender ID"""
        client = Sendly(api_key)

        mock_message["from"] = "MyBrand"
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_message,
        )

        message = client.messages.send(
            to="+15551234567",
            text="Test message",
            from_="MyBrand",
        )

        assert message.from_ == "MyBrand"

        # Verify request body contains the sender ID
        request = httpx_mock.get_request()
        body = request.read().decode()
        assert "MyBrand" in body
        assert '"from"' in body or '"from":' in body

        client.close()

    def test_send_long_message(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test sending a long message (multiple segments)"""
        client = Sendly(api_key)

        long_text = "A" * 500
        mock_message["text"] = long_text
        mock_message["segments"] = 4

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_message,
        )

        message = client.messages.send(to="+15551234567", text=long_text)

        assert message.segments == 4

        client.close()

    def test_send_validation_error_invalid_phone(self, api_key):
        """Test send with invalid phone number format"""
        client = Sendly(api_key)

        # Missing +
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            client.messages.send(to="15551234567", text="Test")

        # Not E.164 format
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            client.messages.send(to="+1-555-123-4567", text="Test")

        # Too short
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            client.messages.send(to="+1", text="Test")

        # Letters in number
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            client.messages.send(to="+155512A4567", text="Test")

        client.close()

    def test_send_validation_error_empty_text(self, api_key):
        """Test send with empty message text"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Message text is required"):
            client.messages.send(to="+15551234567", text="")

        client.close()

    def test_send_validation_error_empty_phone(self, api_key):
        """Test send with empty phone number"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Phone number is required"):
            client.messages.send(to="", text="Test")

        client.close()

    def test_send_validation_error_invalid_sender_id(self, api_key):
        """Test send with invalid sender ID"""
        client = Sendly(api_key)

        # Too short
        with pytest.raises(ValidationError, match="Invalid sender ID"):
            client.messages.send(to="+15551234567", text="Test", from_="A")

        # Too long
        with pytest.raises(ValidationError, match="Invalid sender ID"):
            client.messages.send(to="+15551234567", text="Test", from_="ABCDEFGHIJKL")

        # Special characters
        with pytest.raises(ValidationError, match="Invalid sender ID"):
            client.messages.send(to="+15551234567", text="Test", from_="Test@Brand")

        client.close()

    def test_send_authentication_error_401(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test send with authentication error (401)"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=401,
            json=mock_error_response("unauthorized", "Invalid API key"),
        )

        with pytest.raises(AuthenticationError) as exc_info:
            client.messages.send(to="+15551234567", text="Test")

        assert exc_info.value.code == "unauthorized"
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in str(exc_info.value)

        client.close()

    def test_send_insufficient_credits_402(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test send with insufficient credits (402)"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=402,
            json=mock_error_response(
                "insufficient_credits",
                "Not enough credits",
                creditsNeeded=10,
                currentBalance=5,
            ),
        )

        with pytest.raises(InsufficientCreditsError) as exc_info:
            client.messages.send(to="+15551234567", text="Test")

        assert exc_info.value.code == "insufficient_credits"
        assert exc_info.value.status_code == 402
        assert exc_info.value.credits_needed == 10
        assert exc_info.value.current_balance == 5

        client.close()

    def test_send_rate_limit_429(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        """Test send with rate limit exceeded (429)"""
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=429,
            json=mock_error_response(
                "rate_limit_exceeded",
                "Rate limit exceeded",
                retryAfter=60,
            ),
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.messages.send(to="+15551234567", text="Test")

        assert exc_info.value.code == "rate_limit_exceeded"
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 60

        client.close()

    def test_send_server_error_500_with_retry(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test send with server error (500) and successful retry"""
        client = Sendly(api_key, max_retries=2)

        # First request fails, second succeeds
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=500,
            json={"error": "internal_error", "message": "Server error"},
        )
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_message,
        )

        message = client.messages.send(to="+15551234567", text="Test")

        assert message.id == "msg_test_123"
        assert len(httpx_mock.get_requests()) == 2

        client.close()

    def test_send_network_error_with_retry(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test send with network error and successful retry"""
        import httpx

        client = Sendly(api_key, max_retries=2)

        # First request fails with network error
        httpx_mock.add_exception(httpx.RequestError("Connection failed"))
        # Second succeeds
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_message,
        )

        message = client.messages.send(to="+15551234567", text="Test")

        assert message.id == "msg_test_123"

        client.close()

    def test_send_timeout_error(self, api_key, httpx_mock: HTTPXMock):
        """Test send with timeout"""
        client = Sendly(api_key, timeout=0.001, max_retries=0)

        import httpx

        httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))

        with pytest.raises(TimeoutError):
            client.messages.send(to="+15551234567", text="Test")

        client.close()


class TestMessagesList:
    """Test messages.list() method"""

    def test_list_basic(self, api_key, mock_message_list, httpx_mock: HTTPXMock):
        """Test listing messages without parameters"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="GET",
            json=mock_message_list,
        )

        result = client.messages.list()

        assert isinstance(result, MessageListResponse)
        assert result.count == 2
        assert len(result.data) == 2
        assert result.data[0].id == "msg_test_1"
        assert result.data[1].id == "msg_test_2"

        client.close()

    def test_list_with_limit(self, api_key, mock_message_list, httpx_mock: HTTPXMock):
        """Test listing messages with limit parameter"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages?limit=10",
            method="GET",
            json=mock_message_list,
        )

        result = client.messages.list(limit=10)

        assert result.count == 2
        request = httpx_mock.get_request()
        assert "limit=10" in str(request.url)

        client.close()

    def test_list_validation_error_limit_too_low(self, api_key):
        """Test list with limit < 1"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            client.messages.list(limit=0)

        client.close()

    def test_list_validation_error_limit_too_high(self, api_key):
        """Test list with limit > 100"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            client.messages.list(limit=101)

        client.close()

    def test_list_validation_error_limit_not_integer(self, api_key):
        """Test list with non-integer limit"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Limit must be an integer"):
            client.messages.list(limit="10")

        client.close()

    def test_list_authentication_error_401(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test list with authentication error"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="GET",
            status_code=401,
            json=mock_error_response("unauthorized", "Invalid API key"),
        )

        with pytest.raises(AuthenticationError):
            client.messages.list()

        client.close()

    def test_list_rate_limit_429(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        """Test list with rate limit"""
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="GET",
            status_code=429,
            json=mock_error_response("rate_limit_exceeded", "Too many requests", retryAfter=30),
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.messages.list()

        assert exc_info.value.retry_after == 30

        client.close()

    def test_list_empty_result(self, api_key, httpx_mock: HTTPXMock):
        """Test list with empty results"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="GET",
            json={"data": [], "count": 0},
        )

        result = client.messages.list()

        assert result.count == 0
        assert len(result.data) == 0

        client.close()


class TestMessagesGet:
    """Test messages.get() method"""

    def test_get_by_id(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test getting a message by ID"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/msg_test_123",
            method="GET",
            json=mock_message,
        )

        message = client.messages.get("msg_test_123")

        assert isinstance(message, Message)
        assert message.id == "msg_test_123"

        client.close()

    def test_get_validation_error_empty_id(self, api_key):
        """Test get with empty ID"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Message ID is required"):
            client.messages.get("")

        client.close()

    def test_get_validation_error_invalid_id_format(self, api_key):
        """Test get with invalid ID format"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Invalid message ID format"):
            client.messages.get("invalid-id")

        with pytest.raises(ValidationError, match="Invalid message ID format"):
            client.messages.get("msg")

        client.close()

    def test_get_not_found_404(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        """Test get with non-existent message (404)"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/msg_nonexistent",
            method="GET",
            status_code=404,
            json=mock_error_response("not_found", "Message not found"),
        )

        with pytest.raises(NotFoundError) as exc_info:
            client.messages.get("msg_nonexistent")

        assert exc_info.value.code == "not_found"
        assert exc_info.value.status_code == 404

        client.close()

    def test_get_authentication_error_401(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test get with authentication error"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/msg_test_123",
            method="GET",
            status_code=401,
            json=mock_error_response("unauthorized", "Invalid API key"),
        )

        with pytest.raises(AuthenticationError):
            client.messages.get("msg_test_123")

        client.close()

    def test_get_uuid_format_id(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test get with UUID format message ID"""
        client = Sendly(api_key)

        uuid_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_message["id"] = uuid_id

        httpx_mock.add_response(
            url=f"https://sendly.live/api/v1/messages/{uuid_id}",
            method="GET",
            json=mock_message,
        )

        message = client.messages.get(uuid_id)

        assert message.id == uuid_id

        client.close()


class TestMessagesListAll:
    """Test messages.list_all() generator method"""

    def test_list_all_single_page(self, api_key, httpx_mock: HTTPXMock):
        """Test list_all with results fitting in one page"""
        client = Sendly(api_key)

        mock_data = {
            "data": [
                {
                    "id": f"msg_{i}",
                    "to": "+15551234567",
                    "from": "Sendly",
                    "text": f"Message {i}",
                    "status": "delivered",
                    "segments": 1,
                    "creditsUsed": 1,
                    "isSandbox": True,
                    "createdAt": "2025-01-20T10:00:00Z",
                }
                for i in range(50)
            ],
            "count": 50,
        }

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages?limit=100&offset=0",
            method="GET",
            json=mock_data,
        )

        messages = list(client.messages.list_all())

        assert len(messages) == 50
        assert messages[0].id == "msg_0"
        assert messages[49].id == "msg_49"

        client.close()

    def test_list_all_multiple_pages(self, api_key, httpx_mock: HTTPXMock):
        """Test list_all with pagination across multiple pages"""
        client = Sendly(api_key)

        # First page
        page1 = {
            "data": [
                {
                    "id": f"msg_{i}",
                    "to": "+15551234567",
                    "from": "Sendly",
                    "text": f"Message {i}",
                    "status": "delivered",
                    "segments": 1,
                    "creditsUsed": 1,
                    "isSandbox": True,
                    "createdAt": "2025-01-20T10:00:00Z",
                }
                for i in range(100)
            ],
            "count": 100,
        }

        # Second page
        page2 = {
            "data": [
                {
                    "id": f"msg_{i}",
                    "to": "+15551234567",
                    "from": "Sendly",
                    "text": f"Message {i}",
                    "status": "delivered",
                    "segments": 1,
                    "creditsUsed": 1,
                    "isSandbox": True,
                    "createdAt": "2025-01-20T10:00:00Z",
                }
                for i in range(100, 150)
            ],
            "count": 50,
        }

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages?limit=100&offset=0",
            method="GET",
            json=page1,
        )
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages?limit=100&offset=100",
            method="GET",
            json=page2,
        )

        messages = list(client.messages.list_all())

        assert len(messages) == 150
        assert messages[0].id == "msg_0"
        assert messages[99].id == "msg_99"
        assert messages[100].id == "msg_100"

        client.close()


    def test_list_all_empty_results(self, api_key, httpx_mock: HTTPXMock):
        """Test list_all with no messages"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages?limit=100&offset=0",
            method="GET",
            json={"data": [], "count": 0},
        )

        messages = list(client.messages.list_all())

        assert len(messages) == 0

        client.close()

    def test_list_all_authentication_error(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test list_all with authentication error"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages?limit=100&offset=0",
            method="GET",
            status_code=401,
            json=mock_error_response("unauthorized", "Invalid API key"),
        )

        with pytest.raises(AuthenticationError):
            list(client.messages.list_all())

        client.close()
