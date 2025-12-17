"""
Tests for Sendly client initialization and configuration
"""

import pytest
from pytest_httpx import HTTPXMock

from sendly import Sendly
from sendly.client import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from sendly.errors import ValidationError
from sendly.types import SendlyConfig


class TestClientInitialization:
    """Test client initialization scenarios"""

    def test_basic_initialization(self, api_key):
        """Test basic client initialization with API key"""
        client = Sendly(api_key)
        assert client._api_key == api_key
        assert client._base_url == DEFAULT_BASE_URL
        assert client._timeout == DEFAULT_TIMEOUT
        assert client._max_retries == DEFAULT_MAX_RETRIES
        client.close()

    def test_initialization_with_custom_config(self, api_key):
        """Test client initialization with custom configuration"""
        client = Sendly(
            api_key,
            base_url="https://custom.api.url",
            timeout=60.0,
            max_retries=5,
        )
        assert client._api_key == api_key
        assert client._base_url == "https://custom.api.url"
        assert client._timeout == 60.0
        assert client._max_retries == 5
        client.close()

    def test_initialization_with_config_object(self, api_key):
        """Test client initialization with SendlyConfig object"""
        config = SendlyConfig(
            api_key=api_key,
            base_url="https://custom.api.url",
            timeout=45.0,
            max_retries=4,
        )
        client = Sendly(config=config)
        assert client._api_key == api_key
        assert client._base_url == "https://custom.api.url"
        assert client._timeout == 45.0
        assert client._max_retries == 4
        client.close()

    def test_initialization_without_api_key(self):
        """Test that initialization fails without API key"""
        with pytest.raises(ValueError, match="api_key is required"):
            Sendly()

    def test_initialization_with_invalid_api_key_format(self):
        """Test that initialization fails with invalid API key format"""
        with pytest.raises(ValueError, match="Invalid API key format"):
            Sendly("invalid_key")

        with pytest.raises(ValueError, match="Invalid API key format"):
            Sendly("sk_wrong_v1_key")

        with pytest.raises(ValueError, match="Invalid API key format"):
            Sendly("random_string")

    def test_context_manager(self, api_key):
        """Test client works as context manager"""
        with Sendly(api_key) as client:
            assert client._api_key == api_key
            assert client.messages is not None

    def test_is_test_mode_with_test_key(self, api_key):
        """Test is_test_mode() returns True for test keys"""
        client = Sendly(api_key)
        assert client.is_test_mode() is True
        client.close()

    def test_is_test_mode_with_live_key(self, live_api_key):
        """Test is_test_mode() returns False for live keys"""
        client = Sendly(live_api_key)
        assert client.is_test_mode() is False
        client.close()

    def test_base_url_property(self, api_key):
        """Test base_url property"""
        client = Sendly(api_key, base_url="https://custom.url")
        assert client.base_url == "https://custom.url"
        client.close()

    def test_base_url_strips_trailing_slash(self, api_key):
        """Test that base URL trailing slash is stripped in HTTP client"""
        client = Sendly(api_key, base_url="https://api.url/")
        # Client stores URL as-is, but HTTP client strips it
        assert client._base_url == "https://api.url/"
        assert client._http.base_url == "https://api.url"
        client.close()

    def test_get_rate_limit_info_initially_none(self, api_key):
        """Test get_rate_limit_info() returns None before any requests"""
        client = Sendly(api_key)
        assert client.get_rate_limit_info() is None
        client.close()

    def test_messages_resource_initialized(self, api_key):
        """Test that messages resource is properly initialized"""
        client = Sendly(api_key)
        assert client.messages is not None
        assert hasattr(client.messages, "send")
        assert hasattr(client.messages, "list")
        assert hasattr(client.messages, "get")
        client.close()

    def test_close_method(self, api_key):
        """Test close method properly closes HTTP client"""
        client = Sendly(api_key)
        client.close()
        # Should be able to close multiple times without error
        client.close()

    def test_client_with_zero_timeout(self, api_key):
        """Test client with zero timeout"""
        client = Sendly(api_key, timeout=0.0)
        assert client._timeout == 0.0
        client.close()

    def test_client_with_zero_retries(self, api_key):
        """Test client with zero retries"""
        client = Sendly(api_key, max_retries=0)
        assert client._max_retries == 0
        client.close()

    def test_http_client_has_correct_headers(self, api_key):
        """Test HTTP client is initialized with correct headers"""
        client = Sendly(api_key)
        headers = client._http._build_headers()
        assert headers["Authorization"] == f"Bearer {api_key}"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "User-Agent" in headers
        assert "sendly-python" in headers["User-Agent"]
        client.close()

    def test_rate_limit_info_after_request(
        self, api_key, mock_message, mock_rate_limit_headers, httpx_mock: HTTPXMock
    ):
        """Test get_rate_limit_info() returns info after request"""
        client = Sendly(api_key)

        httpx_mock.add_response(
            url="https://sendly.live/api/v1/messages",
            method="POST",
            json=mock_message,
            headers=mock_rate_limit_headers,
        )

        client.messages.send(to="+15551234567", text="Test")

        rate_limit = client.get_rate_limit_info()
        assert rate_limit is not None
        assert rate_limit.limit == 100
        assert rate_limit.remaining == 99
        assert rate_limit.reset == 60

        client.close()


class TestClientEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_api_key(self):
        """Test empty API key raises error"""
        with pytest.raises(ValueError):
            Sendly("")

    def test_none_api_key(self):
        """Test None API key raises error"""
        with pytest.raises(ValueError):
            Sendly(None)

    def test_api_key_with_spaces(self):
        """Test API key with spaces raises error"""
        with pytest.raises(ValueError):
            Sendly("sk_test_v1_key with spaces")

    def test_negative_timeout(self, api_key):
        """Test negative timeout is accepted (httpx will handle it)"""
        client = Sendly(api_key, timeout=-1.0)
        assert client._timeout == -1.0
        client.close()

    def test_negative_max_retries(self, api_key):
        """Test negative max_retries is accepted"""
        client = Sendly(api_key, max_retries=-1)
        assert client._max_retries == -1
        client.close()

    def test_very_large_timeout(self, api_key):
        """Test very large timeout value"""
        client = Sendly(api_key, timeout=99999.0)
        assert client._timeout == 99999.0
        client.close()

    def test_very_large_max_retries(self, api_key):
        """Test very large max_retries value"""
        client = Sendly(api_key, max_retries=999)
        assert client._max_retries == 999
        client.close()

    def test_base_url_without_protocol(self, api_key):
        """Test base URL without protocol"""
        client = Sendly(api_key, base_url="api.sendly.live")
        assert client._base_url == "api.sendly.live"
        client.close()

    def test_base_url_with_port(self, api_key):
        """Test base URL with port number"""
        client = Sendly(api_key, base_url="https://api.sendly.live:8080")
        assert client._base_url == "https://api.sendly.live:8080"
        client.close()

    def test_base_url_with_path(self, api_key):
        """Test base URL with path"""
        client = Sendly(api_key, base_url="https://api.sendly.live/v2")
        assert client._base_url == "https://api.sendly.live/v2"
        client.close()

    def test_multiple_client_instances(self, api_key):
        """Test creating multiple client instances"""
        client1 = Sendly(api_key)
        client2 = Sendly(api_key)

        assert client1._api_key == client2._api_key
        assert client1 is not client2
        assert client1.messages is not client2.messages

        client1.close()
        client2.close()

    def test_config_object_overrides_direct_params(self, api_key):
        """Test that config object takes precedence over direct params"""
        config = SendlyConfig(
            api_key="sk_test_v1_config_key",
            base_url="https://config.url",
        )
        # Direct params should be ignored when config is provided
        client = Sendly(
            api_key=api_key,
            base_url="https://direct.url",
            config=config,
        )
        assert client._api_key == "sk_test_v1_config_key"
        assert client._base_url == "https://config.url"
        client.close()
