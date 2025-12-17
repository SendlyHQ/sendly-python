"""
Tests for batch messages (send_batch, get_batch, list_batches)
"""

import pytest
from pytest_httpx import HTTPXMock

from sendly import Sendly
from sendly.errors import (
    AuthenticationError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
    SendlyError,
    ValidationError,
)
from sendly.types import BatchListResponse, BatchMessageResponse


class TestSendBatch:
    """Test messages.send_batch() method"""

    def test_send_batch_basic(self, api_key, mock_batch_response, httpx_mock: HTTPXMock):
        """Test sending a basic batch"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch",
            method="POST",
            json=mock_batch_response,
        )

        messages = [
            {"to": "+15551234567", "text": "Message 1"},
            {"to": "+15559876543", "text": "Message 2"},
        ]

        batch = client.messages.send_batch(messages=messages)

        assert isinstance(batch, BatchMessageResponse)
        assert batch.batch_id == "batch_test_123"
        assert batch.status.value == "completed"
        assert batch.total == 2
        assert batch.queued == 2
        assert batch.sent == 2
        assert batch.failed == 0
        assert len(batch.messages) == 2

        client.close()

    def test_send_batch_with_sender_id(self, api_key, mock_batch_response, httpx_mock: HTTPXMock):
        """Test sending batch with sender ID"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch",
            method="POST",
            json=mock_batch_response,
        )

        messages = [
            {"to": "+15551234567", "text": "Message 1"},
            {"to": "+15559876543", "text": "Message 2"},
        ]

        batch = client.messages.send_batch(messages=messages, from_="MyBrand")

        assert batch.batch_id == "batch_test_123"

        # Verify request body contains the sender ID
        request = httpx_mock.get_request()
        body = request.read().decode()
        assert "MyBrand" in body
        assert '"from"' in body or '"from":' in body

        client.close()

    def test_send_batch_large_batch(self, api_key, httpx_mock: HTTPXMock):
        """Test sending a large batch (100 messages)"""
        client = Sendly(api_key)

        messages = [{"to": f"+1555123{i:04d}", "text": f"Message {i}"} for i in range(100)]

        mock_response = {
            "batchId": "batch_large",
            "status": "completed",
            "total": 100,
            "queued": 100,
            "sent": 100,
            "failed": 0,
            "creditsUsed": 100,
            "messages": [
                {"id": f"msg_{i}", "to": f"+1555123{i:04d}", "status": "queued"} for i in range(100)
            ],
            "createdAt": "2025-01-20T10:00:00Z",
            "completedAt": "2025-01-20T10:00:10Z",
        }

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch",
            method="POST",
            json=mock_response,
        )

        batch = client.messages.send_batch(messages=messages)

        assert batch.total == 100
        assert len(batch.messages) == 100

        client.close()

    def test_send_batch_validation_error_empty_list(self, api_key):
        """Test send_batch with empty message list"""
        client = Sendly(api_key)

        with pytest.raises(SendlyError, match="messages must be a non-empty list"):
            client.messages.send_batch(messages=[])

        client.close()

    def test_send_batch_validation_error_not_list(self, api_key):
        """Test send_batch with non-list input"""
        client = Sendly(api_key)

        with pytest.raises(SendlyError, match="messages must be a non-empty list"):
            client.messages.send_batch(messages="not a list")

        client.close()

    def test_send_batch_validation_error_too_many_messages(self, api_key):
        """Test send_batch with more than 1000 messages"""
        client = Sendly(api_key)

        messages = [{"to": f"+1555{i:07d}", "text": f"Message {i}"} for i in range(1001)]

        with pytest.raises(SendlyError, match="Maximum 1000 messages per batch"):
            client.messages.send_batch(messages=messages)

        client.close()

    def test_send_batch_validation_error_invalid_phone(self, api_key):
        """Test send_batch with invalid phone number"""
        client = Sendly(api_key)

        messages = [
            {"to": "invalid", "text": "Message 1"},
        ]

        with pytest.raises(ValidationError, match="Invalid phone number format"):
            client.messages.send_batch(messages=messages)

        client.close()

    def test_send_batch_validation_error_empty_text(self, api_key):
        """Test send_batch with empty text"""
        client = Sendly(api_key)

        messages = [
            {"to": "+15551234567", "text": ""},
        ]

        with pytest.raises(ValidationError, match="Message text is required"):
            client.messages.send_batch(messages=messages)

        client.close()

    def test_send_batch_validation_error_invalid_sender_id(self, api_key):
        """Test send_batch with invalid sender ID"""
        client = Sendly(api_key)

        messages = [
            {"to": "+15551234567", "text": "Test"},
        ]

        with pytest.raises(ValidationError, match="Invalid sender ID"):
            client.messages.send_batch(messages=messages, from_="X")

        client.close()

    def test_send_batch_authentication_error_401(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test send_batch with authentication error"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch",
            method="POST",
            status_code=401,
            json=mock_error_response("unauthorized", "Invalid API key"),
        )

        messages = [
            {"to": "+15551234567", "text": "Test"},
        ]

        with pytest.raises(AuthenticationError):
            client.messages.send_batch(messages=messages)

        client.close()

    def test_send_batch_insufficient_credits_402(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test send_batch with insufficient credits"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch",
            method="POST",
            status_code=402,
            json=mock_error_response(
                "insufficient_credits",
                "Not enough credits",
                creditsNeeded=100,
                currentBalance=50,
            ),
        )

        messages = [
            {"to": "+15551234567", "text": "Test"},
        ]

        with pytest.raises(InsufficientCreditsError) as exc_info:
            client.messages.send_batch(messages=messages)

        assert exc_info.value.credits_needed == 100
        assert exc_info.value.current_balance == 50

        client.close()

    def test_send_batch_rate_limit_429(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        """Test send_batch with rate limit"""
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch",
            method="POST",
            status_code=429,
            json=mock_error_response("rate_limit_exceeded", "Too many requests", retryAfter=60),
        )

        messages = [
            {"to": "+15551234567", "text": "Test"},
        ]

        with pytest.raises(RateLimitError):
            client.messages.send_batch(messages=messages)

        client.close()

    def test_send_batch_server_error_500_with_retry(
        self, api_key, mock_batch_response, httpx_mock: HTTPXMock
    ):
        """Test send_batch with server error and retry"""
        client = Sendly(api_key, max_retries=1)

        messages = [
            {"to": "+15551234567", "text": "Test"},
        ]

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch",
            method="POST",
            status_code=500,
            json={"error": "internal_error", "message": "Server error"},
        )
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch",
            method="POST",
            json=mock_batch_response,
        )

        batch = client.messages.send_batch(messages=messages)

        assert batch.batch_id == "batch_test_123"

        client.close()

    def test_send_batch_partial_failure(self, api_key, httpx_mock: HTTPXMock):
        """Test send_batch with some messages failing"""
        client = Sendly(api_key)

        mock_response = {
            "batchId": "batch_partial",
            "status": "partial_failure",
            "total": 3,
            "queued": 2,
            "sent": 2,
            "failed": 1,
            "creditsUsed": 2,
            "messages": [
                {"id": "msg_1", "to": "+15551234567", "status": "queued"},
                {"id": "msg_2", "to": "+15559876543", "status": "queued"},
                {"to": "+15551111111", "status": "failed", "error": "Invalid number"},
            ],
            "createdAt": "2025-01-20T10:00:00Z",
            "completedAt": "2025-01-20T10:00:05Z",
        }

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch",
            method="POST",
            json=mock_response,
        )

        messages = [
            {"to": "+15551234567", "text": "Test 1"},
            {"to": "+15559876543", "text": "Test 2"},
            {"to": "+15551111111", "text": "Test 3"},
        ]

        batch = client.messages.send_batch(messages=messages)

        assert batch.status.value == "partial_failure"
        assert batch.failed == 1
        assert batch.queued == 2

        client.close()


class TestGetBatch:
    """Test messages.get_batch() method"""

    def test_get_batch_by_id(self, api_key, mock_batch_response, httpx_mock: HTTPXMock):
        """Test getting batch by ID"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch/batch_test_123",
            method="GET",
            json=mock_batch_response,
        )

        batch = client.messages.get_batch("batch_test_123")

        assert isinstance(batch, BatchMessageResponse)
        assert batch.batch_id == "batch_test_123"
        assert batch.status.value == "completed"

        client.close()

    def test_get_batch_validation_error_empty_id(self, api_key):
        """Test get_batch with empty batch ID"""
        client = Sendly(api_key)

        with pytest.raises(SendlyError, match="Invalid batch ID format"):
            client.messages.get_batch("")

        client.close()

    def test_get_batch_validation_error_invalid_format(self, api_key):
        """Test get_batch with invalid batch ID format"""
        client = Sendly(api_key)

        with pytest.raises(SendlyError, match="Invalid batch ID format"):
            client.messages.get_batch("invalid_id")

        with pytest.raises(SendlyError, match="Invalid batch ID format"):
            client.messages.get_batch("msg_test_123")

        client.close()

    def test_get_batch_not_found_404(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        """Test get_batch with non-existent batch"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch/batch_nonexistent",
            method="GET",
            status_code=404,
            json=mock_error_response("not_found", "Batch not found"),
        )

        with pytest.raises(NotFoundError):
            client.messages.get_batch("batch_nonexistent")

        client.close()

    def test_get_batch_authentication_error_401(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test get_batch with authentication error"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch/batch_test_123",
            method="GET",
            status_code=401,
            json=mock_error_response("unauthorized", "Invalid API key"),
        )

        with pytest.raises(AuthenticationError):
            client.messages.get_batch("batch_test_123")

        client.close()

    def test_get_batch_processing_status(self, api_key, httpx_mock: HTTPXMock):
        """Test get_batch with processing status"""
        client = Sendly(api_key)

        mock_response = {
            "batchId": "batch_processing",
            "status": "processing",
            "total": 100,
            "queued": 50,
            "sent": 30,
            "failed": 0,
            "creditsUsed": 30,
            "messages": [],
            "createdAt": "2025-01-20T10:00:00Z",
        }

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch/batch_processing",
            method="GET",
            json=mock_response,
        )

        batch = client.messages.get_batch("batch_processing")

        assert batch.status.value == "processing"
        assert batch.queued == 50
        assert batch.sent == 30

        client.close()


class TestListBatches:
    """Test messages.list_batches() method"""

    def test_list_batches_basic(self, api_key, mock_batch_list, httpx_mock: HTTPXMock):
        """Test listing batches"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batches",
            method="GET",
            json=mock_batch_list,
        )

        result = client.messages.list_batches()

        assert isinstance(result, BatchListResponse)
        assert result.count == 1
        assert len(result.data) == 1
        assert result.data[0].batch_id == "batch_1"

        client.close()

    def test_list_batches_with_limit(self, api_key, mock_batch_list, httpx_mock: HTTPXMock):
        """Test listing batches with limit"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batches?limit=10",
            method="GET",
            json=mock_batch_list,
        )

        result = client.messages.list_batches(limit=10)

        assert result.count == 1
        request = httpx_mock.get_request()
        assert "limit=10" in str(request.url)

        client.close()

    def test_list_batches_with_offset(self, api_key, mock_batch_list, httpx_mock: HTTPXMock):
        """Test listing batches with offset"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batches?offset=5",
            method="GET",
            json=mock_batch_list,
        )

        result = client.messages.list_batches(offset=5)

        assert result.count == 1
        request = httpx_mock.get_request()
        assert "offset=5" in str(request.url)

        client.close()

    def test_list_batches_with_status_filter(self, api_key, mock_batch_list, httpx_mock: HTTPXMock):
        """Test listing batches with status filter"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batches?status=completed",
            method="GET",
            json=mock_batch_list,
        )

        result = client.messages.list_batches(status="completed")

        assert result.count == 1
        request = httpx_mock.get_request()
        assert "status=completed" in str(request.url)

        client.close()

    def test_list_batches_with_all_params(self, api_key, mock_batch_list, httpx_mock: HTTPXMock):
        """Test listing batches with all parameters"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batches?limit=20&offset=10&status=completed",
            method="GET",
            json=mock_batch_list,
        )

        result = client.messages.list_batches(limit=20, offset=10, status="completed")

        assert result.count == 1

        client.close()

    def test_list_batches_validation_error_limit(self, api_key):
        """Test list_batches with invalid limit"""
        client = Sendly(api_key)

        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            client.messages.list_batches(limit=0)

        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            client.messages.list_batches(limit=101)

        client.close()

    def test_list_batches_authentication_error_401(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test list_batches with authentication error"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batches",
            method="GET",
            status_code=401,
            json=mock_error_response("unauthorized", "Invalid API key"),
        )

        with pytest.raises(AuthenticationError):
            client.messages.list_batches()

        client.close()

    def test_list_batches_empty_results(self, api_key, httpx_mock: HTTPXMock):
        """Test list_batches with no batches"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batches",
            method="GET",
            json={"data": [], "count": 0},
        )

        result = client.messages.list_batches()

        assert result.count == 0
        assert len(result.data) == 0

        client.close()

    def test_list_batches_rate_limit_429(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        """Test list_batches with rate limit"""
        client = Sendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batches",
            method="GET",
            status_code=429,
            json=mock_error_response("rate_limit_exceeded", "Too many requests", retryAfter=30),
        )

        with pytest.raises(RateLimitError):
            client.messages.list_batches()

        client.close()
