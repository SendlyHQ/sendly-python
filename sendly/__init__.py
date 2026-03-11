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

__version__ = "3.21.0"

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

# Resources
from .resources.media import AsyncMediaResource, MediaResource

# Types
from .types import (
    ALL_SUPPORTED_COUNTRIES,
    # Constants
    CREDITS_PER_SMS,
    SANDBOX_TEST_NUMBERS,
    SUPPORTED_COUNTRIES,
    # Account types
    Account,
    # Enterprise types
    AnalyticsOverview,
    ApiKey,
    AutoTopUpSettings,
    BillingBreakdown,
    BillingBreakdownSummary,
    BulkProvisionResult,
    BulkProvisionResultItem,
    BulkProvisionSummary,
    CircuitState,
    CreatedApiKey,
    CreateOptInPageResult,
    CreateWebhookOptions,
    CreditAnalytics,
    CreditAnalyticsDataPoint,
    Credits,
    CreditTransaction,
    DeliveryAnalyticsItem,
    DeliveryStatus,
    DnsRecord,
    EnterpriseAccount,
    EnterpriseWebhook,
    EnterpriseWebhookTestResult,
    EnterpriseWorkspace,
    EnterpriseWorkspaceDetail,
    EnterpriseWorkspaceKey,
    EnterpriseWorkspaceListResponse,
    EnterpriseWorkspaceSummary,
    Invitation,
    ListMessagesOptions,
    # Media types
    MediaFile,
    Message,
    MessageAnalytics,
    MessageAnalyticsDataPoint,
    MessageListResponse,
    MessageStatus,
    OptInPage,
    PricingTier,
    QuotaSettings,
    RateLimitInfo,
    ResumeWorkspaceResult,
    SandboxTestNumbers,
    SenderType,
    SendlyConfig,
    SendMessageRequest,
    SetCustomDomainResult,
    SetWorkspaceWebhookResult,
    SuspendWorkspaceResult,
    TransactionType,
    TransferCreditsResult,
    UpdateWebhookOptions,
    # Webhook types
    Webhook,
    WebhookCreatedResponse,
    WebhookDelivery,
    WebhookSecretRotation,
    WebhookTestResult,
    WorkspaceBillingItem,
    WorkspaceCredits,
    WorkspaceWebhook,
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
    "MediaFile",
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
    # Enterprise types
    "AnalyticsOverview",
    "AutoTopUpSettings",
    "BillingBreakdown",
    "BillingBreakdownSummary",
    "BulkProvisionResult",
    "BulkProvisionResultItem",
    "BulkProvisionSummary",
    "CreateOptInPageResult",
    "CreatedApiKey",
    "CreditAnalytics",
    "CreditAnalyticsDataPoint",
    "DeliveryAnalyticsItem",
    "DnsRecord",
    "EnterpriseAccount",
    "EnterpriseWebhook",
    "EnterpriseWebhookTestResult",
    "EnterpriseWorkspace",
    "EnterpriseWorkspaceDetail",
    "EnterpriseWorkspaceKey",
    "EnterpriseWorkspaceListResponse",
    "EnterpriseWorkspaceSummary",
    "Invitation",
    "MessageAnalytics",
    "MessageAnalyticsDataPoint",
    "OptInPage",
    "QuotaSettings",
    "ResumeWorkspaceResult",
    "SetCustomDomainResult",
    "SetWorkspaceWebhookResult",
    "SuspendWorkspaceResult",
    "TransferCreditsResult",
    "WorkspaceBillingItem",
    "WorkspaceCredits",
    "WorkspaceWebhook",
    # Media resources
    "MediaResource",
    "AsyncMediaResource",
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
