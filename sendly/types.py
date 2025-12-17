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
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


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
        default="https://sendly.live/api",
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
    error: Optional[str] = Field(default=None, description="Error message if failed")
    segments: int = Field(default=1, description="Number of SMS segments")
    credits_used: int = Field(default=0, alias="creditsUsed", description="Credits charged")
    is_sandbox: bool = Field(default=False, alias="isSandbox", description="Sandbox mode flag")
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
    """Test phone numbers for sandbox mode"""

    SUCCESS = "+15550001234"  # Always succeeds instantly
    DELAYED = "+15550001010"  # Succeeds after 10 second delay
    INVALID = "+15550001001"  # Fails with invalid_number error
    REJECTED = "+15550001002"  # Fails with carrier_rejected error
    RATE_LIMITED = "+15550001003"  # Fails with rate_limit_exceeded error


SANDBOX_TEST_NUMBERS = SandboxTestNumbers()
