"""
Pytest configuration and fixtures for Sendly SDK tests
"""

import pytest
from pytest_httpx import HTTPXMock


@pytest.fixture
def api_key():
    """Test API key"""
    return "sk_test_v1_test_key_123"


@pytest.fixture
def live_api_key():
    """Live API key for testing"""
    return "sk_live_v1_live_key_456"


@pytest.fixture
def base_url():
    """Base URL for API"""
    return "https://sendly.live/api/v1"


@pytest.fixture
def mock_message():
    """Mock message response"""
    return {
        "id": "msg_test_123",
        "to": "+15551234567",
        "from": "Sendly",
        "text": "Test message",
        "status": "queued",
        "segments": 1,
        "creditsUsed": 1,
        "isSandbox": True,
        "createdAt": "2025-01-20T10:00:00Z",
    }


@pytest.fixture
def mock_message_list():
    """Mock message list response"""
    return {
        "data": [
            {
                "id": "msg_test_1",
                "to": "+15551234567",
                "from": "Sendly",
                "text": "Message 1",
                "status": "delivered",
                "segments": 1,
                "creditsUsed": 1,
                "isSandbox": True,
                "createdAt": "2025-01-20T10:00:00Z",
            },
            {
                "id": "msg_test_2",
                "to": "+15559876543",
                "from": "Sendly",
                "text": "Message 2",
                "status": "queued",
                "segments": 1,
                "creditsUsed": 1,
                "isSandbox": True,
                "createdAt": "2025-01-20T10:01:00Z",
            },
        ],
        "count": 2,
    }


@pytest.fixture
def mock_scheduled_message():
    """Mock scheduled message response"""
    return {
        "id": "msg_scheduled_123",
        "to": "+15551234567",
        "from": "Sendly",
        "text": "Scheduled message",
        "status": "scheduled",
        "scheduledAt": "2025-01-21T10:00:00Z",
        "creditsReserved": 1,
        "createdAt": "2025-01-20T10:00:00Z",
    }


@pytest.fixture
def mock_scheduled_list():
    """Mock scheduled message list response"""
    return {
        "data": [
            {
                "id": "msg_scheduled_1",
                "to": "+15551234567",
                "from": "Sendly",
                "text": "Scheduled 1",
                "status": "scheduled",
                "scheduledAt": "2025-01-21T10:00:00Z",
                "creditsReserved": 1,
                "createdAt": "2025-01-20T10:00:00Z",
            },
        ],
        "count": 1,
    }


@pytest.fixture
def mock_cancelled_message():
    """Mock cancelled message response"""
    return {
        "id": "msg_scheduled_123",
        "status": "cancelled",
        "creditsRefunded": 1,
        "cancelledAt": "2025-01-20T11:00:00Z",
    }


@pytest.fixture
def mock_batch_response():
    """Mock batch response"""
    return {
        "batchId": "batch_test_123",
        "status": "completed",
        "total": 2,
        "queued": 2,
        "sent": 2,
        "failed": 0,
        "creditsUsed": 2,
        "messages": [
            {
                "id": "msg_batch_1",
                "to": "+15551234567",
                "status": "queued",
            },
            {
                "id": "msg_batch_2",
                "to": "+15559876543",
                "status": "queued",
            },
        ],
        "createdAt": "2025-01-20T10:00:00Z",
        "completedAt": "2025-01-20T10:00:05Z",
    }


@pytest.fixture
def mock_batch_list():
    """Mock batch list response"""
    return {
        "data": [
            {
                "batchId": "batch_1",
                "status": "completed",
                "total": 2,
                "queued": 2,
                "sent": 2,
                "failed": 0,
                "creditsUsed": 2,
                "messages": [],
                "createdAt": "2025-01-20T10:00:00Z",
                "completedAt": "2025-01-20T10:00:05Z",
            },
        ],
        "count": 1,
    }


@pytest.fixture
def mock_error_response():
    """Mock error response"""

    def _error(code, message, **kwargs):
        return {
            "error": code,
            "message": message,
            **kwargs,
        }

    return _error


@pytest.fixture
def mock_rate_limit_headers():
    """Mock rate limit headers"""
    return {
        "X-RateLimit-Limit": "100",
        "X-RateLimit-Remaining": "99",
        "X-RateLimit-Reset": "60",
    }
