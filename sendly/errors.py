"""
Sendly SDK Error Classes

Custom exceptions for different error scenarios.
"""

import re
from typing import Any, Dict, List, Optional

from .types import ApiErrorResponse

_ERROR_CODE = re.compile(r"^[a-z][a-z0-9_]*$")

_CODE_FOR_STATUS = {
    400: "invalid_request",
    401: "unauthorized",
    402: "insufficient_credits",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "invalid_request",
    429: "rate_limit_exceeded",
}


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

    @property
    def field_errors(self) -> List[Dict[str, Any]]:
        """Per-field problems the API attached to this error, as
        ``[{"path": ..., "message": ...}]``. Empty unless the response carried
        an ``errors`` list (for example ``rcs_invalid_content``)."""
        if self.response is None:
            return []
        extra = self.response.model_extra or {}
        errors = extra.get("errors")
        if not isinstance(errors, list):
            return []
        return [e for e in errors if isinstance(e, dict)]

    @classmethod
    def from_response(cls, status_code: int, response_data: Dict[str, Any]) -> "SendlyError":
        """Create a SendlyError from an API response

        A body whose ``error`` is a sentence rather than a code, or that has no
        ``error`` at all, gets its code from the HTTP status (``invalid_request``,
        ``unauthorized``, ``insufficient_credits``, ``forbidden``,
        ``not_found``, ``conflict`` or ``rate_limit_exceeded``, otherwise
        ``internal_error``) and its message from ``message``, then the
        sentence, then the status. ``response`` keeps the rest of the body.
        """
        raw_error = response_data.get("error")
        raw_message = response_data.get("message")
        error_text = raw_error.strip() if isinstance(raw_error, str) else ""
        has_code = bool(_ERROR_CODE.match(error_text))
        code = error_text if has_code else _CODE_FOR_STATUS.get(status_code, "internal_error")
        message = (
            raw_message
            if isinstance(raw_message, str) and raw_message
            else ("" if has_code else error_text) or f"HTTP {status_code}"
        )

        try:
            error_response = ApiErrorResponse(
                **{**response_data, "error": error_text or code, "message": message}
            )
        except Exception:
            error_response = ApiErrorResponse(error=error_text or code, message=message)

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

        if code in (
            "rate_limit_exceeded",
            "provision_rate_limit",
            "too_many_failed_key_attempts",
            "too_many_concurrent_verifications",
        ):
            return RateLimitError(
                message,
                retry_after=error_response.retry_after or 60,
                status_code=status_code,
                response=error_response,
                code=code,
            )

        if code == "insufficient_credits":
            return InsufficientCreditsError(
                message,
                credits_needed=error_response.credits_needed or 0,
                current_balance=error_response.current_balance or 0,
                status_code=status_code,
                response=error_response,
            )

        if code in (
            "invalid_request",
            "unsupported_destination",
            "validation_error",
            "invalid_code",
        ):
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
    """Thrown when rate limit is exceeded

    ``code`` is ``rate_limit_exceeded`` for the request limit, and
    ``provision_rate_limit`` for the workspace provisioning limit (120 a
    minute, 1,000 an hour). It is ``too_many_failed_key_attempts`` when
    repeated wrong API keys from one address locked the account out for a
    while: fix the key, then wait
    ``retry_after`` seconds, since until the lockout ends the right key can
    be refused too. It is ``too_many_concurrent_verifications`` when too many
    first-time key checks ran at once; the client retries that one itself
    and only raises it once its retries run out.
    """

    def __init__(
        self,
        message: str,
        retry_after: int,
        status_code: Optional[int] = None,
        response: Optional[ApiErrorResponse] = None,
        code: str = "rate_limit_exceeded",
    ):
        super().__init__(message, code, status_code, response)
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
