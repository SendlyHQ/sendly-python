"""
Webhooks Resource

Manage webhook endpoints for receiving real-time message status updates.
"""

from typing import Any, Dict, List, Optional

from ..types import (
    CreateWebhookOptions,
    UpdateWebhookOptions,
    Webhook,
    WebhookCreatedResponse,
    WebhookDelivery,
    WebhookMode,
    WebhookSecretRotation,
    WebhookTestResult,
)
from ..utils.http import AsyncHttpClient, HttpClient


def _transform_webhook_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform snake_case API response to camelCase for pydantic models."""
    # Map snake_case keys to camelCase aliases
    key_map = {
        "is_active": "isActive",
        "failure_count": "failureCount",
        "last_failure_at": "lastFailureAt",
        "circuit_state": "circuitState",
        "circuit_opened_at": "circuitOpenedAt",
        "api_version": "apiVersion",
        "created_at": "createdAt",
        "updated_at": "updatedAt",
        "total_deliveries": "totalDeliveries",
        "successful_deliveries": "successfulDeliveries",
        "success_rate": "successRate",
        "last_delivery_at": "lastDeliveryAt",
    }
    result = {}
    for key, value in data.items():
        new_key = key_map.get(key, key)
        result[new_key] = value
    return result


def _transform_delivery_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform snake_case API response for webhook delivery."""
    key_map = {
        "webhook_id": "webhookId",
        "event_id": "eventId",
        "event_type": "eventType",
        "attempt_number": "attemptNumber",
        "max_attempts": "maxAttempts",
        "response_status_code": "responseStatusCode",
        "response_time_ms": "responseTimeMs",
        "error_message": "errorMessage",
        "error_code": "errorCode",
        "next_retry_at": "nextRetryAt",
        "created_at": "createdAt",
        "delivered_at": "deliveredAt",
    }
    result = {}
    for key, value in data.items():
        new_key = key_map.get(key, key)
        result[new_key] = value
    return result


class WebhooksResource:
    """
    Webhooks API resource (synchronous)

    Manage webhook endpoints for receiving real-time message status updates.

    Example:
        >>> # Create a webhook
        >>> webhook = client.webhooks.create(
        ...     url='https://example.com/webhooks/sendly',
        ...     events=['message.delivered', 'message.failed']
        ... )
        >>> # IMPORTANT: Save the secret - it's only shown once!
        >>> print(f'Secret: {webhook.secret}')
        >>>
        >>> # List webhooks
        >>> webhooks = client.webhooks.list()
        >>>
        >>> # Test a webhook
        >>> result = client.webhooks.test(webhook.id)
    """

    def __init__(self, http: HttpClient):
        self._http = http

    def create(
        self,
        url: str,
        events: List[str],
        description: Optional[str] = None,
        mode: Optional[WebhookMode] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WebhookCreatedResponse:
        """
        Create a new webhook endpoint.

        Args:
            url: HTTPS endpoint URL
            events: Event types to subscribe to
            description: Optional description
            mode: Event mode filter (all, test, live). Live requires verification.
            metadata: Custom metadata

        Returns:
            The created webhook with signing secret (shown only once!)

        Raises:
            ValidationError: If the URL is invalid or events are empty
            AuthenticationError: If the API key is invalid
        """
        if not url or not url.startswith("https://"):
            raise ValueError("Webhook URL must be HTTPS")

        if not events:
            raise ValueError("At least one event type is required")

        body = {"url": url, "events": events}
        if description:
            body["description"] = description
        if mode:
            body["mode"] = mode.value if isinstance(mode, WebhookMode) else mode
        if metadata:
            body["metadata"] = metadata

        response = self._http.request("POST", "/webhooks", json=body)
        return WebhookCreatedResponse(**_transform_webhook_response(response))

    def list(self) -> List[Webhook]:
        """
        List all webhooks.

        Returns:
            Array of webhook configurations
        """
        response = self._http.request("GET", "/webhooks")
        return [Webhook(**_transform_webhook_response(w)) for w in response]

    def get(self, webhook_id: str) -> Webhook:
        """
        Get a specific webhook by ID.

        Args:
            webhook_id: Webhook ID (whk_xxx)

        Returns:
            The webhook details

        Raises:
            NotFoundError: If the webhook doesn't exist
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = self._http.request("GET", f"/webhooks/{webhook_id}")
        return Webhook(**_transform_webhook_response(response))

    def update(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        mode: Optional[WebhookMode] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Webhook:
        """
        Update a webhook configuration.

        Args:
            webhook_id: Webhook ID
            url: New URL
            events: New event subscriptions
            description: New description
            is_active: Enable/disable webhook
            mode: Event mode filter (all, test, live)
            metadata: Custom metadata

        Returns:
            The updated webhook
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        if url and not url.startswith("https://"):
            raise ValueError("Webhook URL must be HTTPS")

        body = {}
        if url is not None:
            body["url"] = url
        if events is not None:
            body["events"] = events
        if description is not None:
            body["description"] = description
        if is_active is not None:
            body["is_active"] = is_active
        if mode is not None:
            body["mode"] = mode.value if isinstance(mode, WebhookMode) else mode
        if metadata is not None:
            body["metadata"] = metadata

        response = self._http.request("PATCH", f"/webhooks/{webhook_id}", json=body)
        return Webhook(**_transform_webhook_response(response))

    def delete(self, webhook_id: str) -> None:
        """
        Delete a webhook.

        Args:
            webhook_id: Webhook ID

        Raises:
            NotFoundError: If the webhook doesn't exist
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        self._http.request("DELETE", f"/webhooks/{webhook_id}")

    def test(self, webhook_id: str) -> WebhookTestResult:
        """
        Send a test event to a webhook endpoint.

        Args:
            webhook_id: Webhook ID

        Returns:
            Test result with response details
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = self._http.request("POST", f"/webhooks/{webhook_id}/test")
        return WebhookTestResult(**response)

    def rotate_secret(self, webhook_id: str) -> WebhookSecretRotation:
        """
        Rotate the webhook signing secret.

        The old secret remains valid for 24 hours to allow for graceful migration.

        Args:
            webhook_id: Webhook ID

        Returns:
            New secret and expiration info
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = self._http.request("POST", f"/webhooks/{webhook_id}/rotate-secret")
        # Transform the nested webhook object
        if "webhook" in response:
            response["webhook"] = _transform_webhook_response(response["webhook"])
        return WebhookSecretRotation(**response)

    def get_deliveries(self, webhook_id: str) -> List[WebhookDelivery]:
        """
        Get delivery history for a webhook.

        Args:
            webhook_id: Webhook ID

        Returns:
            Array of delivery attempts
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = self._http.request("GET", f"/webhooks/{webhook_id}/deliveries")
        return [WebhookDelivery(**_transform_delivery_response(d)) for d in response]

    def retry_delivery(self, webhook_id: str, delivery_id: str) -> None:
        """
        Retry a failed delivery.

        Args:
            webhook_id: Webhook ID
            delivery_id: Delivery ID
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")
        if not delivery_id or not delivery_id.startswith("del_"):
            raise ValueError("Invalid delivery ID format")

        self._http.request("POST", f"/webhooks/{webhook_id}/deliveries/{delivery_id}/retry")

    def list_event_types(self) -> List[str]:
        """
        List available event types.

        Returns:
            Array of event type strings
        """
        response = self._http.request("GET", "/webhooks/event-types")
        return [e["type"] for e in response.get("events", [])]


class AsyncWebhooksResource:
    """
    Webhooks API resource (asynchronous)

    Async version of the webhooks resource for use with asyncio.
    """

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def create(
        self,
        url: str,
        events: List[str],
        description: Optional[str] = None,
        mode: Optional[WebhookMode] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WebhookCreatedResponse:
        """Create a new webhook endpoint."""
        if not url or not url.startswith("https://"):
            raise ValueError("Webhook URL must be HTTPS")

        if not events:
            raise ValueError("At least one event type is required")

        body = {"url": url, "events": events}
        if description:
            body["description"] = description
        if mode:
            body["mode"] = mode.value if isinstance(mode, WebhookMode) else mode
        if metadata:
            body["metadata"] = metadata

        response = await self._http.request("POST", "/webhooks", json=body)
        return WebhookCreatedResponse(**_transform_webhook_response(response))

    async def list(self) -> List[Webhook]:
        """List all webhooks."""
        response = await self._http.request("GET", "/webhooks")
        return [Webhook(**_transform_webhook_response(w)) for w in response]

    async def get(self, webhook_id: str) -> Webhook:
        """Get a specific webhook by ID."""
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = await self._http.request("GET", f"/webhooks/{webhook_id}")
        return Webhook(**_transform_webhook_response(response))

    async def update(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        mode: Optional[WebhookMode] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Webhook:
        """Update a webhook configuration."""
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        if url and not url.startswith("https://"):
            raise ValueError("Webhook URL must be HTTPS")

        body = {}
        if url is not None:
            body["url"] = url
        if events is not None:
            body["events"] = events
        if description is not None:
            body["description"] = description
        if is_active is not None:
            body["is_active"] = is_active
        if mode is not None:
            body["mode"] = mode.value if isinstance(mode, WebhookMode) else mode
        if metadata is not None:
            body["metadata"] = metadata

        response = await self._http.request("PATCH", f"/webhooks/{webhook_id}", json=body)
        return Webhook(**_transform_webhook_response(response))

    async def delete(self, webhook_id: str) -> None:
        """Delete a webhook."""
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        await self._http.request("DELETE", f"/webhooks/{webhook_id}")

    async def test(self, webhook_id: str) -> WebhookTestResult:
        """Send a test event to a webhook endpoint."""
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = await self._http.request("POST", f"/webhooks/{webhook_id}/test")
        return WebhookTestResult(**response)

    async def rotate_secret(self, webhook_id: str) -> WebhookSecretRotation:
        """Rotate the webhook signing secret."""
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = await self._http.request("POST", f"/webhooks/{webhook_id}/rotate-secret")
        if "webhook" in response:
            response["webhook"] = _transform_webhook_response(response["webhook"])
        return WebhookSecretRotation(**response)

    async def get_deliveries(self, webhook_id: str) -> List[WebhookDelivery]:
        """Get delivery history for a webhook."""
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = await self._http.request("GET", f"/webhooks/{webhook_id}/deliveries")
        return [WebhookDelivery(**_transform_delivery_response(d)) for d in response]

    async def retry_delivery(self, webhook_id: str, delivery_id: str) -> None:
        """Retry a failed delivery."""
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")
        if not delivery_id or not delivery_id.startswith("del_"):
            raise ValueError("Invalid delivery ID format")

        await self._http.request("POST", f"/webhooks/{webhook_id}/deliveries/{delivery_id}/retry")

    async def list_event_types(self) -> List[str]:
        """List available event types."""
        response = await self._http.request("GET", "/webhooks/event-types")
        return [e["type"] for e in response.get("events", [])]
