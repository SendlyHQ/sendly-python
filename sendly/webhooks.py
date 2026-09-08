"""
Sendly Webhook Helpers

Utilities for verifying and parsing webhook events from Sendly.

Every event exposes its payload verbatim on ``event.object`` (alias
``event.raw_object``), whatever the event type. ``event.data`` is the *message*
view and is ``None`` for anything that is not a ``message.*`` event, because a
lifecycle payload (RCS, WhatsApp, voice, 10DLC, numbers, porting, contacts,
conversations, drafts, verification) is not message-shaped.

Example:
    >>> from sendly import Webhooks, WebhookSignatureError
    >>>
    >>> # In your webhook handler (e.g., Flask)
    >>> @app.route('/webhooks/sendly', methods=['POST'])
    >>> def handle_webhook():
    ...     signature = request.headers.get('X-Sendly-Signature')
    ...     timestamp = request.headers.get('X-Sendly-Timestamp')
    ...     payload = request.get_data(as_text=True)
    ...
    ...     try:
    ...         event = Webhooks.parse_event(
    ...             payload, signature, WEBHOOK_SECRET, timestamp=timestamp
    ...         )
    ...         print(f'Received event: {event.type}')
    ...
    ...         if event.type == 'message.delivered':
    ...             print(f'Message {event.data.id} delivered!')
    ...         elif event.type == 'message.failed':
    ...             print(f'Message {event.data.id} failed: {event.data.error}')
    ...         elif event.type == 'rcs_agent.live':
    ...             # Lifecycle event: event.data is None, read event.object
    ...             print(f"Agent {event.object['agent_id']} is live")
    ...
    ...         return 'OK', 200
    ...     except WebhookSignatureError:
    ...         return 'Invalid signature', 401
"""

import dataclasses
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union, cast, overload

from .types import WebhookEventType

__all__ = [
    "SIGNATURE_TOLERANCE_SECONDS",
    "WEBHOOK_EVENT_TYPES",
    "WebhookEvent",
    "WebhookEventType",
    "WebhookMessageData",
    "WebhookMessageStatus",
    "WebhookSignatureError",
    "WebhookVerificationData",
    "Webhooks",
    "is_message_event",
]

# Event types are defined once, in sendly.types.WebhookEventType. This module
# re-exports that enum rather than carrying a second, drifting copy.
WEBHOOK_EVENT_TYPES: Tuple[str, ...] = tuple(member.value for member in WebhookEventType)

# The event-type prefix that carries a message-shaped payload. Everything else
# ("rcs_*", "whatsapp_*", "call.*", "brand.*", "campaign.*", "assignment.*",
# "number.*", "port*", "contact*", "conversation.*", "draft.*",
# "verification.*", and any type released after this SDK version) carries a
# different object entirely and is exposed only through `event.object`.
MESSAGE_EVENT_PREFIX = "message."

#: message.opt_in and message.opt_out share the message.* prefix but carry an opt-out record ({phone_number, keyword, from_number, timestamp}), not a message.
#: Treating them as messages produced a message view with every field null, which is the invented-value problem this module removes.
NON_MESSAGE_MESSAGE_EVENTS = frozenset({"message.opt_in", "message.opt_out"})

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

T = TypeVar("T")


def is_message_event(event_type: Union[str, WebhookEventType]) -> bool:
    """Whether an event type carries a message-shaped ``data.object``.

    Only ``message.*`` events do. Lifecycle events carry their own object and
    must be read with :attr:`WebhookEvent.object` / :meth:`WebhookEvent.object_as`.
    """
    value = event_type.value if isinstance(event_type, WebhookEventType) else str(event_type)
    return (
        value.startswith(MESSAGE_EVENT_PREFIX)
        and value not in NON_MESSAGE_MESSAGE_EVENTS
    )


def _object_as(obj: Dict[str, Any], cls: Type[T]) -> T:
    """Build ``cls`` from a raw webhook object without inventing values."""
    if cls is dict:
        return cast(T, dict(obj))

    model_validate = getattr(cls, "model_validate", None)
    if callable(model_validate):  # pydantic v2 model
        return cast(T, model_validate(obj))

    if dataclasses.is_dataclass(cls):
        kwargs: Dict[str, Any] = {}
        for f in dataclasses.fields(cls):
            if f.name in obj:
                kwargs[f.name] = obj[f.name]
            elif f.name.endswith("_") and f.name[:-1] in obj:
                # `from_` <- `from`, `class_` <- `class`, ...
                kwargs[f.name] = obj[f.name[:-1]]
        return cast(T, cls(**kwargs))

    return cls(**obj)


@dataclass
class WebhookMessageData:
    """The message view of ``data.object`` for ``message.*`` events.

    Every field is optional: a key the payload did not carry stays ``None``
    rather than being filled with a plausible-looking default.
    """

    id: Optional[str] = None
    """The message ID, from `id` (or legacy `message_id`). None if absent."""

    status: Optional[WebhookMessageStatus] = None
    """Current message status. One of WebhookMessageStatus when known."""

    to: Optional[str] = None
    """Recipient phone number. None if the payload did not carry one."""

    from_: Optional[str] = None
    """Sender ID or phone number. None if the payload did not carry one."""

    segments: Optional[int] = None
    """Number of SMS segments. None if the payload did not carry one."""

    credits_used: Optional[int] = None
    """Credits charged. None if the payload did not carry one."""

    direction: Optional[str] = None
    """Message direction: outbound or inbound. None if absent."""

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

    media_urls: Optional[List[Any]] = None
    """Media URLs for MMS messages."""

    retry_count: Optional[int] = None

    metadata: Optional[Dict[str, Any]] = None

    batch_id: Optional[str] = None
    """Batch ID if message was sent as part of a batch."""

    @property
    def message_id(self) -> Optional[str]:
        """Backwards-compatible alias for id."""
        return self.id


@dataclass
class WebhookVerificationData:
    """The verification view of ``data.object`` for ``verification.*`` events.

    Not produced by :meth:`Webhooks.parse_event`; pass it to
    ``event.object_as(WebhookVerificationData)`` when you want it.
    """

    id: Optional[str] = None
    organization_id: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    delivery_status: Optional[str] = None
    attempts: Optional[int] = None
    max_attempts: Optional[int] = None
    expires_at: Optional[Union[str, int]] = None
    verified_at: Optional[Union[str, int]] = None
    created_at: Optional[Union[str, int]] = None
    app_name: Optional[str] = None
    template_id: Optional[str] = None
    profile_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class WebhookEvent:
    """Webhook event from Sendly."""

    id: str
    """Unique event ID."""

    type: Union[WebhookEventType, str]
    """Event type, verbatim from the payload.

    Compares equal to the matching :class:`~sendly.types.WebhookEventType`
    member; an event type this SDK version does not know about is still
    delivered as its raw string rather than being rejected.
    """

    data: Optional[WebhookMessageData] = None
    """The message view of ``data.object``.

    ``None`` for every event that is not a ``message.*`` event — RCS, WhatsApp,
    voice (``call.*``), 10DLC (``brand.*``/``campaign.*``/``assignment.*``),
    ``number.*``, ``port*``, ``contact*``, ``conversation.*``, ``draft.*`` and
    ``verification.*`` payloads are not message-shaped. Read those with
    :attr:`object` or :meth:`object_as`.
    """

    created: Union[str, int] = 0
    """When the event was created (unix timestamp)."""

    api_version: str = "2024-01"
    """API version."""

    livemode: bool = False
    """Whether this is a live (production) event."""

    object: Dict[str, Any] = field(default_factory=dict)
    """``data.object`` exactly as it arrived, for every event type.

    Keys are verbatim (``camelCase`` stays ``camelCase``), JSON ``null`` stays
    ``None``, and nothing is added that the payload did not carry.
    """

    @property
    def raw_object(self) -> Dict[str, Any]:
        """Alias for :attr:`object` (mirrors the Go/.NET SDKs' RawObject)."""
        return self.object

    @property
    def created_at(self) -> Union[str, int]:
        """Backwards-compatible alias for created."""
        return self.created

    @overload
    def object_as(self) -> Dict[str, Any]:
        ...

    @overload
    def object_as(self, cls: Type[T]) -> T:
        ...

    def object_as(self, cls: Optional[Type[Any]] = None) -> Any:
        """Read ``data.object`` as the shape you expect.

        Works with a dataclass, a pydantic model, or ``dict`` (the default):

            >>> @dataclasses.dataclass
            ... class AgentLive:
            ...     agent_id: str
            ...     name: str
            ...     stage: str
            >>> agent = event.object_as(AgentLive)

        Only keys the payload actually carried are passed through.
        """
        if cls is None:
            return dict(self.object)
        return _object_as(self.object, cls)


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
            Parsed and validated WebhookEvent. ``event.object`` always holds
            ``data.object`` verbatim; ``event.data`` is the message view and is
            ``None`` for every non-``message.*`` event.

        Raises:
            WebhookSignatureError: If signature is invalid or payload is malformed.

        Example:
            >>> try:
            ...     event = Webhooks.parse_event(raw_body, signature, secret, timestamp=ts)
            ...     print(f'Event type: {event.type}')
            ...     if event.data is not None:
            ...         print(f'Message ID: {event.data.id}')
            ...     else:
            ...         print(f'Object: {event.object}')
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
            obj = raw_data.get("object", raw_data) if isinstance(raw_data, dict) else raw_data
            # Fail loudly rather than substituting {}. An earlier revision fell
            # back to an empty dict here, which turned a malformed or legacy-flat
            # payload into a successfully-parsed event carrying nothing — the
            # exact silent-data-loss class this module was rewritten to remove.
            if not isinstance(obj, dict):
                raise ValueError(
                    "Invalid event structure: data.object must be an object, "
                    f"got {type(obj).__name__}"
                )

            event_type = raw_event["type"]

            data: Optional[WebhookMessageData] = None
            if is_message_event(event_type):
                # `message_id` is only a fallback for the message's own id on a
                # message event. It is never read off a lifecycle payload,
                # where `id` belongs to something else entirely (a contact, a
                # brand, a call) and `message_id` points at a different row.
                message_id = obj["id"] if "id" in obj else obj.get("message_id")
                data = WebhookMessageData(
                    id=message_id,
                    status=obj.get("status"),
                    to=obj.get("to"),
                    from_=obj.get("from"),
                    segments=obj.get("segments"),
                    credits_used=obj.get("credits_used"),
                    direction=obj.get("direction"),
                    organization_id=obj.get("organization_id"),
                    text=obj.get("text"),
                    error=obj.get("error"),
                    error_code=obj.get("error_code"),
                    delivered_at=obj.get("delivered_at"),
                    failed_at=obj.get("failed_at"),
                    created_at=obj.get("created_at"),
                    message_format=obj.get("message_format"),
                    media_urls=obj.get("media_urls"),
                    retry_count=obj.get("retry_count"),
                    metadata=obj.get("metadata"),
                    batch_id=obj.get("batch_id"),
                )

            created = raw_event["created"] if "created" in raw_event else raw_event.get(
                "created_at", 0
            )

            return WebhookEvent(
                id=raw_event["id"],
                type=event_type,
                data=data,
                created=created,
                api_version=raw_event.get("api_version", "2024-01"),
                livemode=raw_event.get("livemode", False),
                object=obj,
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
