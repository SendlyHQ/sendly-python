"""
Webhooks Resource

Manage webhook endpoints for receiving real-time message status updates.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError
from ..types import (
    ApiErrorResponse,
    CreateWebhookOptions,
    DeliveryStatus,
    UpdateWebhookOptions,
    Webhook,
    WebhookCreatedResponse,
    WebhookDelivery,
    WebhookMode,
    WebhookSecretRotation,
    WebhookTestResult,
)
from ..utils.http import AsyncHttpClient, HttpClient
from urllib.parse import quote


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


def _check_create_input(url: str, events: List[str]) -> None:
    if not url or not url.startswith("https://"):
        raise ValueError("Webhook URL must be HTTPS")
    if not events:
        raise ValueError("At least one event type is required")


def _deliveries_params(
    limit: Optional[int],
    offset: Optional[int],
    status: Optional[Union[DeliveryStatus, str]],
) -> Optional[Dict[str, Any]]:
    params: Dict[str, Any] = {}
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    if status is not None:
        params["status"] = status.value if isinstance(status, DeliveryStatus) else status
    return params or None


def _parse_deliveries(response: Any) -> List[WebhookDelivery]:
    items = response.get("deliveries", []) if isinstance(response, dict) else response
    try:
        return [WebhookDelivery(**_transform_delivery_response(d)) for d in items]
    except PydanticValidationError as e:
        raise SendlyError(
            message=f"Invalid API response format: {e}",
            code="invalid_response",
            status_code=200,
        ) from e


def _transform_test_response(data: Dict[str, Any]) -> Dict[str, Any]:
    delivery = data.get("delivery")
    if not isinstance(delivery, dict):
        return data
    result = dict(data)
    result.setdefault("statusCode", delivery.get("status_code"))
    result.setdefault("responseTimeMs", delivery.get("response_time"))
    result.setdefault("error", delivery.get("error"))
    return result


def _parse_rotation(response: Dict[str, Any]) -> WebhookSecretRotation:
    if isinstance(response.get("webhook"), dict):
        response = {**response, "webhook": _transform_webhook_response(response["webhook"])}
    try:
        return WebhookSecretRotation(**response)
    except PydanticValidationError as e:
        body = {k: v for k, v in response.items() if k not in ("error", "message")}
        raise SendlyError(
            message=f"Invalid API response format: {e}",
            code="invalid_response",
            status_code=200,
            response=ApiErrorResponse(
                error="invalid_response", message=str(response.get("message", "")), **body
            ),
        ) from e


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
            ValueError: If the URL is not HTTPS or events are empty
            AuthenticationError: If the API key is invalid
        """
        _check_create_input(url, events)

        body = {"url": url, "events": events}
        if description:
            body["description"] = description
        if mode:
            body["mode"] = mode.value if isinstance(mode, WebhookMode) else mode
        if metadata:
            body["metadata"] = metadata

        response = self._http.request("POST", "/webhooks", body=body)
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

        response = self._http.request("GET", f"/webhooks/{quote(webhook_id, safe='')}")
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

        response = self._http.request("PATCH", f"/webhooks/{quote(webhook_id, safe='')}", body=body)
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

        self._http.request("DELETE", f"/webhooks/{quote(webhook_id, safe='')}")

    def test(self, webhook_id: str) -> WebhookTestResult:
        """
        Send a test event to a webhook endpoint.

        Args:
            webhook_id: Webhook ID

        Returns:
            Test result with the endpoint's status code and response time

        Raises:
            SendlyError: When the endpoint did not accept the test event (an
                error status, a timeout or no answer); the message says why
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = self._http.request("POST", f"/webhooks/{quote(webhook_id, safe='')}/test")
        return WebhookTestResult(**_transform_test_response(response))

    def reset_circuit(self, webhook_id: str) -> dict:
        """
        Reset the circuit breaker for a webhook.

        Manually resets an open circuit breaker so deliveries resume immediately
        instead of waiting for the automatic 5-minute recovery.

        Args:
            webhook_id: Webhook ID

        Returns:
            Reset confirmation with updated webhook
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        return self._http.request("POST", f"/webhooks/{quote(webhook_id, safe='')}/reset-circuit")

    def redeliver(
        self,
        webhook_id: str,
        *,
        since: Optional[str] = None,
        until: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """
        Replay failed or cancelled webhook deliveries from the audit log.

        Use after a customer endpoint has recovered from an outage to re-fire
        deliveries that we recorded but couldn't deliver. Each replay creates
        a new delivery row preserving the original ``event_id`` so customers
        can dedupe.

        Rejects with HTTP 409 if the circuit is currently open — call
        :meth:`reset_circuit` first.

        Args:
            webhook_id: Webhook ID
            since: Earliest delivery created_at, ISO-8601 (default: now − 24h)
            until: Latest delivery created_at, ISO-8601 (default: now)
            event_types: Filter by event type (default: all)
            statuses: Replay deliveries in any of these statuses
                (default: ``["failed", "cancelled"]``)
            limit: Maximum number of deliveries to requeue
                (default 1000, max 10000)

        Returns:
            Counts of requeued deliveries plus the new delivery IDs
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        body: dict = {}
        if since is not None:
            body["since"] = since
        if until is not None:
            body["until"] = until
        if event_types is not None:
            body["event_types"] = event_types
        if statuses is not None:
            body["statuses"] = statuses
        if limit is not None:
            body["limit"] = limit

        return self._http.request(
            "POST", f"/webhooks/{quote(webhook_id, safe='')}/redeliver", body=body or None
        )

    def backfill(
        self,
        webhook_id: str,
        *,
        since: Optional[str] = None,
        until: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """
        Backfill missed webhook events from the underlying message log.

        Use this when a circuit-breaker outage left events with no audit row
        (the case :meth:`redeliver` cannot recover). The endpoint scans the
        ``messages`` table for the window and synthesizes a webhook delivery
        for any message whose ``message.sent`` / ``message.delivered`` /
        ``message.failed`` event has not been successfully delivered yet.

        Synthesized message events carry the same event id the original
        dispatch used, so dedupe on ``event.id``. Do not dedupe on
        ``event.data.object.id``: a message's sent and delivered events share it.

        Rejects with HTTP 409 if the circuit is currently open — call
        :meth:`reset_circuit` first.

        Args:
            webhook_id: Webhook ID
            since: Earliest message created_at, ISO-8601 (default: now − 24h)
            until: Latest message created_at, ISO-8601 (default: now)
            event_types: Filter by event type
                (default: subscribed message events)
            limit: Maximum events to synthesize (default 1000, max 10000)

        Returns:
            Counts grouped by event type plus the new delivery IDs
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        body: dict = {}
        if since is not None:
            body["since"] = since
        if until is not None:
            body["until"] = until
        if event_types is not None:
            body["event_types"] = event_types
        if limit is not None:
            body["limit"] = limit

        return self._http.request(
            "POST", f"/webhooks/{quote(webhook_id, safe='')}/backfill", body=body or None
        )

    def rotate_secret(self, webhook_id: str) -> WebhookSecretRotation:
        """
        Rotate the webhook signing secret.

        Deliveries are signed with the new secret as soon as this returns, so
        have your endpoint accept both the old and the new secret until the
        new one is deployed.

        Args:
            webhook_id: Webhook ID

        Returns:
            The new secret (shown only once) and when it was rotated

        Raises:
            SendlyError: With code ``invalid_response`` when the response
                cannot be read; ``e.response.model_extra`` still holds the
                body, new secret included
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = self._http.request("POST", f"/webhooks/{quote(webhook_id, safe='')}/rotate-secret")
        return _parse_rotation(response)

    def get_deliveries(
        self,
        webhook_id: str,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[Union[DeliveryStatus, str]] = None,
    ) -> List[WebhookDelivery]:
        """
        Get delivery history for a webhook, newest first.

        Args:
            webhook_id: Webhook ID
            limit: Maximum number of deliveries to return
            offset: Number of deliveries to skip
            status: Only return deliveries in this status: a DeliveryStatus or
                its value (pending, delivered, failed or cancelled)

        Returns:
            Array of delivery attempts
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = self._http.request(
            "GET",
            f"/webhooks/{quote(webhook_id, safe='')}/deliveries",
            params=_deliveries_params(limit, offset, status),
        )
        return _parse_deliveries(response)

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

        self._http.request("POST", f"/webhooks/{quote(webhook_id, safe='')}/deliveries/{quote(delivery_id, safe='')}/retry")

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
        _check_create_input(url, events)

        body = {"url": url, "events": events}
        if description:
            body["description"] = description
        if mode:
            body["mode"] = mode.value if isinstance(mode, WebhookMode) else mode
        if metadata:
            body["metadata"] = metadata

        response = await self._http.request("POST", "/webhooks", body=body)
        return WebhookCreatedResponse(**_transform_webhook_response(response))

    async def list(self) -> List[Webhook]:
        """List all webhooks."""
        response = await self._http.request("GET", "/webhooks")
        return [Webhook(**_transform_webhook_response(w)) for w in response]

    async def get(self, webhook_id: str) -> Webhook:
        """Get a specific webhook by ID."""
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = await self._http.request("GET", f"/webhooks/{quote(webhook_id, safe='')}")
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

        response = await self._http.request("PATCH", f"/webhooks/{quote(webhook_id, safe='')}", body=body)
        return Webhook(**_transform_webhook_response(response))

    async def delete(self, webhook_id: str) -> None:
        """Delete a webhook."""
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        await self._http.request("DELETE", f"/webhooks/{quote(webhook_id, safe='')}")

    async def test(self, webhook_id: str) -> WebhookTestResult:
        """Send a test event to a webhook endpoint."""
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = await self._http.request("POST", f"/webhooks/{quote(webhook_id, safe='')}/test")
        return WebhookTestResult(**_transform_test_response(response))

    async def reset_circuit(self, webhook_id: str) -> dict:
        """Reset the circuit breaker for a webhook."""
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        return await self._http.request("POST", f"/webhooks/{quote(webhook_id, safe='')}/reset-circuit")

    async def redeliver(
        self,
        webhook_id: str,
        *,
        since: Optional[str] = None,
        until: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Replay failed/cancelled webhook deliveries from the audit log.

        See :meth:`WebhooksResource.redeliver` for details.
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        body: dict = {}
        if since is not None:
            body["since"] = since
        if until is not None:
            body["until"] = until
        if event_types is not None:
            body["event_types"] = event_types
        if statuses is not None:
            body["statuses"] = statuses
        if limit is not None:
            body["limit"] = limit

        return await self._http.request(
            "POST", f"/webhooks/{quote(webhook_id, safe='')}/redeliver", body=body or None
        )

    async def backfill(
        self,
        webhook_id: str,
        *,
        since: Optional[str] = None,
        until: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Backfill missed webhook events from the underlying message log.

        See :meth:`WebhooksResource.backfill` for details.
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        body: dict = {}
        if since is not None:
            body["since"] = since
        if until is not None:
            body["until"] = until
        if event_types is not None:
            body["event_types"] = event_types
        if limit is not None:
            body["limit"] = limit

        return await self._http.request(
            "POST", f"/webhooks/{quote(webhook_id, safe='')}/backfill", body=body or None
        )

    async def rotate_secret(self, webhook_id: str) -> WebhookSecretRotation:
        """Rotate the webhook signing secret.

        Deliveries are signed with the new secret as soon as this returns.
        See :meth:`WebhooksResource.rotate_secret`.
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = await self._http.request("POST", f"/webhooks/{quote(webhook_id, safe='')}/rotate-secret")
        return _parse_rotation(response)

    async def get_deliveries(
        self,
        webhook_id: str,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[Union[DeliveryStatus, str]] = None,
    ) -> List[WebhookDelivery]:
        """Get delivery history for a webhook, newest first.

        See :meth:`WebhooksResource.get_deliveries` for the filters.
        """
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")

        response = await self._http.request(
            "GET",
            f"/webhooks/{quote(webhook_id, safe='')}/deliveries",
            params=_deliveries_params(limit, offset, status),
        )
        return _parse_deliveries(response)

    async def retry_delivery(self, webhook_id: str, delivery_id: str) -> None:
        """Retry a failed delivery."""
        if not webhook_id or not webhook_id.startswith("whk_"):
            raise ValueError("Invalid webhook ID format")
        if not delivery_id or not delivery_id.startswith("del_"):
            raise ValueError("Invalid delivery ID format")

        await self._http.request("POST", f"/webhooks/{quote(webhook_id, safe='')}/deliveries/{quote(delivery_id, safe='')}/retry")

    async def list_event_types(self) -> List[str]:
        """List available event types."""
        response = await self._http.request("GET", "/webhooks/event-types")
        return [e["type"] for e in response.get("events", [])]
