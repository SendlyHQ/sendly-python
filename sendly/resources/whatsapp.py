"""
WhatsApp Resource - Connect senders, manage templates, check windows

WhatsApp is a first-class Sendly channel: connect a number you own, create
Meta-reviewed message templates, and send via
``client.messages.send(channel='whatsapp', ...)``.

Connecting a number is a one-time $19 setup (no monthly fee) and always ends
with a human step: ``signup.create()`` returns a ``connect_url`` that a person
must open in a browser and log in with Facebook to link their WhatsApp
Business Account. Hand the URL to your user - the connection cannot be
completed programmatically.

Two ways to reach a recipient:

- **Inside a 24-hour window** (the recipient messaged you in the last 24h):
  free-form text and media are allowed. Check with ``window()``.
- **Anytime**: an approved template. Templates are reviewed by Meta
  (typically 24-48h) and categorized as authentication, utility, or
  marketing - pricing follows the category and destination country. Note:
  Meta has paused marketing template delivery to US (+1) numbers.
"""

from typing import Any, Dict, List, Optional
from urllib.parse import quote

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError, ValidationError
from ..types import (
    WhatsAppSenderListResponse,
    WhatsAppSenderProfile,
    WhatsAppSignup,
    WhatsAppSignupSession,
    WhatsAppTemplate,
    WhatsAppTemplateDeletedResponse,
    WhatsAppTemplateListResponse,
    WhatsAppWindow,
)
from ..utils.http import AsyncHttpClient, HttpClient
from ..utils.validation import validate_phone_number


class WhatsAppSignupResource:
    """Signup sub-resource for connecting numbers to WhatsApp (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def create(self, phone_number: str) -> WhatsAppSignupSession:
        """Start connecting a number to WhatsApp.

        Charges a one-time $19 setup fee (no monthly fee) and returns a
        ``connect_url``. Completing the connection requires a human: hand the
        URL to your user - they open it in a browser and log in with Facebook
        to link their WhatsApp Business Account. Then poll :meth:`get` until
        the status is ``active``.

        Calling again for a number with an in-flight signup returns the
        existing signup (same ``connect_url``) without charging again.
        Requires a live API key.

        Args:
            phone_number: The number to connect, in E.164 format. Must be an
                active number in your workspace (provisioned, purchased, or
                ported into Sendly).
        """
        validate_phone_number(phone_number)
        data = self._http.request(
            method="POST", path="/whatsapp/signup", body={"phoneNumber": phone_number}
        )
        try:
            return WhatsAppSignupSession(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def get(self, id: str) -> WhatsAppSignup:
        """Get the status of a WhatsApp signup.

        Args:
            id: The signup's id.
        """
        if not id:
            raise ValidationError("A signup 'id' is required")
        data = self._http.request(
            method="GET", path=f"/whatsapp/signup/{quote(id, safe='')}"
        )
        try:
            return WhatsAppSignup(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class WhatsAppSendersResource:
    """Senders sub-resource for WhatsApp-connected numbers and their
    business profiles (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def list(self) -> WhatsAppSenderListResponse:
        """List your WhatsApp senders.

        Returns the numbers connected (or connecting) to WhatsApp on your
        workspace, newest first. An empty list means no number is connected
        yet - start one with :meth:`WhatsAppSignupResource.create`.
        """
        data = self._http.request(method="GET", path="/whatsapp/senders")
        try:
            return WhatsAppSenderListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def get_profile(self, phone_number: str) -> WhatsAppSenderProfile:
        """Get a sender's business profile.

        Returns what recipients see when they open your business in
        WhatsApp. The number must have an active WhatsApp connection.

        Args:
            phone_number: Your WhatsApp-connected sending number, in E.164
                format.

        Example:
            >>> profile = client.whatsapp.senders.get_profile('+15559876543')
            >>> print(profile.display_name, profile.about)
        """
        validate_phone_number(phone_number)
        data = self._http.request(
            method="GET",
            path=f"/whatsapp/senders/{quote(phone_number, safe='')}/profile",
        )
        try:
            return WhatsAppSenderProfile(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def update_profile(
        self,
        phone_number: str,
        *,
        display_name: Optional[str] = None,
        about: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        email: Optional[str] = None,
        website: Optional[str] = None,
        address: Optional[str] = None,
    ) -> WhatsAppSenderProfile:
        """Update a sender's business profile.

        Supply only the fields to change - omitted fields keep their current
        value. Requires a live API key.

        Args:
            phone_number: Your WhatsApp-connected sending number, in E.164
                format.
            display_name: The business name recipients see.
            about: Short profile line (max 139 characters).
            description: Longer business description (max 512 characters).
            category: Business category (e.g. ``'Restaurant'``).
            email: Contact email shown on the profile.
            website: Website shown on the profile.
            address: Business address shown on the profile.

        Example:
            >>> client.whatsapp.senders.update_profile(
            ...     '+15559876543',
            ...     about='Fresh roasts daily',
            ...     website='https://acme.example.com',
            ... )
        """
        validate_phone_number(phone_number)
        payload = _profile_body(
            display_name, about, description, category, email, website, address
        )
        data = self._http.request(
            method="PATCH",
            path=f"/whatsapp/senders/{quote(phone_number, safe='')}/profile",
            body=payload,
        )
        try:
            return WhatsAppSenderProfile(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class WhatsAppTemplatesResource:
    """Templates sub-resource for Meta-reviewed message templates (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def list(self) -> WhatsAppTemplateListResponse:
        """List your WhatsApp templates with review status and quality rating."""
        data = self._http.request(method="GET", path="/whatsapp/templates")
        try:
            return WhatsAppTemplateListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def create(
        self,
        sender: str,
        name: str,
        language: str,
        category: str,
        body: str,
        *,
        footer: Optional[str] = None,
        header: Optional[str] = None,
        buttons: Optional[List[Dict[str, Any]]] = None,
        examples: Optional[Dict[str, str]] = None,
    ) -> WhatsAppTemplate:
        """Create a template and submit it to Meta for review.

        Review usually takes 24-48h; the template is usable once its status
        is ``APPROVED``. Requires a live API key.

        Args:
            sender: The WhatsApp-connected sending number this template
                belongs to, in E.164 format.
            name: Template name: lowercase letters, digits, and underscores
                (e.g. ``order_shipped``).
            language: Template language code (e.g. ``en_US``).
            category: Template category (``AUTHENTICATION``, ``UTILITY``, or
                ``MARKETING``) - drives Meta review rules and pricing.
            body: Body text. Use ``{{1}}``, ``{{2}}``, ... for variables;
                every placeholder needs an example value in ``examples``.
            footer: Optional footer line.
            header: Optional text header.
            buttons: Optional buttons, e.g.
                ``[{'type': 'quick_reply', 'text': 'Stop promotions'}]``.
                A ``url`` button takes ``url`` (may contain a ``{{1}}``
                placeholder, with ``example`` values for review); an ``otp``
                button is required on AUTHENTICATION templates.
            examples: Example values for body placeholders, keyed by
                placeholder number: ``{'1': 'Acme Inc', '2': '#4821'}``.
                Required when the body has variables.
        """
        validate_phone_number(sender)
        payload = _create_template_body(
            sender, name, language, category, body, footer, header, buttons, examples
        )
        data = self._http.request(method="POST", path="/whatsapp/templates", body=payload)
        try:
            return WhatsAppTemplate(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def update(
        self,
        id: str,
        *,
        body: Optional[str] = None,
        footer: Optional[str] = None,
        header: Optional[str] = None,
        buttons: Optional[List[Dict[str, Any]]] = None,
        examples: Optional[Dict[str, str]] = None,
    ) -> WhatsAppTemplate:
        """Edit an APPROVED or REJECTED template and resubmit it for review.

        This is the recovery path for rejections: template names are locked
        for ~30 days after deletion, so editing a rejected template (rather
        than deleting and re-creating it) is the way to fix it. The updated
        template goes back to ``PENDING`` review. Requires a live API key.

        Args:
            id: The template's id.
            body: Replacement body text.
            footer: Replacement footer.
            header: Replacement text header.
            buttons: Replacement buttons.
            examples: Replacement example values for body placeholders.
        """
        if not id:
            raise ValidationError("A template 'id' is required")
        payload = _update_template_body(body, footer, header, buttons, examples)
        data = self._http.request(
            method="PATCH",
            path=f"/whatsapp/templates/{quote(id, safe='')}",
            body=payload,
        )
        try:
            return WhatsAppTemplate(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def delete(self, id: str) -> WhatsAppTemplateDeletedResponse:
        """Delete a template.

        Meta locks a deleted template's name for ~30 days - re-creating it
        fails with ``template_name_locked`` until the lock lifts. To fix a
        rejected template, prefer :meth:`update`. Requires a live API key.

        Args:
            id: The template's id.
        """
        if not id:
            raise ValidationError("A template 'id' is required")
        data = self._http.request(
            method="DELETE", path=f"/whatsapp/templates/{quote(id, safe='')}"
        )
        try:
            return WhatsAppTemplateDeletedResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class WhatsAppResource:
    """WhatsApp API resource (sync)

    Example:
        >>> # 1. Connect a number ($19 one-time, no monthly fee). The connect
        >>> #    URL must be opened by a human - they log in with Facebook in
        >>> #    a browser to link their WhatsApp Business Account.
        >>> signup = client.whatsapp.signup.create('+15559876543')
        >>> print(f'Have your user open: {signup.connect_url}')
        >>> # ...poll client.whatsapp.signup.get(signup.id) until status == 'active'
        >>> client.whatsapp.templates.create(
        ...     sender='+15559876543',
        ...     name='order_shipped',
        ...     language='en_US',
        ...     category='UTILITY',
        ...     body='Hi {{1}}, your order {{2}} has shipped!',
        ...     examples={'1': 'Sam', '2': '#4821'},
        ... )
        >>> # Send - free-form inside an open 24h window, template anytime
        >>> window = client.whatsapp.window(from_='+15559876543', to='+15551234567')
        >>> if not window.open:
        ...     pass  # use a template send instead of free-form text
    """

    def __init__(self, http: HttpClient):
        self._http = http
        self.signup = WhatsAppSignupResource(http)
        self.senders = WhatsAppSendersResource(http)
        self.templates = WhatsAppTemplatesResource(http)

    def window(self, from_: str, to: str) -> WhatsAppWindow:
        """Check whether a 24-hour customer-service window is open between
        one of your WhatsApp senders and a recipient.

        Free-form text and media only deliver while a window is open (it
        opens when the recipient messages you and lasts 24h from their last
        inbound message). Outside a window, send an approved template.

        Args:
            from_: Your WhatsApp-connected sending number, in E.164 format.
            to: The recipient's number, in E.164 format.
        """
        validate_phone_number(from_)
        validate_phone_number(to)
        data = self._http.request(
            method="GET", path="/whatsapp/window", params={"from": from_, "to": to}
        )
        try:
            return WhatsAppWindow(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class AsyncWhatsAppSignupResource:
    """Signup sub-resource for connecting numbers to WhatsApp (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def create(self, phone_number: str) -> WhatsAppSignupSession:
        """Start connecting a number to WhatsApp. See :meth:`WhatsAppSignupResource.create`."""
        validate_phone_number(phone_number)
        data = await self._http.request(
            method="POST", path="/whatsapp/signup", body={"phoneNumber": phone_number}
        )
        try:
            return WhatsAppSignupSession(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def get(self, id: str) -> WhatsAppSignup:
        """Get the status of a WhatsApp signup."""
        if not id:
            raise ValidationError("A signup 'id' is required")
        data = await self._http.request(
            method="GET", path=f"/whatsapp/signup/{quote(id, safe='')}"
        )
        try:
            return WhatsAppSignup(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class AsyncWhatsAppSendersResource:
    """Senders sub-resource for WhatsApp-connected numbers and their
    business profiles (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list(self) -> WhatsAppSenderListResponse:
        """List your WhatsApp senders."""
        data = await self._http.request(method="GET", path="/whatsapp/senders")
        try:
            return WhatsAppSenderListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def get_profile(self, phone_number: str) -> WhatsAppSenderProfile:
        """Get a sender's business profile.
        See :meth:`WhatsAppSendersResource.get_profile`."""
        validate_phone_number(phone_number)
        data = await self._http.request(
            method="GET",
            path=f"/whatsapp/senders/{quote(phone_number, safe='')}/profile",
        )
        try:
            return WhatsAppSenderProfile(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def update_profile(
        self,
        phone_number: str,
        *,
        display_name: Optional[str] = None,
        about: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        email: Optional[str] = None,
        website: Optional[str] = None,
        address: Optional[str] = None,
    ) -> WhatsAppSenderProfile:
        """Update a sender's business profile.
        See :meth:`WhatsAppSendersResource.update_profile`."""
        validate_phone_number(phone_number)
        payload = _profile_body(
            display_name, about, description, category, email, website, address
        )
        data = await self._http.request(
            method="PATCH",
            path=f"/whatsapp/senders/{quote(phone_number, safe='')}/profile",
            body=payload,
        )
        try:
            return WhatsAppSenderProfile(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class AsyncWhatsAppTemplatesResource:
    """Templates sub-resource for Meta-reviewed message templates (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list(self) -> WhatsAppTemplateListResponse:
        """List your WhatsApp templates with review status and quality rating."""
        data = await self._http.request(method="GET", path="/whatsapp/templates")
        try:
            return WhatsAppTemplateListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def create(
        self,
        sender: str,
        name: str,
        language: str,
        category: str,
        body: str,
        *,
        footer: Optional[str] = None,
        header: Optional[str] = None,
        buttons: Optional[List[Dict[str, Any]]] = None,
        examples: Optional[Dict[str, str]] = None,
    ) -> WhatsAppTemplate:
        """Create a template and submit it to Meta for review.
        See :meth:`WhatsAppTemplatesResource.create`."""
        validate_phone_number(sender)
        payload = _create_template_body(
            sender, name, language, category, body, footer, header, buttons, examples
        )
        data = await self._http.request(
            method="POST", path="/whatsapp/templates", body=payload
        )
        try:
            return WhatsAppTemplate(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def update(
        self,
        id: str,
        *,
        body: Optional[str] = None,
        footer: Optional[str] = None,
        header: Optional[str] = None,
        buttons: Optional[List[Dict[str, Any]]] = None,
        examples: Optional[Dict[str, str]] = None,
    ) -> WhatsAppTemplate:
        """Edit an APPROVED or REJECTED template and resubmit it for review.
        See :meth:`WhatsAppTemplatesResource.update`."""
        if not id:
            raise ValidationError("A template 'id' is required")
        payload = _update_template_body(body, footer, header, buttons, examples)
        data = await self._http.request(
            method="PATCH",
            path=f"/whatsapp/templates/{quote(id, safe='')}",
            body=payload,
        )
        try:
            return WhatsAppTemplate(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def delete(self, id: str) -> WhatsAppTemplateDeletedResponse:
        """Delete a template. See :meth:`WhatsAppTemplatesResource.delete`."""
        if not id:
            raise ValidationError("A template 'id' is required")
        data = await self._http.request(
            method="DELETE", path=f"/whatsapp/templates/{quote(id, safe='')}"
        )
        try:
            return WhatsAppTemplateDeletedResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class AsyncWhatsAppResource:
    """WhatsApp API resource (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http
        self.signup = AsyncWhatsAppSignupResource(http)
        self.senders = AsyncWhatsAppSendersResource(http)
        self.templates = AsyncWhatsAppTemplatesResource(http)

    async def window(self, from_: str, to: str) -> WhatsAppWindow:
        """Check whether a 24-hour customer-service window is open.
        See :meth:`WhatsAppResource.window`."""
        validate_phone_number(from_)
        validate_phone_number(to)
        data = await self._http.request(
            method="GET", path="/whatsapp/window", params={"from": from_, "to": to}
        )
        try:
            return WhatsAppWindow(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


def _create_template_body(
    sender: str,
    name: str,
    language: str,
    category: str,
    body: str,
    footer: Optional[str],
    header: Optional[str],
    buttons: Optional[List[Dict[str, Any]]],
    examples: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "sender": sender,
        "name": name,
        "language": language,
        "category": category,
        "body": body,
    }
    optional: Dict[str, Any] = {
        "footer": footer,
        "header": header,
        "buttons": buttons,
        "examples": examples,
    }
    for key, value in optional.items():
        if value is not None:
            payload[key] = value
    return payload


def _profile_body(
    display_name: Optional[str],
    about: Optional[str],
    description: Optional[str],
    category: Optional[str],
    email: Optional[str],
    website: Optional[str],
    address: Optional[str],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    optional: Dict[str, Any] = {
        "displayName": display_name,
        "about": about,
        "description": description,
        "category": category,
        "email": email,
        "website": website,
        "address": address,
    }
    for key, value in optional.items():
        if value is not None:
            payload[key] = value
    if not payload:
        raise ValidationError("Provide at least one profile field to update")
    return payload


def _update_template_body(
    body: Optional[str],
    footer: Optional[str],
    header: Optional[str],
    buttons: Optional[List[Dict[str, Any]]],
    examples: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    optional: Dict[str, Any] = {
        "body": body,
        "footer": footer,
        "header": header,
        "buttons": buttons,
        "examples": examples,
    }
    for key, value in optional.items():
        if value is not None:
            payload[key] = value
    return payload


def _invalid_response(e: PydanticValidationError) -> SendlyError:
    """Wrap a pydantic schema error as a SendlyError, matching the SDK's idiom."""
    return SendlyError(
        message=f"Invalid API response format: {e}",
        code="invalid_response",
        status_code=200,
    )
