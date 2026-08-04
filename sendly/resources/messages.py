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
    EnhanceMessageResponse,
    GroupMessageResponse,
    ListMessagesOptions,
    Message,
    MessageListResponse,
    RcsMessage,
    ScheduledMessage,
    ScheduledMessageListResponse,
    SendMessageRequest,
    WhatsAppMessage,
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
        text: Optional[str] = None,
        from_: Optional[str] = None,
        message_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        media_urls: Optional[List[str]] = None,
        channel: Optional[str] = None,
        template: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        card: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[Dict[str, Any]]] = None,
        fallback_to_sms: Optional[bool] = None,
        **kwargs: Any,
    ) -> Union[Message, WhatsAppMessage, RcsMessage]:
        """
        Send an SMS, WhatsApp, or RCS message

        Pass ``channel='whatsapp'`` to send on WhatsApp. WhatsApp sends
        require a live API key and a ``from_`` number with an active WhatsApp
        connection (see ``client.whatsapp.signup``). Free-form ``text`` and
        media only deliver inside an open 24-hour customer-service window -
        outside it, send an approved ``template`` instead (check with
        ``client.whatsapp.window()``).

        Pass ``channel='rcs'`` to send on RCS. RCS sends require a live API
        key and a sendable RCS agent on your workspace (see
        ``client.rcs.agents``). Provide exactly one of ``text`` (optionally
        with ``suggestions`` chips) or ``card``. When the recipient doesn't
        support RCS, text sends fall back to SMS automatically - check
        ``message.channel`` (or ``message.fell_back_to``) on the response to
        tell which leg delivered. Rich cards have no SMS form and respond
        422 instead.

        Args:
            to: Destination phone number in E.164 format (e.g., +15551234567)
            text: Message content. On WhatsApp: free-form text (max 4096
                bytes), or the caption when media_urls is provided (max 1024
                bytes); requires an open 24-hour window. On RCS: the message
                body - provide this or card, never both
            from_: Optional sender ID or phone number. Required on WhatsApp -
                must be a number with an active WhatsApp connection. Ignored
                on RCS (the agent is the sender)
            message_type: Message type for compliance - 'marketing' (default, subject to quiet hours) or 'transactional' (24/7)
            metadata: Custom JSON metadata to attach to the message (max 4KB)
            media_urls: URLs of media files to attach. WhatsApp accepts
                exactly one per message
            channel: Omit (or 'sms') for SMS; 'whatsapp' to send on WhatsApp;
                'rcs' to send on RCS
            template: Approved WhatsApp template to send, works regardless of
                the 24-hour window: {'name': 'order_shipped', 'language':
                'en_US', 'variables': {'1': 'Acme Inc', '2': '#4821'}}
                (optional 'buttons' for dynamic-URL button variables)
            agent_id: RCS only - the agent to send as. Optional when your
                workspace has exactly one agent; required when it has several
            card: RCS only - a rich card:
                {'title': 'Your order shipped', 'description': 'Arriving
                Thursday', 'mediaUrl': 'https://example.com/box.jpg',
                'orientation': 'vertical', 'suggestions': [...]}.
                ``title`` and ``description`` are both required. Provide this
                or text, never both
            suggestions: RCS only - suggestion chips for a text message:
                [{'reply': {'text': 'On my way', 'postbackData': 'omw'}},
                {'action': {'text': 'Track it', 'postbackData': 'track',
                'url': 'https://example.com/track'}}]. Card buttons go in
                card['suggestions'] instead. Dropped (and disclosed via
                message.rcs.suggestions_dropped) when the send falls back
            fallback_to_sms: RCS only - deliver as SMS when the recipient
                doesn't support RCS (default True). Pass False to get a 422
                rcs_not_supported_for_recipient instead

        Returns:
            The created message (a WhatsAppMessage when channel='whatsapp',
            an RcsMessage when channel='rcs')

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

        WhatsApp example:
            >>> message = client.messages.send(
            ...     channel='whatsapp',
            ...     to='+15551234567',
            ...     from_='+15559876543',
            ...     template={
            ...         'name': 'order_shipped',
            ...         'language': 'en_US',
            ...         'variables': {'1': 'Acme Inc', '2': '#4821'},
            ...     },
            ... )
            >>> print(message.whatsapp.kind)  # 'template'

        RCS example:
            >>> message = client.messages.send(
            ...     channel='rcs',
            ...     to='+15551234567',
            ...     text='Your table is ready!',
            ...     suggestions=[
            ...         {'reply': {'text': 'On my way', 'postbackData': 'omw'}},
            ...     ],
            ... )
            >>> if message.channel == 'rcs':
            ...     print(message.rcs.agent_name)  # delivered over RCS
            ... else:
            ...     print(message.fell_back_to)    # 'sms'
        """
        # Validate inputs
        validate_phone_number(to)

        if channel == "rcs":
            data = self._http.request(
                method="POST",
                path="/messages",
                body=_rcs_send_body(
                    to, text, agent_id, card, suggestions, fallback_to_sms, metadata
                ),
            )

            try:
                return RcsMessage(**data)
            except PydanticValidationError as e:
                raise SendlyError(
                    message=f"Invalid API response format: {e}",
                    code="invalid_response",
                    status_code=200,
                ) from e

        if channel == "whatsapp":
            validate_phone_number(from_ or "")
            has_media = bool(media_urls)
            if not text and not has_media and not template:
                raise SendlyError(
                    message="Provide 'text', 'media_urls', or 'template'",
                    code="invalid_request",
                    status_code=400,
                )

            body: Dict[str, Any] = {
                "channel": "whatsapp",
                "to": to,
                "from": from_,
            }
            if text is not None:
                body["text"] = text
            if has_media:
                body["mediaUrls"] = media_urls
            if template:
                body["template"] = template
            if metadata:
                body["metadata"] = metadata

            data = self._http.request(
                method="POST",
                path="/messages",
                body=body,
            )

            try:
                return WhatsAppMessage(**data)
            except PydanticValidationError as e:
                raise SendlyError(
                    message=f"Invalid API response format: {e}",
                    code="invalid_response",
                    status_code=200,
                ) from e

        validate_message_text(text or "")
        if from_:
            validate_sender_id(from_)

        # Build request body
        body = {
            "to": to,
            "text": text,
        }
        if from_:
            body["from"] = from_
        if message_type:
            body["messageType"] = message_type
        if metadata:
            body["metadata"] = metadata
        if media_urls:
            body["mediaUrls"] = media_urls

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
        metadata: Optional[Dict[str, Any]] = None,
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
            metadata: Custom JSON metadata to attach to the message (max 4KB)

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
        if metadata:
            body["metadata"] = metadata

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
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> BatchMessageResponse:
        """
        Send multiple SMS messages in a single batch

        Args:
            messages: List of dicts with 'to' and 'text' keys (max 1000). Each dict can also include 'metadata' for per-message metadata.
            from_: Optional sender ID (for international destinations only)
            message_type: Message type for compliance - 'marketing' (default, subject to quiet hours) or 'transactional' (24/7)
            metadata: Shared metadata for all messages in the batch (max 4KB). Per-message metadata takes priority when merging.

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
        if metadata:
            body["metadata"] = metadata

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

    def preview_batch(
        self,
        messages: List[Dict[str, str]],
        from_: Optional[str] = None,
        message_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Preview a batch without sending (dry run)

        Args:
            messages: List of dicts with 'to' and 'text' keys (max 1000)
            from_: Optional sender ID (for international destinations only)
            message_type: Message type: 'marketing' (default) or 'transactional'

        Returns:
            Preview showing what would happen if batch was sent

        Example:
            >>> preview = client.messages.preview_batch(
            ...     messages=[
            ...         {'to': '+15551234567', 'text': 'Hello User 1!'},
            ...         {'to': '+15559876543', 'text': 'Hello User 2!'}
            ...     ]
            ... )
            >>> print(preview['canSend'])
            >>> print(preview['creditsNeeded'])
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

        return self._http.request(
            method="POST",
            path="/messages/batch/preview",
            body=body,
        )

    # =========================================================================
    # Group MMS
    # =========================================================================

    def send_group(
        self,
        to: List[str],
        text: Optional[str] = None,
        from_: Optional[str] = None,
        media_urls: Optional[List[str]] = None,
        message_type: Optional[str] = None,
        **kwargs: Any,
    ) -> GroupMessageResponse:
        """
        Send a group MMS to 2-8 US/Canada recipients

        Everyone in ``to`` shares one thread and replies fan out to all
        participants. Requires the ``group_mms`` feature (and ``enable_mms``
        when sending media). US/Canada destinations only.

        Args:
            to: 2-8 recipient phone numbers in E.164 format (US/CA only)
            text: Message content (required unless media_urls is provided)
            from_: Optional sender ID or phone number
            media_urls: Optional media URLs for the group MMS
            message_type: 'marketing' or 'transactional' (default)

        Returns:
            The created group message, including a group_message_id

        Example:
            >>> group = client.messages.send_group(
            ...     to=['+14155551234', '+14155555678'],
            ...     text='Dinner at 7?'
            ... )
            >>> print(group.id, group.group_message_id)
        """
        if not isinstance(to, list) or len(to) < 2:
            raise SendlyError(
                message="Group messaging needs at least 2 recipients in 'to'",
                code="invalid_request",
                status_code=400,
            )
        if len(to) > 8:
            raise SendlyError(
                message="Group messaging supports at most 8 recipients",
                code="invalid_request",
                status_code=400,
            )
        for recipient in to:
            validate_phone_number(recipient)
        if not text and not media_urls:
            raise SendlyError(
                message="Provide 'text' or 'media_urls'",
                code="invalid_request",
                status_code=400,
            )
        if from_:
            validate_sender_id(from_)

        body: Dict[str, Any] = {"to": to}
        if text:
            body["text"] = text
        if from_:
            body["from"] = from_
        if media_urls:
            body["mediaUrls"] = media_urls
        if message_type:
            body["messageType"] = message_type

        data = self._http.request(
            method="POST",
            path="/messages/group",
            body=body,
        )

        try:
            return GroupMessageResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    # =========================================================================
    # AI Enhance
    # =========================================================================

    def enhance(
        self,
        text: Optional[str] = None,
        message_type: Optional[str] = None,
        **kwargs: Any,
    ) -> EnhanceMessageResponse:
        """
        Enhance message copy with AI

        Requires the ``ai_classification`` feature. When AI is unavailable the
        original text is returned with an empty explanation.

        Args:
            text: Message text to enhance
            message_type: 'marketing' or 'transactional' to steer the tone

        Returns:
            The enhanced text with a short explanation

        Example:
            >>> result = client.messages.enhance(text='ur order shipped')
            >>> print(result.enhanced)
        """
        if not text and not message_type:
            raise SendlyError(
                message="Provide 'text' or 'message_type'",
                code="invalid_request",
                status_code=400,
            )

        body: Dict[str, Any] = {}
        if text is not None:
            body["text"] = text
        if message_type:
            body["messageType"] = message_type

        data = self._http.request(
            method="POST",
            path="/ai/enhance",
            body=body,
        )

        try:
            return EnhanceMessageResponse(**data)
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
        text: Optional[str] = None,
        from_: Optional[str] = None,
        message_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        media_urls: Optional[List[str]] = None,
        channel: Optional[str] = None,
        template: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        card: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[Dict[str, Any]]] = None,
        fallback_to_sms: Optional[bool] = None,
        **kwargs: Any,
    ) -> Union[Message, WhatsAppMessage, RcsMessage]:
        """
        Send an SMS, WhatsApp, or RCS message (async)

        Pass ``channel='whatsapp'`` to send on WhatsApp, or ``channel='rcs'``
        to send on RCS. See :meth:`MessagesResource.send` for the full
        parameter reference.

        Args:
            to: Destination phone number in E.164 format
            text: Message content. On WhatsApp, free-form text or the media
                caption; requires an open 24-hour window. On RCS, the message
                body - provide this or card, never both
            from_: Optional sender ID or phone number. Required on WhatsApp
            message_type: Message type for compliance - 'marketing' (default, subject to quiet hours) or 'transactional' (24/7)
            metadata: Custom JSON metadata to attach to the message (max 4KB)
            media_urls: URLs of media files to attach. WhatsApp accepts
                exactly one per message
            channel: Omit (or 'sms') for SMS; 'whatsapp' to send on WhatsApp;
                'rcs' to send on RCS
            template: Approved WhatsApp template to send, works regardless of
                the 24-hour window
            agent_id: RCS only - the agent to send as
            card: RCS only - a rich card (title and description required)
            suggestions: RCS only - suggestion chips for a text message
            fallback_to_sms: RCS only - deliver as SMS when the recipient
                doesn't support RCS (default True)

        Returns:
            The created message (a WhatsAppMessage when channel='whatsapp',
            an RcsMessage when channel='rcs')

        Example:
            >>> message = await client.messages.send(
            ...     to='+15551234567',
            ...     text='Your code is: 123456'
            ... )
        """
        # Validate inputs
        validate_phone_number(to)

        if channel == "rcs":
            data = await self._http.request(
                method="POST",
                path="/messages",
                body=_rcs_send_body(
                    to, text, agent_id, card, suggestions, fallback_to_sms, metadata
                ),
            )

            try:
                return RcsMessage(**data)
            except PydanticValidationError as e:
                raise SendlyError(
                    message=f"Invalid API response format: {e}",
                    code="invalid_response",
                    status_code=200,
                ) from e

        if channel == "whatsapp":
            validate_phone_number(from_ or "")
            has_media = bool(media_urls)
            if not text and not has_media and not template:
                raise SendlyError(
                    message="Provide 'text', 'media_urls', or 'template'",
                    code="invalid_request",
                    status_code=400,
                )

            body: Dict[str, Any] = {
                "channel": "whatsapp",
                "to": to,
                "from": from_,
            }
            if text is not None:
                body["text"] = text
            if has_media:
                body["mediaUrls"] = media_urls
            if template:
                body["template"] = template
            if metadata:
                body["metadata"] = metadata

            data = await self._http.request(
                method="POST",
                path="/messages",
                body=body,
            )

            try:
                return WhatsAppMessage(**data)
            except PydanticValidationError as e:
                raise SendlyError(
                    message=f"Invalid API response format: {e}",
                    code="invalid_response",
                    status_code=200,
                ) from e

        validate_message_text(text or "")
        if from_:
            validate_sender_id(from_)

        # Build request body
        body = {
            "to": to,
            "text": text,
        }
        if from_:
            body["from"] = from_
        if message_type:
            body["messageType"] = message_type
        if metadata:
            body["metadata"] = metadata
        if media_urls:
            body["mediaUrls"] = media_urls

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
        metadata: Optional[Dict[str, Any]] = None,
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
            metadata: Custom JSON metadata to attach to the message (max 4KB)

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
        if metadata:
            body["metadata"] = metadata

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
        metadata: Optional[Dict[str, Any]] = None,
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
        if metadata:
            body["metadata"] = metadata

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

    async def preview_batch(
        self,
        messages: List[Dict[str, str]],
        from_: Optional[str] = None,
        message_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Preview a batch without sending (dry run) (async)"""
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

        return await self._http.request(
            method="POST",
            path="/messages/batch/preview",
            body=body,
        )

    # =========================================================================
    # Group MMS
    # =========================================================================

    async def send_group(
        self,
        to: List[str],
        text: Optional[str] = None,
        from_: Optional[str] = None,
        media_urls: Optional[List[str]] = None,
        message_type: Optional[str] = None,
        **kwargs: Any,
    ) -> GroupMessageResponse:
        """
        Send a group MMS to 2-8 US/Canada recipients (async)

        Everyone in ``to`` shares one thread and replies fan out to all
        participants. Requires the ``group_mms`` feature (and ``enable_mms``
        when sending media). US/Canada destinations only.

        Args:
            to: 2-8 recipient phone numbers in E.164 format (US/CA only)
            text: Message content (required unless media_urls is provided)
            from_: Optional sender ID or phone number
            media_urls: Optional media URLs for the group MMS
            message_type: 'marketing' or 'transactional' (default)

        Returns:
            The created group message, including a group_message_id
        """
        if not isinstance(to, list) or len(to) < 2:
            raise SendlyError(
                message="Group messaging needs at least 2 recipients in 'to'",
                code="invalid_request",
                status_code=400,
            )
        if len(to) > 8:
            raise SendlyError(
                message="Group messaging supports at most 8 recipients",
                code="invalid_request",
                status_code=400,
            )
        for recipient in to:
            validate_phone_number(recipient)
        if not text and not media_urls:
            raise SendlyError(
                message="Provide 'text' or 'media_urls'",
                code="invalid_request",
                status_code=400,
            )
        if from_:
            validate_sender_id(from_)

        body: Dict[str, Any] = {"to": to}
        if text:
            body["text"] = text
        if from_:
            body["from"] = from_
        if media_urls:
            body["mediaUrls"] = media_urls
        if message_type:
            body["messageType"] = message_type

        data = await self._http.request(
            method="POST",
            path="/messages/group",
            body=body,
        )

        try:
            return GroupMessageResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e

    # =========================================================================
    # AI Enhance
    # =========================================================================

    async def enhance(
        self,
        text: Optional[str] = None,
        message_type: Optional[str] = None,
        **kwargs: Any,
    ) -> EnhanceMessageResponse:
        """
        Enhance message copy with AI (async)

        Requires the ``ai_classification`` feature. When AI is unavailable the
        original text is returned with an empty explanation.

        Args:
            text: Message text to enhance
            message_type: 'marketing' or 'transactional' to steer the tone

        Returns:
            The enhanced text with a short explanation
        """
        if not text and not message_type:
            raise SendlyError(
                message="Provide 'text' or 'message_type'",
                code="invalid_request",
                status_code=400,
            )

        body: Dict[str, Any] = {}
        if text is not None:
            body["text"] = text
        if message_type:
            body["messageType"] = message_type

        data = await self._http.request(
            method="POST",
            path="/ai/enhance",
            body=body,
        )

        try:
            return EnhanceMessageResponse(**data)
        except PydanticValidationError as e:
            raise SendlyError(
                message=f"Invalid API response format: {e}",
                code="invalid_response",
                status_code=200,
            ) from e


def _rcs_send_body(
    to: str,
    text: Optional[str],
    agent_id: Optional[str],
    card: Optional[Dict[str, Any]],
    suggestions: Optional[List[Dict[str, Any]]],
    fallback_to_sms: Optional[bool],
    metadata: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    has_text = bool(text)
    has_card = bool(card)
    if has_text == has_card:
        raise SendlyError(
            message="Provide exactly one of 'text' or 'card'",
            code="invalid_request",
            status_code=400,
        )

    body: Dict[str, Any] = {"channel": "rcs", "to": to}
    if agent_id:
        body["agentId"] = agent_id
    if has_text:
        body["text"] = text
    if has_card:
        body["card"] = card
    if suggestions:
        body["suggestions"] = suggestions
    if fallback_to_sms is not None:
        body["fallbackToSms"] = fallback_to_sms
    if metadata:
        body["metadata"] = metadata
    return body
