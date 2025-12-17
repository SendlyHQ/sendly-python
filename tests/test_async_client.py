"""
Tests for AsyncSendly client and async methods
"""

import pytest
from pytest_httpx import HTTPXMock

from sendly import AsyncSendly
from sendly.errors import (
    AuthenticationError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from sendly.types import (
    BatchMessageResponse,
    CancelledMessageResponse,
    Message,
    MessageListResponse,
    ScheduledMessage,
)


class TestAsyncClientInitialization:
    """Test async client initialization"""

    @pytest.mark.asyncio
    async def test_basic_initialization(self, api_key):
        """Test basic async client initialization"""
        client = AsyncSendly(api_key)
        assert client._api_key == api_key
        assert client.is_test_mode() is True
        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self, api_key):
        """Test async client as context manager"""
        async with AsyncSendly(api_key) as client:
            assert client._api_key == api_key
            assert client.messages is not None

    @pytest.mark.asyncio
    async def test_initialization_without_api_key(self):
        """Test that initialization fails without API key"""
        with pytest.raises(ValueError, match="api_key is required"):
            AsyncSendly()

    @pytest.mark.asyncio
    async def test_is_test_mode(self, api_key, live_api_key):
        """Test is_test_mode() method"""
        test_client = AsyncSendly(api_key)
        assert test_client.is_test_mode() is True
        await test_client.close()

        live_client = AsyncSendly(live_api_key)
        assert live_client.is_test_mode() is False
        await live_client.close()


class TestAsyncMessagesSend:
    """Test async messages.send() method"""

    @pytest.mark.asyncio
    async def test_send_basic_message(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test sending a basic SMS message asynchronously"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_message,
        )

        message = await client.messages.send(to="+15551234567", text="Test message")

        assert isinstance(message, Message)
        assert message.id == "msg_test_123"
        assert message.to == "+15551234567"

        await client.close()

    @pytest.mark.asyncio
    async def test_send_with_sender_id(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test sending message with sender ID"""
        client = AsyncSendly(api_key)

        mock_message["from"] = "MyBrand"
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_message,
        )

        message = await client.messages.send(
            to="+15551234567",
            text="Test",
            from_="MyBrand",
        )

        assert message.from_ == "MyBrand"

        await client.close()

    @pytest.mark.asyncio
    async def test_send_validation_error_invalid_phone(self, api_key):
        """Test send with invalid phone number"""
        client = AsyncSendly(api_key)

        with pytest.raises(ValidationError, match="Invalid phone number format"):
            await client.messages.send(to="invalid", text="Test")

        await client.close()

    @pytest.mark.asyncio
    async def test_send_authentication_error_401(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test send with authentication error"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=401,
            json=mock_error_response("unauthorized", "Invalid API key"),
        )

        with pytest.raises(AuthenticationError):
            await client.messages.send(to="+15551234567", text="Test")

        await client.close()

    @pytest.mark.asyncio
    async def test_send_insufficient_credits_402(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test send with insufficient credits"""
        client = AsyncSendly(api_key)

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
            await client.messages.send(to="+15551234567", text="Test")

        assert exc_info.value.credits_needed == 10

        await client.close()

    @pytest.mark.asyncio
    async def test_send_rate_limit_429(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        """Test send with rate limit"""
        client = AsyncSendly(api_key, max_retries=0)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=429,
            json=mock_error_response("rate_limit_exceeded", "Too many requests", retryAfter=60),
        )

        with pytest.raises(RateLimitError):
            await client.messages.send(to="+15551234567", text="Test")

        await client.close()

    @pytest.mark.asyncio
    async def test_send_server_error_500_with_retry(
        self, api_key, mock_message, httpx_mock: HTTPXMock
    ):
        """Test send with server error and retry"""
        client = AsyncSendly(api_key, max_retries=1)

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

        message = await client.messages.send(to="+15551234567", text="Test")

        assert message.id == "msg_test_123"

        await client.close()


class TestAsyncMessagesList:
    """Test async messages.list() method"""

    @pytest.mark.asyncio
    async def test_list_basic(self, api_key, mock_message_list, httpx_mock: HTTPXMock):
        """Test listing messages"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="GET",
            json=mock_message_list,
        )

        result = await client.messages.list()

        assert isinstance(result, MessageListResponse)
        assert result.count == 2
        assert len(result.data) == 2

        await client.close()

    @pytest.mark.asyncio
    async def test_list_with_limit(self, api_key, mock_message_list, httpx_mock: HTTPXMock):
        """Test listing with limit"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages?limit=10",
            method="GET",
            json=mock_message_list,
        )

        result = await client.messages.list(limit=10)

        assert result.count == 2

        await client.close()

    @pytest.mark.asyncio
    async def test_list_validation_error_limit(self, api_key):
        """Test list with invalid limit"""
        client = AsyncSendly(api_key)

        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            await client.messages.list(limit=0)

        await client.close()

    @pytest.mark.asyncio
    async def test_list_authentication_error_401(
        self, api_key, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test list with authentication error"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="GET",
            status_code=401,
            json=mock_error_response("unauthorized", "Invalid API key"),
        )

        with pytest.raises(AuthenticationError):
            await client.messages.list()

        await client.close()


class TestAsyncMessagesGet:
    """Test async messages.get() method"""

    @pytest.mark.asyncio
    async def test_get_by_id(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test getting message by ID"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/msg_test_123",
            method="GET",
            json=mock_message,
        )

        message = await client.messages.get("msg_test_123")

        assert isinstance(message, Message)
        assert message.id == "msg_test_123"

        await client.close()

    @pytest.mark.asyncio
    async def test_get_validation_error_empty_id(self, api_key):
        """Test get with empty ID"""
        client = AsyncSendly(api_key)

        with pytest.raises(ValidationError, match="Message ID is required"):
            await client.messages.get("")

        await client.close()

    @pytest.mark.asyncio
    async def test_get_not_found_404(self, api_key, mock_error_response, httpx_mock: HTTPXMock):
        """Test get with non-existent message"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/msg_nonexistent",
            method="GET",
            status_code=404,
            json=mock_error_response("not_found", "Message not found"),
        )

        with pytest.raises(NotFoundError):
            await client.messages.get("msg_nonexistent")

        await client.close()


class TestAsyncMessagesListAll:
    """Test async messages.list_all() generator"""

    @pytest.mark.asyncio
    async def test_list_all_single_page(self, api_key, httpx_mock: HTTPXMock):
        """Test list_all with single page"""
        client = AsyncSendly(api_key)

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

        messages = []
        async for message in client.messages.list_all():
            messages.append(message)

        assert len(messages) == 50
        assert messages[0].id == "msg_0"

        await client.close()

    @pytest.mark.asyncio
    async def test_list_all_multiple_pages(self, api_key, httpx_mock: HTTPXMock):
        """Test list_all with pagination"""
        client = AsyncSendly(api_key)

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

        messages = []
        async for message in client.messages.list_all():
            messages.append(message)

        assert len(messages) == 150

        await client.close()


class TestAsyncScheduledMessages:
    """Test async scheduled messages methods"""

    @pytest.mark.asyncio
    async def test_schedule(self, api_key, mock_scheduled_message, httpx_mock: HTTPXMock):
        """Test scheduling a message"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/schedule",
            method="POST",
            json=mock_scheduled_message,
        )

        scheduled = await client.messages.schedule(
            to="+15551234567",
            text="Scheduled message",
            scheduled_at="2025-01-21T10:00:00Z",
        )

        assert isinstance(scheduled, ScheduledMessage)
        assert scheduled.id == "msg_scheduled_123"

        await client.close()

    @pytest.mark.asyncio
    async def test_list_scheduled(self, api_key, mock_scheduled_list, httpx_mock: HTTPXMock):
        """Test listing scheduled messages"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled",
            method="GET",
            json=mock_scheduled_list,
        )

        result = await client.messages.list_scheduled()

        assert result.count == 1
        assert len(result.data) == 1

        await client.close()

    @pytest.mark.asyncio
    async def test_get_scheduled(self, api_key, mock_scheduled_message, httpx_mock: HTTPXMock):
        """Test getting scheduled message"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled/msg_scheduled_123",
            method="GET",
            json=mock_scheduled_message,
        )

        scheduled = await client.messages.get_scheduled("msg_scheduled_123")

        assert scheduled.id == "msg_scheduled_123"

        await client.close()

    @pytest.mark.asyncio
    async def test_cancel_scheduled(self, api_key, mock_cancelled_message, httpx_mock: HTTPXMock):
        """Test cancelling scheduled message"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/scheduled/msg_scheduled_123",
            method="DELETE",
            json=mock_cancelled_message,
        )

        cancelled = await client.messages.cancel_scheduled("msg_scheduled_123")

        assert isinstance(cancelled, CancelledMessageResponse)
        assert cancelled.id == "msg_scheduled_123"
        assert cancelled.status == "cancelled"

        await client.close()


class TestAsyncBatchMessages:
    """Test async batch messages methods"""

    @pytest.mark.asyncio
    async def test_send_batch(self, api_key, mock_batch_response, httpx_mock: HTTPXMock):
        """Test sending batch messages"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch",
            method="POST",
            json=mock_batch_response,
        )

        messages = [
            {"to": "+15551234567", "text": "Message 1"},
            {"to": "+15559876543", "text": "Message 2"},
        ]

        batch = await client.messages.send_batch(messages=messages)

        assert isinstance(batch, BatchMessageResponse)
        assert batch.batch_id == "batch_test_123"
        assert batch.total == 2

        await client.close()

    @pytest.mark.asyncio
    async def test_get_batch(self, api_key, mock_batch_response, httpx_mock: HTTPXMock):
        """Test getting batch status"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batch/batch_test_123",
            method="GET",
            json=mock_batch_response,
        )

        batch = await client.messages.get_batch("batch_test_123")

        assert batch.batch_id == "batch_test_123"

        await client.close()

    @pytest.mark.asyncio
    async def test_list_batches(self, api_key, mock_batch_list, httpx_mock: HTTPXMock):
        """Test listing batches"""
        client = AsyncSendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages/batches",
            method="GET",
            json=mock_batch_list,
        )

        result = await client.messages.list_batches()

        assert result.count == 1

        await client.close()


class TestAsyncErrorHandling:
    """Test async error handling and retries"""

    @pytest.mark.asyncio
    async def test_network_error_with_retry(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test network error with successful retry"""
        import httpx

        client = AsyncSendly(api_key, max_retries=1)

        httpx_mock.add_exception(httpx.RequestError("Network error"))
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_message,
        )

        message = await client.messages.send(to="+15551234567", text="Test")

        assert message.id == "msg_test_123"

        await client.close()

    @pytest.mark.asyncio
    async def test_rate_limit_with_retry_after(
        self, api_key, mock_message, mock_error_response, httpx_mock: HTTPXMock
    ):
        """Test rate limit with Retry-After header"""
        client = AsyncSendly(api_key, max_retries=1)

        # This will fail on first attempt due to max_retries=1
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            status_code=429,
            json=mock_error_response("rate_limit_exceeded", "Too many requests", retryAfter=1),
        )
        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_message,
        )

        message = await client.messages.send(to="+15551234567", text="Test")

        assert message.id == "msg_test_123"

        await client.close()

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, api_key, mock_message, httpx_mock: HTTPXMock):
        """Test making concurrent requests"""
        import asyncio

        client = AsyncSendly(api_key)

        # Add multiple responses
        for i in range(5):
            mock_msg = mock_message.copy()
            mock_msg["id"] = f"msg_test_{i}"
            httpx_mock.add_response(
                url="https://sendly.live/api/v1/messages",
                method="POST",
                json=mock_msg,
            )

        # Send 5 messages concurrently
        tasks = [client.messages.send(to="+15551234567", text=f"Test {i}") for i in range(5)]
        messages = await asyncio.gather(*tasks)

        assert len(messages) == 5

        await client.close()
