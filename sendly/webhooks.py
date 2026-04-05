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
    ...     timestamp = request.headers.get('X-Sendly-Timestamp')
    ...     payload = request.get_data(as_text=True)
    ...
    ...     try:
    ...         event = Webhooks.parse_event(payload, signature, WEBHOOK_SECRET, timestamp=timestamp)
    ...         print(f'Received event: {event.type}')
    ...
    ...         if event.type == 'message.delivered':
    ...             print(f'Message {event.data.id} delivered!')
    ...         elif event.type == 'message.failed':
    ...             print(f'Message {event.data.id} failed: {event.data.error}')
    ...
    ...         return 'OK', 200
    ...     except WebhookSignatureError:
    ...         return 'Invalid signature', 401
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Literal, Optional, Union

# Webhook event types
WebhookEventType = Literal[
    "message.queued",
    "message.sent",
    "message.delivered",
    "message.failed",
    "message.bounced",
    "message.retrying",
    "message.received",
    "message.opt_out",
    "message.opt_in",
    "message.undelivered",
    "verification.created",
    "verification.delivered",
    "verification.verified",
    "verification.expired",
    "verification.failed",
    "verification.resent",
    "verification.delivery_failed",
]

# Message status in webhook events
WebhookMessageStatus = Literal[
    "queued",
    "sent",
    "delivered",
    "failed",
    "bounced",
    "retrying",
    "received",
    "undelivered",
]

SIGNATURE_TOLERANCE_SECONDS = 300


@dataclass
class WebhookMessageData:
    """Data payload for message webhook events."""

    id: str
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

    direction: str = "outbound"
    """Message direction: outbound or inbound."""

    organization_id: Optional[str] = None
    """Organization ID."""

    text: Optional[str] = None
    """Message text."""

    error: Optional[str] = None
    """Error message if status is 'failed' or 'undelivered'."""

    error_code: Optional[str] = None
    """Error code if available."""

    delivered_at: Optional[Union[str, int]] = None
    """When the message was delivered."""

    failed_at: Optional[Union[str, int]] = None
    """When the message failed."""

    created_at: Optional[Union[str, int]] = None
    """When the message was created."""

    message_format: Optional[str] = None
    """Message format: sms or mms."""

    media_urls: Optional[list] = None
    """Media URLs for MMS messages."""

    retry_count: Optional[int] = None

    metadata: Optional[dict] = None

    batch_id: Optional[str] = None
    """Batch ID if message was sent as part of a batch."""

    @property
    def message_id(self) -> str:
        """Backwards-compatible alias for id."""
        return self.id


@dataclass
class WebhookVerificationData:
    id: str = ""
    organization_id: Optional[str] = None
    phone: str = ""
    status: str = ""
    delivery_status: str = "queued"
    attempts: int = 0
    max_attempts: int = 3
    expires_at: Optional[Union[str, int]] = None
    verified_at: Optional[Union[str, int]] = None
    created_at: Optional[Union[str, int]] = None
    app_name: Optional[str] = None
    template_id: Optional[str] = None
    profile_id: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class WebhookEvent:
    """Webhook event from Sendly."""

    id: str
    """Unique event ID."""

    type: WebhookEventType
    """Event type."""

    data: WebhookMessageData
    """Event data."""

    created: Union[str, int] = 0
    """When the event was created (unix timestamp)."""

    api_version: str = "2024-01"
    """API version."""

    livemode: bool = False
    """Whether this is a live (production) event."""

    @property
    def created_at(self) -> Union[str, int]:
        """Backwards-compatible alias for created."""
        return self.created


class WebhookSignatureError(Exception):
    """Error thrown when webhook signature verification fails."""

    def __init__(self, message: str = "Invalid webhook signature"):
        super().__init__(message)
        self.message = message


class Webhooks:
    """Webhook utilities for verifying and parsing Sendly webhook events."""

    @staticmethod
    def verify_signature(
        payload: str,
        signature: str,
        secret: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Verify webhook signature from Sendly.

        Args:
            payload: Raw request body as string.
            signature: X-Sendly-Signature header value.
            secret: Your webhook secret from dashboard.
            timestamp: X-Sendly-Timestamp header value (recommended).

        Returns:
            True if signature is valid, False otherwise.

        Example:
            >>> is_valid = Webhooks.verify_signature(
            ...     raw_body,
            ...     request.headers['X-Sendly-Signature'],
            ...     WEBHOOK_SECRET,
            ...     timestamp=request.headers.get('X-Sendly-Timestamp')
            ... )
        """
        if not payload or not signature or not secret:
            return False

        try:
            if timestamp:
                signed_payload = f"{timestamp}.{payload}"
                if abs(time.time() - float(timestamp)) > SIGNATURE_TOLERANCE_SECONDS:
                    return False
            else:
                signed_payload = payload

            expected = hmac.new(
                secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            expected_signature = f"sha256={expected}"

            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False

    @staticmethod
    def parse_event(
        payload: str,
        signature: str,
        secret: str,
        timestamp: Optional[str] = None,
    ) -> WebhookEvent:
        """
        Parse and validate a webhook event.

        Args:
            payload: Raw request body as string.
            signature: X-Sendly-Signature header value.
            secret: Your webhook secret from dashboard.
            timestamp: X-Sendly-Timestamp header value (recommended).

        Returns:
            Parsed and validated WebhookEvent.

        Raises:
            WebhookSignatureError: If signature is invalid or payload is malformed.

        Example:
            >>> try:
            ...     event = Webhooks.parse_event(raw_body, signature, secret, timestamp=ts)
            ...     print(f'Event type: {event.type}')
            ...     print(f'Message ID: {event.data.id}')
            ... except WebhookSignatureError:
            ...     print('Invalid signature')
        """
        if not Webhooks.verify_signature(payload, signature, secret, timestamp=timestamp):
            raise WebhookSignatureError()

        try:
            raw_event = json.loads(payload)

            if not all(key in raw_event for key in ("id", "type", "data")):
                raise ValueError("Invalid event structure")

            raw_data = raw_event["data"]
            obj = raw_data.get("object", raw_data)

            data = WebhookMessageData(
                id=obj.get("id", obj.get("message_id", "")),
                status=obj.get("status", ""),
                to=obj.get("to", ""),
                from_=obj.get("from", ""),
                segments=obj.get("segments", 1),
                credits_used=obj.get("credits_used", 0),
                direction=obj.get("direction", "outbound"),
                organization_id=obj.get("organization_id"),
                text=obj.get("text"),
                error=obj.get("error"),
                error_code=obj.get("error_code"),
                delivered_at=obj.get("delivered_at"),
                failed_at=obj.get("failed_at"),
                created_at=obj.get("created_at"),
                message_format=obj.get("message_format"),
                media_urls=obj.get("media_urls"),
                batch_id=obj.get("batch_id"),
            )

            return WebhookEvent(
                id=raw_event["id"],
                type=raw_event["type"],
                data=data,
                created=raw_event.get("created", raw_event.get("created_at", 0)),
                api_version=raw_event.get("api_version", "2024-01"),
                livemode=raw_event.get("livemode", False),
            )
        except WebhookSignatureError:
            raise
        except Exception as e:
            raise WebhookSignatureError(f"Failed to parse webhook payload: {e}")

    @staticmethod
    def generate_signature(
        payload: str,
        secret: str,
        timestamp: Optional[str] = None,
    ) -> str:
        """
        Generate a webhook signature for testing purposes.

        Args:
            payload: The payload to sign.
            secret: The secret to use for signing.
            timestamp: Optional timestamp to include in signature.

        Returns:
            The signature in the format "sha256=...".
        """
        if timestamp:
            signed_payload = f"{timestamp}.{payload}"
        else:
            signed_payload = payload

        hash_value = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={hash_value}"
