"""
Sendly Python SDK

Official SDK for the Sendly SMS API.

Example:
    >>> from sendly import Sendly
    >>>
    >>> client = Sendly('sk_live_v1_your_api_key')
    >>>
    >>> # Send an SMS
    >>> message = client.messages.send(
    ...     to='+15551234567',
    ...     text='Hello from Sendly!'
    ... )
    >>> print(f'Message sent: {message.id}')

Async Example:
    >>> import asyncio
    >>> from sendly import AsyncSendly
    >>>
    >>> async def main():
    ...     async with AsyncSendly('sk_live_v1_xxx') as client:
    ...         message = await client.messages.send(
    ...             to='+15551234567',
    ...             text='Hello!'
    ...         )
    >>>
    >>> asyncio.run(main())
"""

__version__ = "1.0.5"

# Main clients
from .client import AsyncSendly, Sendly

# Errors
from .errors import (
    AuthenticationError,
    InsufficientCreditsError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    SendlyError,
    TimeoutError,
    ValidationError,
)

# Types
from .types import (
    ALL_SUPPORTED_COUNTRIES,
    # Constants
    CREDITS_PER_SMS,
    SANDBOX_TEST_NUMBERS,
    SUPPORTED_COUNTRIES,
    # Account types
    Account,
    ApiKey,
    CircuitState,
    CreateWebhookOptions,
    Credits,
    CreditTransaction,
    DeliveryStatus,
    ListMessagesOptions,
    Message,
    MessageListResponse,
    MessageStatus,
    PricingTier,
    RateLimitInfo,
    SandboxTestNumbers,
    SenderType,
    SendlyConfig,
    SendMessageRequest,
    TransactionType,
    UpdateWebhookOptions,
    # Webhook types
    Webhook,
    WebhookCreatedResponse,
    WebhookDelivery,
    WebhookSecretRotation,
    WebhookTestResult,
)

# Utilities (for advanced usage)
from .utils.validation import (
    calculate_segments,
    get_country_from_phone,
    is_country_supported,
    validate_message_text,
    validate_phone_number,
    validate_sender_id,
)

# Webhooks
from .webhooks import (
    WebhookEvent,
    WebhookEventType,
    WebhookMessageData,
    WebhookMessageStatus,
    Webhooks,
    WebhookSignatureError,
)

__all__ = [
    # Version
    "__version__",
    # Clients
    "Sendly",
    "AsyncSendly",
    # Types
    "SendlyConfig",
    "SendMessageRequest",
    "Message",
    "MessageStatus",
    "SenderType",
    "ListMessagesOptions",
    "MessageListResponse",
    "RateLimitInfo",
    "PricingTier",
    # Webhook types
    "Webhook",
    "WebhookCreatedResponse",
    "CreateWebhookOptions",
    "UpdateWebhookOptions",
    "WebhookDelivery",
    "WebhookTestResult",
    "WebhookSecretRotation",
    "CircuitState",
    "DeliveryStatus",
    # Account types
    "Account",
    "Credits",
    "CreditTransaction",
    "TransactionType",
    "ApiKey",
    # Constants
    "CREDITS_PER_SMS",
    "SUPPORTED_COUNTRIES",
    "ALL_SUPPORTED_COUNTRIES",
    "SANDBOX_TEST_NUMBERS",
    "SandboxTestNumbers",
    # Errors
    "SendlyError",
    "AuthenticationError",
    "RateLimitError",
    "InsufficientCreditsError",
    "ValidationError",
    "NotFoundError",
    "NetworkError",
    "TimeoutError",
    # Utilities
    "validate_phone_number",
    "validate_message_text",
    "validate_sender_id",
    "get_country_from_phone",
    "is_country_supported",
    "calculate_segments",
    # Webhooks
    "Webhooks",
    "WebhookSignatureError",
    "WebhookEvent",
    "WebhookEventType",
    "WebhookMessageData",
    "WebhookMessageStatus",
]
