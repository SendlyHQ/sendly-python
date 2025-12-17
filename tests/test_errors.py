"""
Tests for error classes and error handling
"""

import pytest

from sendly.errors import (
    AuthenticationError,
    InsufficientCreditsError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    SendlyError,
    TimeoutError,
    ValidationError,
)
from sendly.types import ApiErrorResponse


class TestSendlyError:
    """Test base SendlyError class"""

    def test_basic_error(self):
        """Test basic error creation"""
        error = SendlyError("Test error", code="test_code", status_code=400)

        assert error.message == "Test error"
        assert error.code == "test_code"
        assert error.status_code == 400
        assert str(error) == "[test_code] (400) Test error"

    def test_error_without_status_code(self):
        """Test error without status code"""
        error = SendlyError("Test error", code="test_code")

        assert error.status_code is None
        assert str(error) == "[test_code] Test error"

    def test_error_repr(self):
        """Test error __repr__"""
        error = SendlyError("Test error", code="test_code")

        assert repr(error) == "SendlyError(code='test_code', message='Test error')"

    def test_error_with_response(self):
        """Test error with response object"""
        response = ApiErrorResponse(error="test_error", message="Test message")
        error = SendlyError("Test error", code="test_code", response=response)

        assert error.response == response
        assert error.response.error == "test_error"

    def test_error_from_response_unauthorized(self):
        """Test creating error from unauthorized response"""
        response_data = {
            "error": "unauthorized",
            "message": "Invalid API key",
        }

        error = SendlyError.from_response(401, response_data)

        assert isinstance(error, AuthenticationError)
        assert error.code == "unauthorized"
        assert error.message == "Invalid API key"
        assert error.status_code == 401

    def test_error_from_response_rate_limit(self):
        """Test creating error from rate limit response"""
        response_data = {
            "error": "rate_limit_exceeded",
            "message": "Too many requests",
            "retryAfter": 60,
        }

        error = SendlyError.from_response(429, response_data)

        assert isinstance(error, RateLimitError)
        assert error.retry_after == 60

    def test_error_from_response_insufficient_credits(self):
        """Test creating error from insufficient credits response"""
        response_data = {
            "error": "insufficient_credits",
            "message": "Not enough credits",
            "creditsNeeded": 10,
            "currentBalance": 5,
        }

        error = SendlyError.from_response(402, response_data)

        assert isinstance(error, InsufficientCreditsError)
        assert error.credits_needed == 10
        assert error.current_balance == 5

    def test_error_from_response_validation_error(self):
        """Test creating error from validation error response"""
        response_data = {
            "error": "invalid_request",
            "message": "Invalid phone number",
        }

        error = SendlyError.from_response(400, response_data)

        assert isinstance(error, ValidationError)

    def test_error_from_response_not_found(self):
        """Test creating error from not found response"""
        response_data = {
            "error": "not_found",
            "message": "Message not found",
        }

        error = SendlyError.from_response(404, response_data)

        assert isinstance(error, NotFoundError)

    def test_error_from_response_generic(self):
        """Test creating generic error from response"""
        response_data = {
            "error": "some_other_error",
            "message": "Some error occurred",
        }

        error = SendlyError.from_response(500, response_data)

        assert isinstance(error, SendlyError)
        assert not isinstance(error, AuthenticationError)
        assert error.code == "some_other_error"

    def test_error_from_response_invalid_data(self):
        """Test creating error from invalid response data"""
        response_data = {"invalid": "data"}

        error = SendlyError.from_response(500, response_data)

        assert isinstance(error, SendlyError)
        assert error.code == "internal_error"


class TestAuthenticationError:
    """Test AuthenticationError class"""

    def test_basic_authentication_error(self):
        """Test basic authentication error"""
        error = AuthenticationError("Invalid API key")

        assert error.message == "Invalid API key"
        assert error.code == "unauthorized"
        assert isinstance(error, SendlyError)

    def test_authentication_error_with_custom_code(self):
        """Test authentication error with custom code"""
        error = AuthenticationError("Key expired", code="key_expired", status_code=401)

        assert error.code == "key_expired"
        assert error.status_code == 401

    def test_authentication_error_codes(self):
        """Test various authentication error codes"""
        codes = [
            "unauthorized",
            "invalid_auth_format",
            "invalid_key_format",
            "invalid_api_key",
            "key_revoked",
            "key_expired",
            "insufficient_permissions",
        ]

        for code in codes:
            response_data = {"error": code, "message": f"Error: {code}"}
            error = SendlyError.from_response(401, response_data)

            assert isinstance(error, AuthenticationError)
            assert error.code == code


class TestRateLimitError:
    """Test RateLimitError class"""

    def test_basic_rate_limit_error(self):
        """Test basic rate limit error"""
        error = RateLimitError("Too many requests", retry_after=60)

        assert error.message == "Too many requests"
        assert error.code == "rate_limit_exceeded"
        assert error.retry_after == 60

    def test_rate_limit_error_with_status_code(self):
        """Test rate limit error with status code"""
        error = RateLimitError("Rate limited", retry_after=30, status_code=429)

        assert error.status_code == 429
        assert error.retry_after == 30

    def test_rate_limit_error_from_response(self):
        """Test creating rate limit error from response"""
        response_data = {
            "error": "rate_limit_exceeded",
            "message": "Rate limit exceeded",
            "retryAfter": 120,
        }

        error = SendlyError.from_response(429, response_data)

        assert isinstance(error, RateLimitError)
        assert error.retry_after == 120

    def test_rate_limit_error_default_retry_after(self):
        """Test rate limit error with default retry_after"""
        response_data = {
            "error": "rate_limit_exceeded",
            "message": "Rate limit exceeded",
            # No retryAfter
        }

        error = SendlyError.from_response(429, response_data)

        assert isinstance(error, RateLimitError)
        assert error.retry_after == 60  # Default


class TestInsufficientCreditsError:
    """Test InsufficientCreditsError class"""

    def test_basic_insufficient_credits_error(self):
        """Test basic insufficient credits error"""
        error = InsufficientCreditsError(
            "Not enough credits",
            credits_needed=10,
            current_balance=5,
        )

        assert error.message == "Not enough credits"
        assert error.code == "insufficient_credits"
        assert error.credits_needed == 10
        assert error.current_balance == 5

    def test_insufficient_credits_error_with_status_code(self):
        """Test insufficient credits error with status code"""
        error = InsufficientCreditsError(
            "Insufficient balance",
            credits_needed=100,
            current_balance=50,
            status_code=402,
        )

        assert error.status_code == 402

    def test_insufficient_credits_error_from_response(self):
        """Test creating insufficient credits error from response"""
        response_data = {
            "error": "insufficient_credits",
            "message": "Not enough credits",
            "creditsNeeded": 25,
            "currentBalance": 10,
        }

        error = SendlyError.from_response(402, response_data)

        assert isinstance(error, InsufficientCreditsError)
        assert error.credits_needed == 25
        assert error.current_balance == 10

    def test_insufficient_credits_error_default_values(self):
        """Test insufficient credits error with default values"""
        response_data = {
            "error": "insufficient_credits",
            "message": "Not enough credits",
            # No creditsNeeded or currentBalance
        }

        error = SendlyError.from_response(402, response_data)

        assert isinstance(error, InsufficientCreditsError)
        assert error.credits_needed == 0
        assert error.current_balance == 0


class TestValidationError:
    """Test ValidationError class"""

    def test_basic_validation_error(self):
        """Test basic validation error"""
        error = ValidationError("Invalid input")

        assert error.message == "Invalid input"
        assert error.code == "invalid_request"

    def test_validation_error_with_custom_code(self):
        """Test validation error with custom code"""
        error = ValidationError(
            "Unsupported destination",
            code="unsupported_destination",
            status_code=400,
        )

        assert error.code == "unsupported_destination"

    def test_validation_error_codes(self):
        """Test various validation error codes"""
        codes = ["invalid_request", "unsupported_destination"]

        for code in codes:
            response_data = {"error": code, "message": f"Error: {code}"}
            error = SendlyError.from_response(400, response_data)

            assert isinstance(error, ValidationError)
            assert error.code == code


class TestNotFoundError:
    """Test NotFoundError class"""

    def test_basic_not_found_error(self):
        """Test basic not found error"""
        error = NotFoundError("Resource not found")

        assert error.message == "Resource not found"
        assert error.code == "not_found"

    def test_not_found_error_with_status_code(self):
        """Test not found error with status code"""
        error = NotFoundError("Message not found", status_code=404)

        assert error.status_code == 404

    def test_not_found_error_from_response(self):
        """Test creating not found error from response"""
        response_data = {
            "error": "not_found",
            "message": "Message not found",
        }

        error = SendlyError.from_response(404, response_data)

        assert isinstance(error, NotFoundError)


class TestNetworkError:
    """Test NetworkError class"""

    def test_basic_network_error(self):
        """Test basic network error"""
        error = NetworkError("Connection failed")

        assert error.message == "Connection failed"
        assert error.code == "internal_error"

    def test_network_error_with_cause(self):
        """Test network error with cause"""
        cause = Exception("Underlying error")
        error = NetworkError("Connection failed", cause=cause)

        assert error.cause == cause


class TestTimeoutError:
    """Test TimeoutError class"""

    def test_basic_timeout_error(self):
        """Test basic timeout error"""
        error = TimeoutError()

        assert error.message == "Request timed out"
        assert error.code == "internal_error"

    def test_timeout_error_with_custom_message(self):
        """Test timeout error with custom message"""
        error = TimeoutError("Custom timeout message")

        assert error.message == "Custom timeout message"


class TestErrorInheritance:
    """Test error class inheritance"""

    def test_all_errors_inherit_from_sendly_error(self):
        """Test that all error classes inherit from SendlyError"""
        errors = [
            AuthenticationError("test"),
            RateLimitError("test", retry_after=60),
            InsufficientCreditsError("test", credits_needed=1, current_balance=0),
            ValidationError("test"),
            NotFoundError("test"),
            NetworkError("test"),
            TimeoutError("test"),
        ]

        for error in errors:
            assert isinstance(error, SendlyError)
            assert isinstance(error, Exception)

    def test_all_errors_inherit_from_exception(self):
        """Test that all errors can be caught as Exception"""
        errors = [
            AuthenticationError("test"),
            RateLimitError("test", retry_after=60),
            InsufficientCreditsError("test", credits_needed=1, current_balance=0),
            ValidationError("test"),
            NotFoundError("test"),
            NetworkError("test"),
            TimeoutError("test"),
        ]

        for error in errors:
            try:
                raise error
            except Exception as e:
                assert isinstance(e, Exception)


class TestErrorAttributes:
    """Test error attributes and properties"""

    def test_error_message_attribute(self):
        """Test that all errors have message attribute"""
        errors = [
            SendlyError("msg", code="code"),
            AuthenticationError("msg"),
            RateLimitError("msg", retry_after=60),
            InsufficientCreditsError("msg", credits_needed=1, current_balance=0),
            ValidationError("msg"),
            NotFoundError("msg"),
            NetworkError("msg"),
            TimeoutError("msg"),
        ]

        for error in errors:
            assert hasattr(error, "message")
            assert error.message == "msg"

    def test_error_code_attribute(self):
        """Test that all errors have code attribute"""
        errors = [
            SendlyError("msg", code="test_code"),
            AuthenticationError("msg", code="auth_code"),
            RateLimitError("msg", retry_after=60),
            InsufficientCreditsError("msg", credits_needed=1, current_balance=0),
            ValidationError("msg", code="validation_code"),
            NotFoundError("msg"),
            NetworkError("msg"),
            TimeoutError("msg"),
        ]

        for error in errors:
            assert hasattr(error, "code")
            assert error.code is not None

    def test_error_status_code_attribute(self):
        """Test that all errors have status_code attribute"""
        errors = [
            SendlyError("msg", code="code", status_code=400),
            AuthenticationError("msg", status_code=401),
            RateLimitError("msg", retry_after=60, status_code=429),
            InsufficientCreditsError("msg", credits_needed=1, current_balance=0, status_code=402),
            ValidationError("msg", status_code=400),
            NotFoundError("msg", status_code=404),
            NetworkError("msg"),
            TimeoutError("msg"),
        ]

        for error in errors:
            assert hasattr(error, "status_code")


class TestErrorStringRepresentation:
    """Test error string representations"""

    def test_error_str_with_status_code(self):
        """Test error string representation with status code"""
        error = SendlyError("Test message", code="test_code", status_code=400)

        assert str(error) == "[test_code] (400) Test message"

    def test_error_str_without_status_code(self):
        """Test error string representation without status code"""
        error = SendlyError("Test message", code="test_code")

        assert str(error) == "[test_code] Test message"

    def test_all_errors_have_string_representation(self):
        """Test that all errors have proper string representation"""
        errors = [
            SendlyError("msg", code="code"),
            AuthenticationError("msg"),
            RateLimitError("msg", retry_after=60),
            InsufficientCreditsError("msg", credits_needed=1, current_balance=0),
            ValidationError("msg"),
            NotFoundError("msg"),
            NetworkError("msg"),
            TimeoutError("msg"),
        ]

        for error in errors:
            string_repr = str(error)
            assert isinstance(string_repr, str)
            assert len(string_repr) > 0
            assert "msg" in string_repr


class TestApiErrorResponse:
    """Test ApiErrorResponse type"""

    def test_basic_api_error_response(self):
        """Test basic API error response"""
        response = ApiErrorResponse(
            error="test_error",
            message="Test message",
        )

        assert response.error == "test_error"
        assert response.message == "Test message"

    def test_api_error_response_with_optional_fields(self):
        """Test API error response with optional fields"""
        response = ApiErrorResponse(
            error="insufficient_credits",
            message="Not enough credits",
            creditsNeeded=10,
            currentBalance=5,
            retryAfter=60,
        )

        assert response.credits_needed == 10
        assert response.current_balance == 5
        assert response.retry_after == 60

    def test_api_error_response_default_values(self):
        """Test API error response default values"""
        response = ApiErrorResponse(
            error="test_error",
            message="Test message",
        )

        assert response.credits_needed is None
        assert response.current_balance is None
        assert response.retry_after is None
