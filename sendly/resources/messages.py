"""
Messages Resource

API resource for sending and managing SMS messages.
"""

from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError
from ..types import (
    BatchListResponse,
    BatchMessageResponse,
    CancelledMessageResponse,
    ListMessagesOptions,
    Message,
    MessageListResponse,
    ScheduledMessage,
    ScheduledMessageListResponse,
    SendMessageRequest,
)
from ..utils.http import AsyncHttpClient, HttpClient
from ..utils.validation import (
    validate_limit,
    validate_message_id,
    validate_message_text,
    validate_phone_number,
    validate_sender_id,
)


class MessagesResource:
    """
    Messages API resource (synchronous)

    Example:
        >>> client = Sendly('sk_live_v1_xxx')
        >>> message = client.messages.send(to='+15551234567', text='Hello!')
        >>> messages = client.messages.list(limit=10)
        >>> msg = client.messages.get('msg_xxx')
    """

    def __init__(self, http: HttpClient):
        self._http = http

    def send(
        self,
        to: str,
        text: str,
        from_: Optional[str] = None,
        message_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Message:
        """
        Send an SMS message

        Args:
            to: Destination phone number in E.164 format (e.g., +15551234567)
            text: Message content
            from_: Optional sender ID or phone number
            message_type: Message type for compliance - 'marketing' (default, subject to quiet hours) or 'transactional' (24/7)

        Returns:
            The created message

        Raises:
            ValidationError: If the request is invalid
            InsufficientCreditsError: If credit balance is too low
            AuthenticationError: If the API key is invalid
            RateLimitError: If rate limit is exceeded

        Example:
            >>> message = client.messages.send(
            ...     to='+15551234567',
            ...     text='Your code is: 123456'
            ... )
            >>> print(message.id)
            >>> print(message.status)
        """
        # Validate inputs
        validate_phone_number(to)
        validate_message_text(text)
        if from_:
            validate_sender_id(from_)

        # Build request body
        body: Dict[str, Any] = {
            "to": to,
            "text": text,
        }
        if from_:
            body["from"] = from_
        if message_type:
            body["messageType"] = message_type

        # Make API request
        data = self._http.request(
            method="POST",
            path="/messages",
            body=body,
        )

        try:
            return Message(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def list(
        self,
        limit: Optional[int] = None,
        **kwargs: Any,
    ) -> MessageListResponse:
        """
        List sent messages

        Args:
            limit: Maximum number of messages to return (1-100, default 50)

        Returns:
            Paginated list of messages

        Raises:
            AuthenticationError: If the API key is invalid
            RateLimitError: If rate limit is exceeded

        Example:
            >>> result = client.messages.list(limit=10)
            >>> for msg in result.data:
            ...     print(f'{msg.to}: {msg.status}')
        """
        # Validate inputs
        validate_limit(limit)

        # Build query params
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit

        # Make API request
        data = self._http.request(
            method="GET",
            path="/messages",
            params=params if params else None,
        )

        try:
            return MessageListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def get(self, id: str) -> Message:
        """
        Get a specific message by ID

        Args:
            id: Message ID

        Returns:
            The message details

        Raises:
            NotFoundError: If the message doesn't exist
            AuthenticationError: If the API key is invalid
            RateLimitError: If rate limit is exceeded

        Example:
            >>> message = client.messages.get('msg_xxx')
            >>> print(message.status)
            >>> print(message.delivered_at)
        """
        # Validate ID
        validate_message_id(id)

        # Make API request
        data = self._http.request(
            method="GET",
            path=f"/messages/{quote(id, safe='')}",
        )

        try:
            return Message(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def list_all(
        self,
        batch_size: int = 100,
        **kwargs: Any,
    ):
        """
        Iterate through all messages with automatic pagination

        Args:
            batch_size: Number of messages to fetch per request (max 100)

        Yields:
            Message objects one at a time

        Raises:
            AuthenticationError: If the API key is invalid
            RateLimitError: If rate limit is exceeded

        Example:
            >>> for message in client.messages.list_all():
            ...     print(f'{message.id}: {message.status}')
        """
        batch_size = min(batch_size, 100)
        offset = 0

        while True:
            data = self._http.request(
                method="GET",
                path="/messages",
                params={"limit": batch_size, "offset": offset},
            )

            try:
                response = MessageListResponse(**data)
            except PydanticValidationError as e:
                raise SendlyError(
                    message=f"Invalid API response format: {e}",
                    code="invalid_response",
                    status_code=200,
                ) from e

            for message in response.data:
                yield message

            if len(response.data) < batch_size:
                break

            offset += batch_size

    # =========================================================================
    # Scheduled Messages
    # =========================================================================

    def schedule(
        self,
        to: str,
        text: str,
        scheduled_at: str,
        from_: Optional[str] = None,
        message_type: Optional[str] = None,
        **kwargs: Any,
    ) -> ScheduledMessage:
        """
        Schedule an SMS message for future delivery

        Args:
            to: Destination phone number in E.164 format
            text: Message content
            scheduled_at: When to send (ISO 8601, must be > 1 minute in future)
            from_: Optional sender ID (for international destinations only)
            message_type: Message type for compliance - 'marketing' (default, subject to quiet hours) or 'transactional' (24/7)

        Returns:
            The scheduled message

        Example:
            >>> scheduled = client.messages.schedule(
            ...     to='+15551234567',
            ...     text='Your appointment reminder!',
            ...     scheduled_at='2025-01-20T10:00:00Z'
            ... )
            >>> print(scheduled.id)
            >>> print(scheduled.status)
        """
        validate_phone_number(to)
        validate_message_text(text)
        if from_:
            validate_sender_id(from_)

        body: Dict[str, Any] = {
            "to": to,
            "text": text,
            "scheduledAt": scheduled_at,
        }
        if from_:
            body["from"] = from_
        if message_type:
            body["messageType"] = message_type

        data = self._http.request(
            method="POST",
            path="/messages/schedule",
            body=body,
        )

        try:
            return ScheduledMessage(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def list_scheduled(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
        **kwargs: Any,
    ) -> ScheduledMessageListResponse:
        """
        List scheduled messages

        Args:
            limit: Maximum number of messages to return (1-100)
            offset: Number of messages to skip
            status: Filter by status

        Returns:
            Paginated list of scheduled messages
        """
        validate_limit(limit)

        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status

        data = self._http.request(
            method="GET",
            path="/messages/scheduled",
            params=params if params else None,
        )

        try:
            return ScheduledMessageListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def get_scheduled(self, id: str) -> ScheduledMessage:
        """
        Get a specific scheduled message by ID

        Args:
            id: Message ID

        Returns:
            The scheduled message details
        """
        validate_message_id(id)

        data = self._http.request(
            method="GET",
            path=f"/messages/scheduled/{quote(id, safe='')}",
        )

        try:
            return ScheduledMessage(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def cancel_scheduled(self, id: str) -> CancelledMessageResponse:
        """
        Cancel a scheduled message

        Args:
            id: Message ID to cancel

        Returns:
            Cancellation confirmation with refunded credits
        """
        validate_message_id(id)

        data = self._http.request(
            method="DELETE",
            path=f"/messages/scheduled/{quote(id, safe='')}",
        )

        try:
            return CancelledMessageResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    # =========================================================================
    # Batch Messages
    # =========================================================================

    def send_batch(
        self,
        messages: List[Dict[str, str]],
        from_: Optional[str] = None,
        message_type: Optional[str] = None,
        **kwargs: Any,
    ) -> BatchMessageResponse:
        """
        Send multiple SMS messages in a single batch

        Args:
            messages: List of dicts with 'to' and 'text' keys (max 1000)
            from_: Optional sender ID (for international destinations only)
            message_type: Message type for compliance - 'marketing' (default, subject to quiet hours) or 'transactional' (24/7)

        Returns:
            Batch response with individual message results

        Example:
            >>> batch = client.messages.send_batch(
            ...     messages=[
            ...         {'to': '+15551234567', 'text': 'Hello User 1!'},
            ...         {'to': '+15559876543', 'text': 'Hello User 2!'}
            ...     ]
            ... )
            >>> print(batch.batch_id)
            >>> print(batch.queued)
        """
        if not messages or not isinstance(messages, list):
            raise SendlyError(
                message="messages must be a non-empty list",
                code="invalid_request",
                status_code=400,
            )

        if len(messages) > 1000:
            raise SendlyError(
                message="Maximum 1000 messages per batch",
                code="invalid_request",
                status_code=400,
            )

        for msg in messages:
            validate_phone_number(msg.get("to", ""))
            validate_message_text(msg.get("text", ""))

        if from_:
            validate_sender_id(from_)

        body: Dict[str, Any] = {"messages": messages}
        if from_:
            body["from"] = from_
        if message_type:
            body["messageType"] = message_type

        data = self._http.request(
            method="POST",
            path="/messages/batch",
            body=body,
        )

        try:
            return BatchMessageResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def get_batch(self, batch_id: str) -> BatchMessageResponse:
        """
        Get batch status and results

        Args:
            batch_id: Batch ID

        Returns:
            Batch details with message results
        """
        if not batch_id or not batch_id.startswith("batch_"):
            raise SendlyError(
                message="Invalid batch ID format",
                code="invalid_request",
                status_code=400,
            )

        data = self._http.request(
            method="GET",
            path=f"/messages/batch/{quote(batch_id, safe='')}",
        )

        try:
            return BatchMessageResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    def list_batches(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
        **kwargs: Any,
    ) -> BatchListResponse:
        """
        List message batches

        Args:
            limit: Maximum number of batches to return (1-100)
            offset: Number of batches to skip
            status: Filter by status

        Returns:
            Paginated list of batches
        """
        validate_limit(limit)

        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status

        data = self._http.request(
            method="GET",
            path="/messages/batches",
            params=params if params else None,
        )

        try:
            return BatchListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e


class AsyncMessagesResource:
    """
    Messages API resource (asynchronous)

    Example:
        >>> async with AsyncSendly('sk_live_v1_xxx') as client:
        ...     message = await client.messages.send(to='+15551234567', text='Hello!')
        ...     messages = await client.messages.list(limit=10)
    """

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def send(
        self,
        to: str,
        text: str,
        from_: Optional[str] = None,
        message_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Message:
        """
        Send an SMS message (async)

        Args:
            to: Destination phone number in E.164 format
            text: Message content
            from_: Optional sender ID or phone number
            message_type: Message type for compliance - 'marketing' (default, subject to quiet hours) or 'transactional' (24/7)

        Returns:
            The created message

        Example:
            >>> message = await client.messages.send(
            ...     to='+15551234567',
            ...     text='Your code is: 123456'
            ... )
        """
        # Validate inputs
        validate_phone_number(to)
        validate_message_text(text)
        if from_:
            validate_sender_id(from_)

        # Build request body
        body: Dict[str, Any] = {
            "to": to,
            "text": text,
        }
        if from_:
            body["from"] = from_
        if message_type:
            body["messageType"] = message_type

        # Make API request
        data = await self._http.request(
            method="POST",
            path="/messages",
            body=body,
        )

        try:
            return Message(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def list(
        self,
        limit: Optional[int] = None,
        **kwargs: Any,
    ) -> MessageListResponse:
        """
        List sent messages (async)

        Args:
            limit: Maximum number of messages to return (1-100)

        Returns:
            Paginated list of messages

        Example:
            >>> result = await client.messages.list(limit=10)
            >>> for msg in result.data:
            ...     print(f'{msg.to}: {msg.status}')
        """
        # Validate inputs
        validate_limit(limit)

        # Build query params
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit

        # Make API request
        data = await self._http.request(
            method="GET",
            path="/messages",
            params=params if params else None,
        )

        try:
            return MessageListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def get(self, id: str) -> Message:
        """
        Get a specific message by ID (async)

        Args:
            id: Message ID

        Returns:
            The message details

        Example:
            >>> message = await client.messages.get('msg_xxx')
            >>> print(message.status)
        """
        # Validate ID
        validate_message_id(id)

        # Make API request
        data = await self._http.request(
            method="GET",
            path=f"/messages/{quote(id, safe='')}",
        )

        try:
            return Message(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def list_all(
        self,
        batch_size: int = 100,
        **kwargs: Any,
    ):
        """
        Iterate through all messages with automatic pagination (async)

        Args:
            batch_size: Number of messages to fetch per request (max 100)

        Yields:
            Message objects one at a time

        Raises:
            AuthenticationError: If the API key is invalid
            RateLimitError: If rate limit is exceeded

        Example:
            >>> async for message in client.messages.list_all():
            ...     print(f'{message.id}: {message.status}')
        """
        batch_size = min(batch_size, 100)
        offset = 0

        while True:
            data = await self._http.request(
                method="GET",
                path="/messages",
                params={"limit": batch_size, "offset": offset},
            )

            try:
                response = MessageListResponse(**data)
            except PydanticValidationError as e:
                raise SendlyError(
                    message=f"Invalid API response format: {e}",
                    code="invalid_response",
                    status_code=200,
                ) from e

            for message in response.data:
                yield message

            if len(response.data) < batch_size:
                break

            offset += batch_size

    # =========================================================================
    # Scheduled Messages
    # =========================================================================

    async def schedule(
        self,
        to: str,
        text: str,
        scheduled_at: str,
        from_: Optional[str] = None,
        message_type: Optional[str] = None,
        **kwargs: Any,
    ) -> ScheduledMessage:
        """
        Schedule an SMS message for future delivery (async)

        Args:
            to: Destination phone number in E.164 format
            text: Message content
            scheduled_at: When to send (ISO 8601, must be > 1 minute in future)
            from_: Optional sender ID (for international destinations only)
            message_type: Message type for compliance - 'marketing' (default, subject to quiet hours) or 'transactional' (24/7)

        Returns:
            The scheduled message
        """
        validate_phone_number(to)
        validate_message_text(text)
        if from_:
            validate_sender_id(from_)

        body: Dict[str, Any] = {
            "to": to,
            "text": text,
            "scheduledAt": scheduled_at,
        }
        if from_:
            body["from"] = from_
        if message_type:
            body["messageType"] = message_type

        data = await self._http.request(
            method="POST",
            path="/messages/schedule",
            body=body,
        )

        try:
            return ScheduledMessage(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def list_scheduled(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
        **kwargs: Any,
    ) -> ScheduledMessageListResponse:
        """List scheduled messages (async)"""
        validate_limit(limit)

        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status

        data = await self._http.request(
            method="GET",
            path="/messages/scheduled",
            params=params if params else None,
        )

        try:
            return ScheduledMessageListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def get_scheduled(self, id: str) -> ScheduledMessage:
        """Get a specific scheduled message by ID (async)"""
        validate_message_id(id)

        data = await self._http.request(
            method="GET",
            path=f"/messages/scheduled/{quote(id, safe='')}",
        )

        try:
            return ScheduledMessage(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def cancel_scheduled(self, id: str) -> CancelledMessageResponse:
        """Cancel a scheduled message (async)"""
        validate_message_id(id)

        data = await self._http.request(
            method="DELETE",
            path=f"/messages/scheduled/{quote(id, safe='')}",
        )

        try:
            return CancelledMessageResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    # =========================================================================
    # Batch Messages
    # =========================================================================

    async def send_batch(
        self,
        messages: List[Dict[str, str]],
        from_: Optional[str] = None,
        message_type: Optional[str] = None,
        **kwargs: Any,
    ) -> BatchMessageResponse:
        """Send multiple SMS messages in a single batch (async)"""
        if not messages or not isinstance(messages, list):
            raise SendlyError(
                message="messages must be a non-empty list",
                code="invalid_request",
                status_code=400,
            )

        if len(messages) > 1000:
            raise SendlyError(
                message="Maximum 1000 messages per batch",
                code="invalid_request",
                status_code=400,
            )

        for msg in messages:
            validate_phone_number(msg.get("to", ""))
            validate_message_text(msg.get("text", ""))

        if from_:
            validate_sender_id(from_)

        body: Dict[str, Any] = {"messages": messages}
        if from_:
            body["from"] = from_
        if message_type:
            body["messageType"] = message_type

        data = await self._http.request(
            method="POST",
            path="/messages/batch",
            body=body,
        )

        try:
            return BatchMessageResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def get_batch(self, batch_id: str) -> BatchMessageResponse:
        """Get batch status and results (async)"""
        if not batch_id or not batch_id.startswith("batch_"):
            raise SendlyError(
                message="Invalid batch ID format",
                code="invalid_request",
                status_code=400,
            )

        data = await self._http.request(
            method="GET",
            path=f"/messages/batch/{quote(batch_id, safe='')}",
        )

        try:
            return BatchMessageResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    async def list_batches(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
        **kwargs: Any,
    ) -> BatchListResponse:
        """List message batches (async)"""
        validate_limit(limit)

        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status

        data = await self._http.request(
            method="GET",
            path="/messages/batches",
            params=params if params else None,
        )

        try:
            return BatchListResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e
