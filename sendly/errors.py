"""
Sendly SDK Error Classes

Custom exceptions for different error scenarios.
"""

from typing import Any, Dict, Optional

from .types import ApiErrorResponse


class SendlyError(Exception):
    """Base error class for all Sendly SDK errors"""

    def __init__(
        self,
        message: str,
        code: str = "internal_error",
        status_code: Optional[int] = None,
        response: Optional[ApiErrorResponse] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.response = response

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.code}] ({self.status_code}) {self.message}"
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"

    @classmethod
    def from_response(cls, status_code: int, response_data: Dict[str, Any]) -> "SendlyError":
        """Create a SendlyError from an API response"""
        try:
            error_response = ApiErrorResponse(**response_data)
        except Exception:
            error_response = ApiErrorResponse(
                error="internal_error",
                message=str(response_data),
            )

        code = error_response.error
        message = error_response.message

        # Return specific error types based on error code
        if code in (
            "unauthorized",
            "invalid_auth_format",
            "invalid_key_format",
            "invalid_api_key",
            "api_key_required",
            "key_revoked",
            "key_expired",
            "insufficient_permissions",
        ):
            return AuthenticationError(message, code, status_code, error_response)

        if code == "rate_limit_exceeded":
            return RateLimitError(
                message,
                retry_after=error_response.retry_after or 60,
                status_code=status_code,
                response=error_response,
            )

        if code == "insufficient_credits":
            return InsufficientCreditsError(
                message,
                credits_needed=error_response.credits_needed or 0,
                current_balance=error_response.current_balance or 0,
                status_code=status_code,
                response=error_response,
            )

        if code in ("invalid_request", "unsupported_destination"):
            return ValidationError(message, code, status_code, error_response)

        if code == "not_found":
            return NotFoundError(message, status_code, error_response)

        return cls(message, code, status_code, error_response)


class AuthenticationError(SendlyError):
    """Thrown when authentication fails"""

    def __init__(
        self,
        message: str,
        code: str = "unauthorized",
        status_code: Optional[int] = None,
        response: Optional[ApiErrorResponse] = None,
    ):
        super().__init__(message, code, status_code, response)


class RateLimitError(SendlyError):
    """Thrown when rate limit is exceeded"""

    def __init__(
        self,
        message: str,
        retry_after: int,
        status_code: Optional[int] = None,
        response: Optional[ApiErrorResponse] = None,
    ):
        super().__init__(message, "rate_limit_exceeded", status_code, response)
        self.retry_after = retry_after


class InsufficientCreditsError(SendlyError):
    """Thrown when credit balance is insufficient"""

    def __init__(
        self,
        message: str,
        credits_needed: int,
        current_balance: int,
        status_code: Optional[int] = None,
        response: Optional[ApiErrorResponse] = None,
    ):
        super().__init__(message, "insufficient_credits", status_code, response)
        self.credits_needed = credits_needed
        self.current_balance = current_balance


class ValidationError(SendlyError):
    """Thrown when request validation fails"""

    def __init__(
        self,
        message: str,
        code: str = "invalid_request",
        status_code: Optional[int] = None,
        response: Optional[ApiErrorResponse] = None,
    ):
        super().__init__(message, code, status_code, response)


class NotFoundError(SendlyError):
    """Thrown when a resource is not found"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[ApiErrorResponse] = None,
    ):
        super().__init__(message, "not_found", status_code, response)


class NetworkError(SendlyError):
    """Thrown when a network or connection error occurs"""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message, "internal_error")
        self.cause = cause


class TimeoutError(SendlyError):
    """Thrown when a request times out"""

    def __init__(self, message: str = "Request timed out"):
        super().__init__(message, "internal_error")
