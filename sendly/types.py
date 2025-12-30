"""
Sendly Python SDK Types

This module contains all type definitions and data models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# ============================================================================
# Enums
# ============================================================================


class MessageStatus(str, Enum):
    """Message delivery status"""

    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class SenderType(str, Enum):
    """How the message was sent"""

    NUMBER_POOL = "number_pool"
    ALPHANUMERIC = "alphanumeric"
    SANDBOX = "sandbox"


class MessageType(str, Enum):
    """Message type for compliance classification"""

    MARKETING = "marketing"
    TRANSACTIONAL = "transactional"


class PricingTier(str, Enum):
    """SMS pricing tier"""

    DOMESTIC = "domestic"
    TIER1 = "tier1"
    TIER2 = "tier2"
    TIER3 = "tier3"


# ============================================================================
# Configuration
# ============================================================================


class SendlyConfig(BaseModel):
    """Configuration options for the Sendly client"""

    api_key: str = Field(..., description="Your Sendly API key")
    base_url: str = Field(
        default="https://sendly.live/api/v1",
        description="Base URL for the Sendly API",
    )
    timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts",
    )


# ============================================================================
# Messages
# ============================================================================


class SendMessageRequest(BaseModel):
    """Request payload for sending an SMS message"""

    to: str = Field(
        ...,
        description="Destination phone number in E.164 format",
        examples=["+15551234567"],
    )
    text: str = Field(
        ...,
        description="Message content",
        min_length=1,
    )
    from_: Optional[str] = Field(
        default=None,
        alias="from",
        description="Sender ID or phone number",
    )
    message_type: Optional[MessageType] = Field(
        default=None,
        alias="messageType",
        description="Message type: 'marketing' (default, subject to quiet hours) or 'transactional' (24/7)",
    )

    class Config:
        populate_by_name = True


class Message(BaseModel):
    """A sent or received SMS message"""

    id: str = Field(..., description="Unique message identifier")
    to: str = Field(..., description="Destination phone number")
    from_: Optional[str] = Field(
        default=None, alias="from", description="Sender ID or phone number"
    )
    text: str = Field(..., description="Message content")
    status: MessageStatus = Field(..., description="Delivery status")
    direction: Literal["outbound", "inbound"] = Field(
        default="outbound", description="Message direction"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    segments: int = Field(default=1, description="Number of SMS segments")
    credits_used: int = Field(default=0, alias="creditsUsed", description="Credits charged")
    is_sandbox: bool = Field(default=False, alias="isSandbox", description="Sandbox mode flag")
    sender_type: Optional[SenderType] = Field(
        default=None, alias="senderType", description="How the message was sent"
    )
    telnyx_message_id: Optional[str] = Field(
        default=None, alias="telnyxMessageId", description="Telnyx message ID for tracking"
    )
    warning: Optional[str] = Field(
        default=None, description="Warning message (e.g., when 'from' is ignored)"
    )
    sender_note: Optional[str] = Field(
        default=None, alias="senderNote", description="Note about sender behavior"
    )
    created_at: Optional[str] = Field(
        default=None, alias="createdAt", description="Creation timestamp"
    )
    delivered_at: Optional[str] = Field(
        default=None, alias="deliveredAt", description="Delivery timestamp"
    )

    class Config:
        populate_by_name = True


class MessageListResponse(BaseModel):
    """Response from listing messages"""

    data: List[Message] = Field(..., description="List of messages")
    count: int = Field(..., description="Total count")


class ListMessagesOptions(BaseModel):
    """Options for listing messages"""

    limit: Optional[int] = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of messages to return",
    )


# ============================================================================
# Scheduled Messages
# ============================================================================


class ScheduledMessageStatus(str, Enum):
    """Scheduled message status"""

    SCHEDULED = "scheduled"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ScheduleMessageRequest(BaseModel):
    """Request payload for scheduling an SMS message"""

    to: str = Field(
        ...,
        description="Destination phone number in E.164 format",
    )
    text: str = Field(
        ...,
        description="Message content",
        min_length=1,
    )
    scheduled_at: str = Field(
        ...,
        alias="scheduledAt",
        description="When to send (ISO 8601, must be > 1 minute in future)",
    )
    from_: Optional[str] = Field(
        default=None,
        alias="from",
        description="Sender ID (for international destinations only)",
    )
    message_type: Optional[MessageType] = Field(
        default=None,
        alias="messageType",
        description="Message type: 'marketing' (default, subject to quiet hours) or 'transactional' (24/7)",
    )

    class Config:
        populate_by_name = True


class ScheduledMessage(BaseModel):
    """A scheduled SMS message"""

    id: str = Field(..., description="Unique message identifier")
    to: str = Field(..., description="Destination phone number")
    from_: Optional[str] = Field(default=None, alias="from", description="Sender ID")
    text: str = Field(..., description="Message content")
    status: ScheduledMessageStatus = Field(..., description="Current status")
    scheduled_at: str = Field(..., alias="scheduledAt", description="When message is scheduled")
    credits_reserved: int = Field(
        default=0, alias="creditsReserved", description="Credits reserved"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    created_at: Optional[str] = Field(
        default=None, alias="createdAt", description="Creation timestamp"
    )
    cancelled_at: Optional[str] = Field(
        default=None, alias="cancelledAt", description="Cancellation timestamp"
    )
    sent_at: Optional[str] = Field(default=None, alias="sentAt", description="Sent timestamp")

    class Config:
        populate_by_name = True


class ScheduledMessageListResponse(BaseModel):
    """Response from listing scheduled messages"""

    data: List[ScheduledMessage] = Field(..., description="List of scheduled messages")
    count: int = Field(..., description="Total count")


class ListScheduledMessagesOptions(BaseModel):
    """Options for listing scheduled messages"""

    limit: Optional[int] = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of messages to return",
    )
    offset: Optional[int] = Field(
        default=0,
        ge=0,
        description="Number of messages to skip",
    )
    status: Optional[ScheduledMessageStatus] = Field(
        default=None,
        description="Filter by status",
    )


class CancelledMessageResponse(BaseModel):
    """Response from cancelling a scheduled message"""

    id: str = Field(..., description="Message ID")
    status: Literal["cancelled"] = Field(..., description="Status (always cancelled)")
    credits_refunded: int = Field(..., alias="creditsRefunded", description="Credits refunded")
    cancelled_at: str = Field(..., alias="cancelledAt", description="Cancellation timestamp")

    class Config:
        populate_by_name = True


# ============================================================================
# Batch Messages
# ============================================================================


class BatchStatus(str, Enum):
    """Batch status"""

    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


class BatchMessageItem(BaseModel):
    """A single message in a batch request"""

    to: str = Field(..., description="Destination phone number in E.164 format")
    text: str = Field(..., description="Message content")


class BatchMessageRequest(BaseModel):
    """Request payload for sending batch messages"""

    messages: List[BatchMessageItem] = Field(
        ...,
        description="Array of messages to send (max 1000)",
        min_length=1,
        max_length=1000,
    )
    from_: Optional[str] = Field(
        default=None,
        alias="from",
        description="Sender ID (for international destinations only)",
    )
    message_type: Optional[MessageType] = Field(
        default=None,
        alias="messageType",
        description="Message type: 'marketing' (default, subject to quiet hours) or 'transactional' (24/7)",
    )

    class Config:
        populate_by_name = True


class BatchMessageResult(BaseModel):
    """Result for a single message in a batch"""

    id: Optional[str] = Field(default=None, description="Message ID (if successful)")
    to: str = Field(..., description="Destination phone number")
    status: Literal["queued", "failed"] = Field(..., description="Status")
    error: Optional[str] = Field(default=None, description="Error message (if failed)")


class BatchMessageResponse(BaseModel):
    """Response from sending batch messages"""

    batch_id: str = Field(..., alias="batchId", description="Unique batch identifier")
    status: BatchStatus = Field(..., description="Current batch status")
    total: int = Field(..., description="Total number of messages")
    queued: int = Field(..., description="Messages queued successfully")
    sent: int = Field(..., description="Messages sent")
    failed: int = Field(..., description="Messages that failed")
    credits_used: int = Field(..., alias="creditsUsed", description="Total credits used")
    messages: List[BatchMessageResult] = Field(..., description="Individual message results")
    created_at: str = Field(..., alias="createdAt", description="Creation timestamp")
    completed_at: Optional[str] = Field(
        default=None, alias="completedAt", description="Completion timestamp"
    )

    class Config:
        populate_by_name = True


class BatchListResponse(BaseModel):
    """Response from listing batches"""

    data: List[BatchMessageResponse] = Field(..., description="List of batches")
    count: int = Field(..., description="Total count")


class ListBatchesOptions(BaseModel):
    """Options for listing batches"""

    limit: Optional[int] = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of batches to return",
    )
    offset: Optional[int] = Field(
        default=0,
        ge=0,
        description="Number of batches to skip",
    )
    status: Optional[BatchStatus] = Field(
        default=None,
        description="Filter by status",
    )


# ============================================================================
# Errors
# ============================================================================


class ApiErrorResponse(BaseModel):
    """Error response from the API"""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    credits_needed: Optional[int] = Field(
        default=None, alias="creditsNeeded", description="Credits needed"
    )
    current_balance: Optional[int] = Field(
        default=None, alias="currentBalance", description="Current balance"
    )
    retry_after: Optional[int] = Field(
        default=None, alias="retryAfter", description="Seconds to wait"
    )

    class Config:
        populate_by_name = True
        extra = "allow"


# ============================================================================
# Rate Limiting
# ============================================================================


class RateLimitInfo(BaseModel):
    """Rate limit information from response headers"""

    limit: int = Field(..., description="Max requests per window")
    remaining: int = Field(..., description="Remaining requests")
    reset: int = Field(..., description="Seconds until reset")


# ============================================================================
# Constants
# ============================================================================

# Credits per SMS by tier
CREDITS_PER_SMS: Dict[PricingTier, int] = {
    PricingTier.DOMESTIC: 1,
    PricingTier.TIER1: 8,
    PricingTier.TIER2: 12,
    PricingTier.TIER3: 16,
}

# Supported countries by tier
SUPPORTED_COUNTRIES: Dict[PricingTier, List[str]] = {
    PricingTier.DOMESTIC: ["US", "CA"],
    PricingTier.TIER1: ["GB", "PL", "PT", "RO", "CZ", "HU", "CN", "KR", "IN", "PH", "TH", "VN"],
    PricingTier.TIER2: [
        "FR",
        "ES",
        "SE",
        "NO",
        "DK",
        "FI",
        "IE",
        "JP",
        "AU",
        "NZ",
        "SG",
        "HK",
        "MY",
        "ID",
        "BR",
        "AR",
        "CL",
        "CO",
        "ZA",
        "GR",
    ],
    PricingTier.TIER3: [
        "DE",
        "IT",
        "NL",
        "BE",
        "AT",
        "CH",
        "MX",
        "IL",
        "AE",
        "SA",
        "EG",
        "NG",
        "KE",
        "TW",
        "PK",
        "TR",
    ],
}

# All supported country codes
ALL_SUPPORTED_COUNTRIES: List[str] = [
    country for countries in SUPPORTED_COUNTRIES.values() for country in countries
]


# ============================================================================
# Sandbox Test Numbers
# ============================================================================


class SandboxTestNumbers:
    """Test phone numbers for sandbox mode.
    Use these with test API keys (sk_test_*) to simulate different scenarios.
    """

    SUCCESS = "+15005550000"  # Always succeeds - any number not in error list succeeds
    INVALID = "+15005550001"  # Fails with invalid_number error
    UNROUTABLE = "+15005550002"  # Fails with unroutable destination error
    QUEUE_FULL = "+15005550003"  # Fails with queue_full error
    RATE_LIMITED = "+15005550004"  # Fails with rate_limit_exceeded error
    CARRIER_VIOLATION = "+15005550006"  # Fails with carrier_violation error


SANDBOX_TEST_NUMBERS = SandboxTestNumbers()


# ============================================================================
# Webhooks
# ============================================================================


class WebhookEventType(str, Enum):
    """Webhook event types"""

    MESSAGE_SENT = "message.sent"
    MESSAGE_DELIVERED = "message.delivered"
    MESSAGE_FAILED = "message.failed"
    MESSAGE_BOUNCED = "message.bounced"


class WebhookMode(str, Enum):
    """Webhook event mode filter"""

    ALL = "all"  # Receive both test and live events
    TEST = "test"  # Only sandbox/test events
    LIVE = "live"  # Only production events (requires verification)


class CircuitState(str, Enum):
    """Circuit breaker state for webhook delivery"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class DeliveryStatus(str, Enum):
    """Webhook delivery status"""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Webhook(BaseModel):
    """A configured webhook endpoint"""

    id: str = Field(..., description="Unique webhook identifier (whk_xxx)")
    url: str = Field(..., description="HTTPS endpoint URL")
    events: List[str] = Field(..., description="Event types subscribed to")
    description: Optional[str] = Field(default=None, description="Optional description")
    mode: WebhookMode = Field(default=WebhookMode.ALL, description="Event mode filter")
    is_active: bool = Field(..., alias="isActive", description="Whether webhook is active")
    failure_count: int = Field(default=0, alias="failureCount", description="Consecutive failures")
    last_failure_at: Optional[str] = Field(
        default=None, alias="lastFailureAt", description="Last failure timestamp"
    )
    circuit_state: CircuitState = Field(
        default=CircuitState.CLOSED, alias="circuitState", description="Circuit breaker state"
    )
    circuit_opened_at: Optional[str] = Field(
        default=None, alias="circuitOpenedAt", description="When circuit was opened"
    )
    api_version: str = Field(default="2024-01", alias="apiVersion", description="API version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")
    created_at: str = Field(..., alias="createdAt", description="Creation timestamp")
    updated_at: str = Field(..., alias="updatedAt", description="Last update timestamp")
    total_deliveries: int = Field(default=0, alias="totalDeliveries", description="Total attempts")
    successful_deliveries: int = Field(
        default=0, alias="successfulDeliveries", description="Successful deliveries"
    )
    success_rate: float = Field(default=0, alias="successRate", description="Success rate (0-100)")
    last_delivery_at: Optional[str] = Field(
        default=None, alias="lastDeliveryAt", description="Last successful delivery"
    )

    class Config:
        populate_by_name = True


class WebhookCreatedResponse(Webhook):
    """Response when creating a webhook (includes secret once)"""

    secret: str = Field(..., description="Webhook signing secret - only shown once!")


class CreateWebhookOptions(BaseModel):
    """Options for creating a webhook"""

    url: str = Field(..., description="HTTPS endpoint URL")
    events: List[str] = Field(..., description="Event types to subscribe to")
    description: Optional[str] = Field(default=None, description="Optional description")
    mode: Optional[WebhookMode] = Field(
        default=None, description="Event mode filter (all, test, live)"
    )
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Custom metadata")


class UpdateWebhookOptions(BaseModel):
    """Options for updating a webhook"""

    url: Optional[str] = Field(default=None, description="New URL")
    events: Optional[List[str]] = Field(default=None, description="New event subscriptions")
    description: Optional[str] = Field(default=None, description="New description")
    is_active: Optional[bool] = Field(default=None, alias="isActive", description="Enable/disable")
    mode: Optional[WebhookMode] = Field(
        default=None, description="Event mode filter (all, test, live)"
    )
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Custom metadata")

    class Config:
        populate_by_name = True


class WebhookDelivery(BaseModel):
    """A webhook delivery attempt"""

    id: str = Field(..., description="Unique delivery identifier (del_xxx)")
    webhook_id: str = Field(..., alias="webhookId", description="Webhook ID")
    event_id: str = Field(..., alias="eventId", description="Event ID for idempotency")
    event_type: str = Field(..., alias="eventType", description="Event type")
    attempt_number: int = Field(..., alias="attemptNumber", description="Attempt number (1-6)")
    max_attempts: int = Field(..., alias="maxAttempts", description="Maximum attempts")
    status: DeliveryStatus = Field(..., description="Delivery status")
    response_status_code: Optional[int] = Field(
        default=None, alias="responseStatusCode", description="HTTP status code"
    )
    response_time_ms: Optional[int] = Field(
        default=None, alias="responseTimeMs", description="Response time in ms"
    )
    error_message: Optional[str] = Field(
        default=None, alias="errorMessage", description="Error message"
    )
    error_code: Optional[str] = Field(default=None, alias="errorCode", description="Error code")
    next_retry_at: Optional[str] = Field(
        default=None, alias="nextRetryAt", description="Next retry time"
    )
    created_at: str = Field(..., alias="createdAt", description="Creation timestamp")
    delivered_at: Optional[str] = Field(
        default=None, alias="deliveredAt", description="Delivery timestamp"
    )

    class Config:
        populate_by_name = True


class WebhookTestResult(BaseModel):
    """Response from testing a webhook"""

    success: bool = Field(..., description="Whether test was successful")
    status_code: Optional[int] = Field(
        default=None, alias="statusCode", description="HTTP status code"
    )
    response_time_ms: Optional[int] = Field(
        default=None, alias="responseTimeMs", description="Response time in ms"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")

    class Config:
        populate_by_name = True


class WebhookSecretRotation(BaseModel):
    """Response from rotating webhook secret"""

    webhook: Webhook = Field(..., description="The webhook")
    new_secret: str = Field(..., alias="newSecret", description="New signing secret")
    old_secret_expires_at: str = Field(
        ..., alias="oldSecretExpiresAt", description="When old secret expires"
    )
    message: str = Field(..., description="Message about grace period")

    class Config:
        populate_by_name = True


# ============================================================================
# Account & Credits
# ============================================================================


class Account(BaseModel):
    """Account information"""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    name: Optional[str] = Field(default=None, description="Display name")
    created_at: str = Field(..., alias="createdAt", description="Account creation date")

    class Config:
        populate_by_name = True


class Credits(BaseModel):
    """Credit balance information"""

    balance: int = Field(..., description="Available credit balance")
    reserved_balance: int = Field(
        default=0, alias="reservedBalance", description="Credits reserved for scheduled messages"
    )
    available_balance: int = Field(
        default=0, alias="availableBalance", description="Total usable credits"
    )

    class Config:
        populate_by_name = True


class TransactionType(str, Enum):
    """Credit transaction type"""

    PURCHASE = "purchase"
    USAGE = "usage"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"
    BONUS = "bonus"


class CreditTransaction(BaseModel):
    """A credit transaction record"""

    id: str = Field(..., description="Transaction ID")
    type: TransactionType = Field(..., description="Transaction type")
    amount: int = Field(..., description="Amount (positive for in, negative for out)")
    balance_after: int = Field(..., alias="balanceAfter", description="Balance after transaction")
    description: str = Field(..., description="Transaction description")
    message_id: Optional[str] = Field(
        default=None, alias="messageId", description="Related message ID"
    )
    created_at: str = Field(..., alias="createdAt", description="Transaction timestamp")

    class Config:
        populate_by_name = True


class ApiKey(BaseModel):
    """An API key"""

    id: str = Field(..., description="Key ID")
    name: str = Field(..., description="Key name/label")
    type: Literal["test", "live"] = Field(..., description="Key type")
    prefix: str = Field(..., description="Key prefix for identification")
    last_four: str = Field(..., alias="lastFour", description="Last 4 characters")
    permissions: List[str] = Field(default_factory=list, description="Permissions granted")
    created_at: str = Field(..., alias="createdAt", description="Creation timestamp")
    last_used_at: Optional[str] = Field(
        default=None, alias="lastUsedAt", description="Last used timestamp"
    )
    expires_at: Optional[str] = Field(
        default=None, alias="expiresAt", description="Expiration timestamp"
    )
    is_revoked: bool = Field(default=False, alias="isRevoked", description="Whether revoked")

    class Config:
        populate_by_name = True
