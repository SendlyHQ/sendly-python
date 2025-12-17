"""
Sendly Webhook Helpers

Utilities for verifying and parsing webhook events from Sendly.

Example:
    >>> from sendly import Webhooks
    >>>
    >>> # In your webhook handler (e.g., Flask)
    >>> @app.route('/webhooks/sendly', methods=['POST'])
    >>> def handle_webhook():
    ...     signature = request.headers.get('X-Sendly-Signature')
    ...     payload = request.get_data(as_text=True)
    ...
    ...     try:
    ...         event = Webhooks.parse_event(payload, signature, WEBHOOK_SECRET)
    ...         print(f'Received event: {event.type}')
    ...
    ...         if event.type == 'message.delivered':
    ...             print(f'Message {event.data.message_id} delivered!')
    ...         elif event.type == 'message.failed':
    ...             print(f'Message {event.data.message_id} failed: {event.data.error}')
    ...
    ...         return 'OK', 200
    ...     except WebhookSignatureError:
    ...         return 'Invalid signature', 401
"""

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Literal, Optional

# Webhook event types
WebhookEventType = Literal[
    "message.queued",
    "message.sent",
    "message.delivered",
    "message.failed",
    "message.undelivered",
]

# Message status in webhook events
WebhookMessageStatus = Literal[
    "queued",
    "sent",
    "delivered",
    "failed",
    "undelivered",
]


@dataclass
class WebhookMessageData:
    """Data payload for message webhook events."""

    message_id: str
    """The message ID."""

    status: WebhookMessageStatus
    """Current message status."""

    to: str
    """Recipient phone number."""

    from_: str
    """Sender ID or phone number."""

    segments: int
    """Number of SMS segments."""

    credits_used: int
    """Credits charged."""

    error: Optional[str] = None
    """Error message if status is 'failed' or 'undelivered'."""

    error_code: Optional[str] = None
    """Error code if available."""

    delivered_at: Optional[str] = None
    """When the message was delivered (ISO 8601)."""

    failed_at: Optional[str] = None
    """When the message failed (ISO 8601)."""


@dataclass
class WebhookEvent:
    """Webhook event from Sendly."""

    id: str
    """Unique event ID."""

    type: WebhookEventType
    """Event type."""

    data: WebhookMessageData
    """Event data."""

    created_at: str
    """When the event was created (ISO 8601)."""

    api_version: str = "2024-01-01"
    """API version."""


class WebhookSignatureError(Exception):
    """Error thrown when webhook signature verification fails."""

    def __init__(self, message: str = "Invalid webhook signature"):
        super().__init__(message)
        self.message = message


class Webhooks:
    """Webhook utilities for verifying and parsing Sendly webhook events."""

    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """
        Verify webhook signature from Sendly.

        Args:
            payload: Raw request body as string.
            signature: X-Sendly-Signature header value.
            secret: Your webhook secret from dashboard.

        Returns:
            True if signature is valid, False otherwise.

        Example:
            >>> is_valid = Webhooks.verify_signature(
            ...     raw_body,
            ...     request.headers['X-Sendly-Signature'],
            ...     WEBHOOK_SECRET
            ... )
        """
        if not payload or not signature or not secret:
            return False

        try:
            expected = hmac.new(
                secret.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            expected_signature = f"sha256={expected}"

            # Use timing-safe comparison to prevent timing attacks
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False

    @staticmethod
    def parse_event(payload: str, signature: str, secret: str) -> WebhookEvent:
        """
        Parse and validate a webhook event.

        Args:
            payload: Raw request body as string.
            signature: X-Sendly-Signature header value.
            secret: Your webhook secret from dashboard.

        Returns:
            Parsed and validated WebhookEvent.

        Raises:
            WebhookSignatureError: If signature is invalid or payload is malformed.

        Example:
            >>> try:
            ...     event = Webhooks.parse_event(raw_body, signature, secret)
            ...     print(f'Event type: {event.type}')
            ...     print(f'Message ID: {event.data.message_id}')
            ... except WebhookSignatureError:
            ...     print('Invalid signature')
        """
        if not Webhooks.verify_signature(payload, signature, secret):
            raise WebhookSignatureError()

        try:
            raw_event = json.loads(payload)

            # Basic validation
            if not all(key in raw_event for key in ("id", "type", "data", "created_at")):
                raise ValueError("Invalid event structure")

            # Parse data
            raw_data = raw_event["data"]
            data = WebhookMessageData(
                message_id=raw_data["message_id"],
                status=raw_data["status"],
                to=raw_data["to"],
                from_=raw_data.get("from", ""),
                segments=raw_data.get("segments", 1),
                credits_used=raw_data.get("credits_used", 0),
                error=raw_data.get("error"),
                error_code=raw_data.get("error_code"),
                delivered_at=raw_data.get("delivered_at"),
                failed_at=raw_data.get("failed_at"),
            )

            return WebhookEvent(
                id=raw_event["id"],
                type=raw_event["type"],
                data=data,
                created_at=raw_event["created_at"],
                api_version=raw_event.get("api_version", "2024-01-01"),
            )
        except WebhookSignatureError:
            raise
        except Exception as e:
            raise WebhookSignatureError(f"Failed to parse webhook payload: {e}")

    @staticmethod
    def generate_signature(payload: str, secret: str) -> str:
        """
        Generate a webhook signature for testing purposes.

        Args:
            payload: The payload to sign.
            secret: The secret to use for signing.

        Returns:
            The signature in the format "sha256=...".

        Example:
            >>> # For testing your webhook handler
            >>> test_payload = json.dumps({
            ...     'id': 'evt_test',
            ...     'type': 'message.delivered',
            ...     'data': {'message_id': 'msg_test', 'status': 'delivered'},
            ...     'created_at': datetime.now().isoformat()
            ... })
            >>> signature = Webhooks.generate_signature(test_payload, 'test_secret')
        """
        hash_value = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={hash_value}"
