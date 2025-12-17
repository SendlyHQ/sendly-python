"""
Tests for scheduled messages (schedule, list_scheduled, get_scheduled, cancel_scheduled)
"""

import pytest
from pytest_httpx import HTTPXMock

from sendly import Sendly
from sendly.errors import (
    AuthenticationError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from sendly.types import (
    CancelledMessageResponse,
    ScheduledMessage,
    ScheduledMessageListResponse,
)


class TestMessagesSchedule:
    """Test messages.schedule() method"""

    def test_schedule_basic(self, api_key, mock_scheduled_message, httpx_mock: HTTPXMock):
        """Test scheduling a basic message"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/schedule",
            method="POST",
            json=mock_scheduled_message,
        )

        scheduled = client.messages.schedule(
            to="+15551234567",
            text="Scheduled message",
            scheduled_at="2025-01-21T10:00:00Z",
        )

        assert isinstance(scheduled, ScheduledMessage)
        assert scheduled.id == "msg_scheduled_123"
        assert scheduled.to == "+15551234567"
        assert scheduled.text == "Scheduled message"
        assert scheduled.status.value == "scheduled"
        assert scheduled.scheduled_at == "2025-01-21T10:00:00Z"

        client.close()

    def test_schedule_with_sender_id(self, api_key, mock_scheduled_message, httpx_mock: HTTPXMock):
        """Test scheduling message with sender ID"""
        client = Sendly(api_key)

        mock_scheduled_message["from"] = "MyBrand"

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/schedule",
            method="POST",
            json=mock_scheduled_message,
        )

        scheduled = client.messages.schedule(
            to="+15551234567",
            text="Scheduled message",
            scheduled_at="2025-01-21T10:00:00Z",
            from_="MyBrand",
        )

        assert scheduled.from_ == "MyBrand"

        # Verify request body contains the sender ID
        request = httpx_mock.get_request()
        body = request.read().decode()
        assert "MyBrand" in body
        assert '"from"' in body or '"from":' in body

        client.close()

    def test_schedule_validation_error_invalid_phone(self, api_key):
        """Test schedule with invalid phone number"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Invalid phone number format"):
            client.messages.schedule(
                to="invalid",
                text="Test",
                scheduled_at="2025-01-21T10:00:00Z",
            )

        client.close()

    def test_schedule_validation_error_empty_text(self, api_key):
        """Test schedule with empty text"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Message text is required"):
            client.messages.schedule(
                to="+15551234567",
                text="",
                scheduled_at="2025-01-21T10:00:00Z",
            )

        client.close()

    def test_schedule_validation_error_invalid_sender_id(self, api_key):
        """Test schedule with invalid sender ID"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Invalid sender ID"):
            client.messages.schedule(
                to="+15551234567",
                text="Test",
                scheduled_at="2025-01-21T10:00:00Z",
                from_="X",  # Too short
            )

        client.close()

    def test_schedule_authentication_error_401(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test schedule with authentication error"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/schedule",
            method="POST",
            status_code=401,
            json=mock_error_response("unauthorized", "Invalid API key"),
        )

        with pytest.raises(AuthenticationError):
            client.messages.schedule(
                to="+15551234567",
                text="Test",
                scheduled_at="2025-01-21T10:00:00Z",
            )

        client.close()

    def test_schedule_insufficient_credits_402(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test schedule with insufficient credits"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/schedule",
            method="POST",
            status_code=402,
            json=mock_error_response(
                "insufficient_credits",
                "Not enough credits",
                creditsNeeded=5,
                currentBalance=2,
            ),
        )

        with pytest.raises(InsufficientCreditsError) as exc_info:
            client.messages.schedule(
                to="+15551234567",
                text="Test",
                scheduled_at="2025-01-21T10:00:00Z",
            )

        assert exc_info.value.credits_needed == 5
        assert exc_info.value.current_balance == 2

        client.close()

    def test_schedule_rate_limit_429(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        """Test schedule with rate limit"""
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/schedule",
            method="POST",
            status_code=429,
            json=mock_error_response(
                "rate_limit_exceeded",
                "Too many requests",
                retryAfter=45,
            ),
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.messages.schedule(
                to="+15551234567",
                text="Test",
                scheduled_at="2025-01-21T10:00:00Z",
            )

        assert exc_info.value.retry_after == 45

        client.close()

    def test_schedule_server_error_500(
        self, api_key, mock_error_response, mock_scheduled_message, httpx_mock: HTTPXMock
    ):
        """Test schedule with server error and retry"""
        client = Sendly(api_key, max_retries=1)

        # First fails, second succeeds
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/schedule",
            method="POST",
            status_code=500,
            json=mock_error_response("internal_error", "Server error"),
        )
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/schedule",
            method="POST",
            json=mock_scheduled_message,
        )

        scheduled = client.messages.schedule(
            to="+15551234567",
            text="Test",
            scheduled_at="2025-01-21T10:00:00Z",
        )

        assert scheduled.id == "msg_scheduled_123"

        client.close()


class TestListScheduled:
    """Test messages.list_scheduled() method"""

    def test_list_scheduled_basic(self, api_key, mock_scheduled_list, httpx_mock: HTTPXMock):
        """Test listing scheduled messages"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled",
            method="GET",
            json=mock_scheduled_list,
        )

        result = client.messages.list_scheduled()

        assert isinstance(result, ScheduledMessageListResponse)
        assert result.count == 1
        assert len(result.data) == 1
        assert result.data[0].id == "msg_scheduled_1"

        client.close()

    def test_list_scheduled_with_limit(self, api_key, mock_scheduled_list, httpx_mock: HTTPXMock):
        """Test listing scheduled messages with limit"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled?limit=10",
            method="GET",
            json=mock_scheduled_list,
        )

        result = client.messages.list_scheduled(limit=10)

        assert result.count == 1
        request = httpx_mock.get_request()
        assert "limit=10" in str(request.url)

        client.close()

    def test_list_scheduled_with_offset(self, api_key, mock_scheduled_list, httpx_mock: HTTPXMock):
        """Test listing scheduled messages with offset"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled?offset=5",
            method="GET",
            json=mock_scheduled_list,
        )

        result = client.messages.list_scheduled(offset=5)

        assert result.count == 1
        request = httpx_mock.get_request()
        assert "offset=5" in str(request.url)

        client.close()

    def test_list_scheduled_with_status_filter(
        self, api_key, mock_scheduled_list, httpx_mock: HTTPXMock
    ):
        """Test listing scheduled messages with status filter"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled?status=scheduled",
            method="GET",
            json=mock_scheduled_list,
        )

        result = client.messages.list_scheduled(status="scheduled")

        assert result.count == 1
        request = httpx_mock.get_request()
        assert "status=scheduled" in str(request.url)

        client.close()

    def test_list_scheduled_with_all_params(
        self, api_key, mock_scheduled_list, httpx_mock: HTTPXMock
    ):
        """Test listing scheduled messages with all parameters"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled?limit=20&offset=10&status=scheduled",
            method="GET",
            json=mock_scheduled_list,
        )

        result = client.messages.list_scheduled(limit=20, offset=10, status="scheduled")

        assert result.count == 1

        client.close()

    def test_list_scheduled_validation_error_limit(self, api_key):
        """Test list_scheduled with invalid limit"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            client.messages.list_scheduled(limit=0)

        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            client.messages.list_scheduled(limit=101)

        client.close()

    def test_list_scheduled_authentication_error_401(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test list_scheduled with authentication error"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled",
            method="GET",
            status_code=401,
            json=mock_error_response("unauthorized", "Invalid API key"),
        )

        with pytest.raises(AuthenticationError):
            client.messages.list_scheduled()

        client.close()

    def test_list_scheduled_empty_results(self, api_key, httpx_mock: HTTPXMock):
        """Test list_scheduled with no messages"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled",
            method="GET",
            json={"data": [], "count": 0},
        )

        result = client.messages.list_scheduled()

        assert result.count == 0
        assert len(result.data) == 0

        client.close()


class TestGetScheduled:
    """Test messages.get_scheduled() method"""

    def test_get_scheduled_by_id(self, api_key, mock_scheduled_message, httpx_mock: HTTPXMock):
        """Test getting a scheduled message by ID"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled/msg_scheduled_123",
            method="GET",
            json=mock_scheduled_message,
        )

        scheduled = client.messages.get_scheduled("msg_scheduled_123")

        assert isinstance(scheduled, ScheduledMessage)
        assert scheduled.id == "msg_scheduled_123"
        assert scheduled.status.value == "scheduled"

        client.close()

    def test_get_scheduled_validation_error_empty_id(self, api_key):
        """Test get_scheduled with empty ID"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Message ID is required"):
            client.messages.get_scheduled("")

        client.close()

    def test_get_scheduled_validation_error_invalid_id(self, api_key):
        """Test get_scheduled with invalid ID format"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Invalid message ID format"):
            client.messages.get_scheduled("invalid")

        client.close()

    def test_get_scheduled_not_found_404(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        """Test get_scheduled with non-existent message"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled/msg_nonexistent",
            method="GET",
            status_code=404,
            json=mock_error_response("not_found", "Scheduled message not found"),
        )

        with pytest.raises(NotFoundError):
            client.messages.get_scheduled("msg_nonexistent")

        client.close()

    def test_get_scheduled_authentication_error_401(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test get_scheduled with authentication error"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled/msg_scheduled_123",
            method="GET",
            status_code=401,
            json=mock_error_response("unauthorized", "Invalid API key"),
        )

        with pytest.raises(AuthenticationError):
            client.messages.get_scheduled("msg_scheduled_123")

        client.close()


class TestCancelScheduled:
    """Test messages.cancel_scheduled() method"""

    def test_cancel_scheduled(self, api_key, mock_cancelled_message, httpx_mock: HTTPXMock):
        """Test cancelling a scheduled message"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled/msg_scheduled_123",
            method="DELETE",
            json=mock_cancelled_message,
        )

        cancelled = client.messages.cancel_scheduled("msg_scheduled_123")

        assert isinstance(cancelled, CancelledMessageResponse)
        assert cancelled.id == "msg_scheduled_123"
        assert cancelled.status == "cancelled"
        assert cancelled.credits_refunded == 1
        assert cancelled.cancelled_at == "2025-01-20T11:00:00Z"

        client.close()

    def test_cancel_scheduled_validation_error_empty_id(self, api_key):
        """Test cancel_scheduled with empty ID"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Message ID is required"):
            client.messages.cancel_scheduled("")

        client.close()

    def test_cancel_scheduled_validation_error_invalid_id(self, api_key):
        """Test cancel_scheduled with invalid ID format"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Invalid message ID format"):
            client.messages.cancel_scheduled("invalid")

        client.close()

    def test_cancel_scheduled_not_found_404(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test cancel_scheduled with non-existent message"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled/msg_nonexistent",
            method="DELETE",
            status_code=404,
            json=mock_error_response("not_found", "Message not found"),
        )

        with pytest.raises(NotFoundError):
            client.messages.cancel_scheduled("msg_nonexistent")

        client.close()

    def test_cancel_scheduled_authentication_error_401(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test cancel_scheduled with authentication error"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled/msg_scheduled_123",
            method="DELETE",
            status_code=401,
            json=mock_error_response("unauthorized", "Invalid API key"),
        )

        with pytest.raises(AuthenticationError):
            client.messages.cancel_scheduled("msg_scheduled_123")

        client.close()

    def test_cancel_scheduled_rate_limit_429(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test cancel_scheduled with rate limit"""
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled/msg_scheduled_123",
            method="DELETE",
            status_code=429,
            json=mock_error_response("rate_limit_exceeded", "Too many requests", retryAfter=30),
        )

        with pytest.raises(RateLimitError):
            client.messages.cancel_scheduled("msg_scheduled_123")

        client.close()

    def test_cancel_scheduled_server_error_500_with_retry(
        self, api_key, mock_cancelled_message, httpx_mock: HTTPXMock
    ):
        """Test cancel_scheduled with server error and retry"""
        client = Sendly(api_key, max_retries=1)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled/msg_scheduled_123",
            method="DELETE",
            status_code=500,
            json={"error": "internal_error", "message": "Server error"},
        )
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled/msg_scheduled_123",
            method="DELETE",
            json=mock_cancelled_message,
        )

        cancelled = client.messages.cancel_scheduled("msg_scheduled_123")

        assert cancelled.id == "msg_scheduled_123"

        client.close()
