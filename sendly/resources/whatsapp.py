"""
WhatsApp Resource - Connect senders, manage templates, check windows

WhatsApp is a first-class Sendly channel: connect a number you own, create
Meta-reviewed message templates, and send via
``client.messages.send(channel='whatsapp', ...)``.

Connecting a number is a one-time $19 setup (no monthly fee) and always ends
with a human step: ``signup.create()`` returns a ``connect_url`` that a person
must open in a browser and log in with Facebook to link their WhatsApp
Business Account. Hand the URL to your user - that connection cannot be
completed programmatically. Once an account is connected, more numbers can
join it by code, without the Facebook step: pass ``business_account_id`` to
``signup.create()``, then submit the code with ``signup.verify()``.

Two ways to reach a recipient:

- **Inside a 24-hour window** (the recipient messaged you in the last 24h):
  free-form text and media are allowed. Check with ``window()``.
- **Anytime**: an approved template. Templates are reviewed by Meta
  (typically 24-48h) and categorized as authentication, utility, or
  marketing - pricing follows the category and destination country. Note:
  Meta has paused marketing template delivery to US (+1) numbers.

Pricing: free-form text or media inside the 24-hour window costs 1 credit
each for the first 1,000 per sending number per calendar month (UTC), then
the destination's utility template price; countries without a listed price
use the default utility price of 12 credits. Templates are priced by category
and destination country; countries without a listed price use 33
(marketing), 12 (utility) and 12 (authentication) credits. A failed send
gives its slot back.

Scopes and keys: sends go through ``messages.send(channel='whatsapp')`` and
need ``sms:send``, not ``whatsapp:write``, and a live key. Reads (signup
status, templates, the window, senders, sender profiles and conversational
components) need ``whatsapp:read`` and accept test keys. Signup (with verify
and resend), template create/edit/delete and sender edits (profile, photo,
conversational components, calling) need ``whatsapp:write`` and a live key
(otherwise 403 ``whatsapp_requires_live_key``). In a team workspace,
connecting and sender edits need an owner or admin (``settings:write``), and template writes need an
owner, admin or member (``templates:write``); a missing role returns 403
``insufficient_permissions``.

WhatsApp is enabled per person: the user who owns the API key, not the
workspace. While it is off, sends return 403 ``whatsapp_not_enabled`` and
every method on this resource gets 404 ``not_found``.
"""

from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union, overload
from urllib.parse import quote

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError, ValidationError
from ..types import (
    WhatsAppCallingSettings,
    WhatsAppCommand,
    WhatsAppConversationalComponents,
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
from .business_upgrade import _multipart_request_async, _multipart_request_sync


class WhatsAppSignupResource:
    """Signup sub-resource for connecting numbers to WhatsApp (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    @overload
    def create(self, phone_number: str) -> WhatsAppSignupSession: ...

    @overload
    def create(
        self,
        phone_number: str,
        *,
        business_account_id: str,
        verification_method: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> WhatsAppSignup: ...

    def create(
        self,
        phone_number: str,
        *,
        business_account_id: Optional[str] = None,
        verification_method: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> Union[WhatsAppSignupSession, WhatsAppSignup]:
        """Start connecting a number to WhatsApp.

        Charges a one-time $19 setup fee (no monthly fee) and returns a
        ``connect_url``. Completing the connection requires a human: hand the
        URL to your user - they open it in a browser and log in with Facebook
        to link their WhatsApp Business Account. Then poll :meth:`get` until
        the status is ``active``.

        Calling again for a number with an in-flight signup returns the
        existing signup (same ``connect_url``) without charging again.
        Requires a live API key with the ``whatsapp:write`` scope and, in a
        team workspace, an owner or admin (``settings:write``). After the
        Facebook step the signup stays ``registering`` while WhatsApp
        activates the number. Activation usually takes a few minutes but can
        take hours. If it hasn't finished about 6 hours after the session
        began, the session fails with ``registration_timeout`` and the fee is
        refunded. If the connection fails, the $19 fee is refunded
        automatically; once the number has connected there is no refund, and
        a later disconnect gets nothing back.

        Pass ``business_account_id`` to add the number to a WhatsApp
        Business Account this workspace has already connected, without the
        Facebook step. The same $19 fee applies (refunded automatically if the
        connection fails), then WhatsApp sends the number a 6-digit code by
        text or voice call. This returns a :class:`WhatsAppSignup` with status
        ``verifying`` and no ``connect_url``: submit the code with
        :meth:`verify`, or read it from :meth:`get` as ``verification_code``
        once the text reaches the number. Calling again for a number that is
        already verifying returns that signup without a second charge or a
        second code, with two exceptions: if the first call stopped before
        the code was requested, the repeat requests it (201); and a verifying
        signup more than 3 hours old is failed and refunded, and a new charged
        one is started. With ``business_account_id`` a 5xx, a timeout or a
        network error is raised at once, never retried: each attempt can
        start a new signup that is charged and, when it fails, refunded. Only
        a 429 the API never ran is retried.

        Args:
            phone_number: The number to connect, in E.164 format. Must be an
                active number in your workspace (provisioned, purchased, or
                fully ported into Sendly).
            business_account_id: The connected account's id, as
                ``business_account_id`` on a sender from
                :meth:`WhatsAppSendersResource.list`. The account needs at
                least one active number in this workspace.
            verification_method: ``'sms'`` (the default) or ``'voice'``; only
                with ``business_account_id``.
            display_name: The name WhatsApp shows for the number (max 512
                characters); only with ``business_account_id``. Defaults to
                the account's existing sender display name, else its
                business name.

        Example:
            >>> senders = client.whatsapp.senders.list().senders
            >>> account_id = next(
            ...     s.business_account_id
            ...     for s in senders
            ...     if s.status == 'active' and s.business_account_id
            ... )
            >>> signup = client.whatsapp.signup.create(
            ...     '+14155550123', business_account_id=account_id
            ... )
            >>> client.whatsapp.signup.verify(signup.id, '123456')

        Raises:
            ValidationError: Locally, without sending anything, for an empty
                ``business_account_id``, or ``verification_method`` or
                ``display_name`` without one.
            AuthenticationError: ``insufficient_permissions`` when the key
                lacks ``whatsapp:write`` or the role isn't owner or admin.
            SendlyError: ``whatsapp_requires_live_key`` (403) with a test key.
            SendlyError: ``whatsapp_unavailable`` (503) while WhatsApp
                connections are unavailable. Nothing is charged. Only signup
                returns it, with ``retryAfter: 3600`` in the body and a
                ``Retry-After: 3600`` header. The SDK retries it like any 5xx
                before raising.
            SendlyError: ``whatsapp_signup_limit_reached`` (429) after 5
                failed, charged signups in 24 hours. Not retried; try again
                the next day.
            SendlyError: ``whatsapp_verification_in_progress`` (409) without
                ``business_account_id`` for a number being added by code;
                ``e.response.model_extra['id']`` is that signup.
            SendlyError: ``whatsapp_business_account_not_found`` (404) when
                the account isn't connected here with an active number.
            SendlyError: ``display_name_required`` (400) when no display name
                was given and the account has none to reuse;
                ``whatsapp_signup_in_progress`` (409) while a Facebook
                connection for the number is in flight
                (``e.response.model_extra['id']`` is that signup);
                ``whatsapp_already_enabled`` (409) when it is connected.
            SendlyError: ``whatsapp_verification_start_failed``: 422 when
                WhatsApp refused to send a code (final), 502 when it couldn't
                be reached. Either way the signup failed and the fee is
                refunded; start again. Not retried automatically.
        """
        validate_phone_number(phone_number)
        body = _signup_body(phone_number, business_account_id, verification_method, display_name)
        data = self._http.request(
            method="POST",
            path="/whatsapp/signup",
            body=body,
            retry_unsent_only=business_account_id is not None,
        )
        try:
            if business_account_id is None:
                return WhatsAppSignupSession(**data)
            return WhatsAppSignup(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def verify(self, id: str, code: str) -> WhatsAppSignup:
        """Submit the 6-digit code WhatsApp sent to a number being added by
        code. Spaces and dashes are ignored, so ``'123-456'`` works.

        A correct code connects the number: the signup comes back ``active``
        and ``whatsapp_account.connected`` fires. A signup that is already
        active comes back as it is. Requires a live API key with the
        ``whatsapp:write`` scope and, in a team workspace, an owner or admin
        (``settings:write``).

        A 5xx, a timeout or a network error is raised at once, never retried:
        every submission uses one of the 5 attempts, and a 502
        ``whatsapp_activation_pending`` means WhatsApp already accepted the
        code. Only a 429 the API never ran is retried.

        Args:
            id: The signup's id.
            code: The code WhatsApp sent.

        Raises:
            SendlyError: ``invalid_verification_code`` (400) when the code
                isn't 6 digits.
            SendlyError: ``whatsapp_verification_code_invalid`` (422) for a
                wrong code; ``e.response.attempts_remaining`` says how many
                tries are left.
            SendlyError: ``whatsapp_verification_failed`` (409) after 5 wrong
                codes: the signup failed and the fee is refunded.
            SendlyError: ``whatsapp_verification_busy`` (409) while another
                code for the number is being checked; try again in a moment.
            SendlyError: ``signup_not_active`` (409) when the signup isn't
                waiting for a code, or is more than 3 hours old.
            SendlyError: ``whatsapp_verification_unavailable`` (502) when
                WhatsApp couldn't check the code (the attempt isn't counted),
                or ``whatsapp_activation_pending`` (502) when the code was
                accepted but the connection didn't finish; Sendly is alerted,
                so check back with :meth:`get`. Neither is retried
                automatically.
            SendlyError: ``signup_not_found`` (404) when no such signup exists
                in your workspace.
        """
        if not id:
            raise ValidationError("A signup 'id' is required")
        data = self._http.request(
            method="POST",
            path=f"/whatsapp/signup/{quote(id, safe='')}/verify",
            body={"code": code},
            retry_unsent_only=True,
        )
        try:
            return WhatsAppSignup(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def resend(self, id: str, verification_method: Optional[str] = None) -> WhatsAppSignup:
        """Ask WhatsApp to send a number being added by code a new code.

        Leaving out ``verification_method`` sends it by text (``'sms'``),
        whichever method the signup used before. Codes are at least 30
        seconds apart, counted from the signup's last change, a code
        submission included. A signup that is already active comes back as it
        is. Requires a live API key with the ``whatsapp:write`` scope and, in
        a team workspace, an owner or admin (``settings:write``).

        Args:
            id: The signup's id.
            verification_method: ``'sms'`` (the default) or ``'voice'``.

        Raises:
            SendlyError: ``whatsapp_verification_resend_too_soon`` (429)
                within 30 seconds of the last change;
                ``e.response.retry_after`` is the wait in seconds. Not
                retried.
            SendlyError: ``whatsapp_verification_resend_failed``: 422 when
                WhatsApp wouldn't send another code yet, 502 when it couldn't
                be reached.
            SendlyError: ``signup_not_active`` (409) when the signup isn't
                waiting for a code, or is more than 3 hours old.
            SendlyError: ``signup_not_found`` (404) when no such signup exists
                in your workspace.
        """
        if not id:
            raise ValidationError("A signup 'id' is required")
        data = self._http.request(
            method="POST",
            path=f"/whatsapp/signup/{quote(id, safe='')}/resend",
            body=_resend_body(verification_method),
        )
        try:
            return WhatsAppSignup(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def get(self, id: str) -> WhatsAppSignup:
        """Get the status of a WhatsApp signup.

        Needs the ``whatsapp:read`` scope; test keys work.

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
        yet - start one with :meth:`WhatsAppSignupResource.create`. Needs the
        ``whatsapp:read`` scope; test keys work.
        """
        data = self._http.request(method="GET", path="/whatsapp/senders")
        try:
            return WhatsAppSenderListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def get_profile(self, phone_number: str) -> WhatsAppSenderProfile:
        """Get a sender's business profile.

        Returns what recipients see when they open your business in
        WhatsApp. The number must have an active WhatsApp connection. Needs
        the ``whatsapp:read`` scope; test keys work.

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
        value. Requires a live API key with the ``whatsapp:write`` scope and,
        in a team workspace, an owner or admin (``settings:write``).

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

    def upload_profile_photo(
        self,
        phone_number: str,
        file: Union[BinaryIO, bytes],
        content_type: str = "image/jpeg",
    ) -> WhatsAppSenderProfile:
        """Upload a sender's profile photo.

        Send a JPEG or PNG of at most 5 MB; the API checks the file's bytes,
        not its name or content type. WhatsApp wants a square image at least
        192 pixels wide (640 recommended). Requires a live API key with the
        ``whatsapp:write`` scope and, in a team workspace, an owner or admin
        (``settings:write``).

        Args:
            phone_number: Your WhatsApp-connected sending number, in E.164
                format.
            file: The image, as a file opened in binary mode or bytes.
            content_type: ``'image/jpeg'`` (the default) or ``'image/png'``.

        Returns:
            The updated business profile.

        Raises:
            SendlyError: ``file_required`` (400) for an empty file,
                ``whatsapp_profile_photo_invalid`` (400) when it isn't a JPEG
                or PNG, or ``whatsapp_profile_photo_too_large`` (413) over
                5 MB.
            SendlyError: ``whatsapp_sender_not_connected`` (404) when the
                number isn't connected to WhatsApp.
            SendlyError: ``whatsapp_profile_update_failed`` (502) when
                WhatsApp refused the photo or couldn't be reached; check the
                image is square and at least 192 pixels wide. A 5xx, a
                timeout or a network error is raised at once, not retried
                automatically.

        Example:
            >>> with open('logo.png', 'rb') as f:
            ...     profile = client.whatsapp.senders.upload_profile_photo(
            ...         '+14155550123', f, content_type='image/png'
            ...     )
            >>> print(profile.profile_photo_url)
        """
        validate_phone_number(phone_number)
        data = _multipart_request_sync(
            self._http,
            f"/whatsapp/senders/{quote(phone_number, safe='')}/profile/photo",
            {},
            _photo_part(file, content_type),
        )
        try:
            return WhatsAppSenderProfile(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def delete_profile_photo(self, phone_number: str) -> WhatsAppSenderProfile:
        """Remove a sender's profile photo.

        Requires a live API key with the ``whatsapp:write`` scope and, in a
        team workspace, an owner or admin (``settings:write``).

        Args:
            phone_number: Your WhatsApp-connected sending number, in E.164
                format.

        Raises:
            SendlyError: ``whatsapp_sender_not_connected`` (404) when the
                number isn't connected to WhatsApp.
            SendlyError: ``whatsapp_profile_update_failed`` (502) when
                WhatsApp couldn't remove it.
        """
        validate_phone_number(phone_number)
        data = self._http.request(
            method="DELETE",
            path=f"/whatsapp/senders/{quote(phone_number, safe='')}/profile/photo",
        )
        try:
            return WhatsAppSenderProfile(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def get_conversational_components(
        self, phone_number: str
    ) -> WhatsAppConversationalComponents:
        """Get a sender's ice breakers and commands.

        Ice breakers are the suggestions shown when someone opens a chat with
        the business for the first time; commands are shown when they type
        "/". Needs the ``whatsapp:read`` scope; test keys work.

        Args:
            phone_number: Your WhatsApp-connected sending number, in E.164
                format.

        Raises:
            SendlyError: ``whatsapp_sender_not_connected`` (404) when the
                number isn't connected to WhatsApp.
            SendlyError: ``whatsapp_conversational_components_fetch_failed``
                (502) when WhatsApp couldn't be reached.
        """
        validate_phone_number(phone_number)
        data = self._http.request(
            method="GET",
            path=f"/whatsapp/senders/{quote(phone_number, safe='')}/conversational_components",
        )
        try:
            return WhatsAppConversationalComponents(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def update_conversational_components(
        self,
        phone_number: str,
        *,
        ice_breakers: Optional[List[str]] = None,
        commands: Optional[List[Union[WhatsAppCommand, Dict[str, str]]]] = None,
    ) -> WhatsAppConversationalComponents:
        """Replace a sender's ice breakers, commands, or both.

        Each list you pass replaces the stored one, and ``[]`` clears it; a
        list you leave out is kept. Requires a live API key with the
        ``whatsapp:write`` scope and, in a team workspace, an owner or admin
        (``settings:write``).

        Args:
            phone_number: Your WhatsApp-connected sending number, in E.164
                format.
            ice_breakers: At most 4, each 1 to 80 characters after trimming,
                no two the same ignoring case.
            commands: At most 30, as ``[{'command': 'menu', 'description':
                "See today's menu"}]`` or :class:`WhatsAppCommand` objects.
                ``command`` is letters, digits or underscores, 1 to 32
                characters (a leading "/" is stripped); ``description`` is 1
                to 256 characters; no command twice.

        Raises:
            ValidationError: Locally when neither list is given, or
                ``invalid_request`` (400) from the API with the reason.
            SendlyError: ``whatsapp_sender_not_connected`` (404) when the
                number isn't connected to WhatsApp.
            SendlyError: ``whatsapp_conversational_components_update_failed``
                (502) when WhatsApp couldn't save them.

        Example:
            >>> client.whatsapp.senders.update_conversational_components(
            ...     '+14155550123',
            ...     ice_breakers=['What are your hours?', 'Book a table'],
            ...     commands=[{'command': 'menu', 'description': "See today's menu"}],
            ... )
        """
        validate_phone_number(phone_number)
        data = self._http.request(
            method="PATCH",
            path=f"/whatsapp/senders/{quote(phone_number, safe='')}/conversational_components",
            body=_components_body(ice_breakers, commands),
        )
        try:
            return WhatsAppConversationalComponents(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def set_calling(self, phone_number: str, *, enabled: bool) -> WhatsAppCallingSettings:
        """Switch WhatsApp calling on or off for a sender.

        With calling on, a WhatsApp user calling the number rings exactly
        like a phone call (the dashboard or the AI agent, per the number's
        voice settings) and is billed at the normal inbound rate. Turning it
        on needs calls switched on for the number first. There is no API for
        placing WhatsApp calls. Requires a live API key with the
        ``whatsapp:write`` scope and, in a team workspace, an owner or admin
        (``settings:write``).

        Args:
            phone_number: Your WhatsApp-connected sending number, in E.164
                format.
            enabled: True to switch calling on, False to switch it off.

        Raises:
            SendlyError: ``voice_not_enabled`` (409) when turning calling on
                for a number whose calls are off.
            SendlyError: ``whatsapp_calling_unavailable`` (422) when WhatsApp
                refused: it only allows calling once the account may message
                at least 2,000 people a day and the display name is approved.
            SendlyError: ``whatsapp_sender_not_connected`` (404) when the
                number isn't connected to WhatsApp.
            SendlyError: ``whatsapp_calling_update_failed`` (502) when
                WhatsApp couldn't be reached.

        Example:
            >>> client.whatsapp.senders.set_calling('+14155550123', enabled=True)
        """
        validate_phone_number(phone_number)
        data = self._http.request(
            method="PATCH",
            path=f"/whatsapp/senders/{quote(phone_number, safe='')}/calling",
            body={"enabled": enabled},
        )
        try:
            return WhatsAppCallingSettings(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class WhatsAppTemplatesResource:
    """Templates sub-resource for Meta-reviewed message templates (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def list(self) -> WhatsAppTemplateListResponse:
        """List your WhatsApp templates with review status and quality rating.

        Needs the ``whatsapp:read`` scope; test keys work.
        """
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
        is ``APPROVED``. Requires a live API key with the ``whatsapp:write``
        scope and, in a team workspace, an owner, admin or member
        (``templates:write``). A marketing template without an opt-out button
        is still accepted, with a warning.

        Args:
            sender: The WhatsApp-connected sending number this template
                belongs to, in E.164 format.
            name: Template name: lowercase letters, digits, and underscores
                (e.g. ``order_shipped``).
            language: Template language code (e.g. ``en_US``).
            category: Template category (``AUTHENTICATION``, ``UTILITY``, or
                ``MARKETING``; the server uppercases it). Required, with no
                default; it drives Meta review rules and pricing and can't be
                changed later.
            body: Body text. Use ``{{1}}``, ``{{2}}``, ... for variables;
                every placeholder needs an example value in ``examples``.
            footer: Optional footer line.
            header: Optional text header. Fixed text only: a header
                containing ``{{n}}`` is refused with
                ``template_header_variable_unsupported``.
            buttons: Optional buttons, e.g.
                ``[{'type': 'quick_reply', 'text': 'Stop promotions'}]``.
                A ``url`` button takes ``url`` (may contain a ``{{1}}``
                placeholder, with ``example`` values for review); an ``otp``
                button is required on AUTHENTICATION templates.
            examples: Example values for body placeholders, keyed by
                placeholder number: ``{'1': 'Acme Inc', '2': '#4821'}``.
                Required when the body has variables.

        Raises:
            NotFoundError: ``whatsapp_sender_not_connected`` (404) when the
                sender isn't connected to WhatsApp; this is checked first.
            SendlyError: With a ``template_*`` code (400) and a readable
                message when the template fails pre-flight checks:
                ``template_category_invalid`` (category missing or not one of
                the three), ``template_authentication_otp_button_required``,
                ``template_authentication_no_links`` (a link in the body or a
                URL button on an authentication template),
                ``template_header_variable_unsupported``, a bad name or
                missing examples.
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
        template goes back to ``PENDING`` review. The category can't be
        changed. Requires a live API key with the ``whatsapp:write`` scope
        and, in a team workspace, an owner, admin or member
        (``templates:write``).

        Args:
            id: The template's id.
            body: Replacement body text.
            footer: Replacement footer.
            header: Replacement text header; it can't contain ``{{n}}``
                variables (``template_header_variable_unsupported``).
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
        rejected template, prefer :meth:`update`. Requires a live API key
        with the ``whatsapp:write`` scope and, in a team workspace, an owner,
        admin or member (``templates:write``).

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
        inbound message). Outside a window, send an approved template. Needs
        the ``whatsapp:read`` scope; test keys work.

        The response is exactly ``{open, expiresAt}``: with no window on
        record ``open`` is False and ``expires_at`` is None; after a window
        has expired ``open`` is False and ``expires_at`` is the past expiry.

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

    @overload
    async def create(self, phone_number: str) -> WhatsAppSignupSession: ...

    @overload
    async def create(
        self,
        phone_number: str,
        *,
        business_account_id: str,
        verification_method: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> WhatsAppSignup: ...

    async def create(
        self,
        phone_number: str,
        *,
        business_account_id: Optional[str] = None,
        verification_method: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> Union[WhatsAppSignupSession, WhatsAppSignup]:
        """Start connecting a number to WhatsApp, or add one to a connected
        account by code. See :meth:`WhatsAppSignupResource.create`."""
        validate_phone_number(phone_number)
        body = _signup_body(phone_number, business_account_id, verification_method, display_name)
        data = await self._http.request(
            method="POST",
            path="/whatsapp/signup",
            body=body,
            retry_unsent_only=business_account_id is not None,
        )
        try:
            if business_account_id is None:
                return WhatsAppSignupSession(**data)
            return WhatsAppSignup(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def verify(self, id: str, code: str) -> WhatsAppSignup:
        """Submit the code WhatsApp sent. See :meth:`WhatsAppSignupResource.verify`."""
        if not id:
            raise ValidationError("A signup 'id' is required")
        data = await self._http.request(
            method="POST",
            path=f"/whatsapp/signup/{quote(id, safe='')}/verify",
            body={"code": code},
            retry_unsent_only=True,
        )
        try:
            return WhatsAppSignup(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def resend(
        self, id: str, verification_method: Optional[str] = None
    ) -> WhatsAppSignup:
        """Ask for a new code. See :meth:`WhatsAppSignupResource.resend`."""
        if not id:
            raise ValidationError("A signup 'id' is required")
        data = await self._http.request(
            method="POST",
            path=f"/whatsapp/signup/{quote(id, safe='')}/resend",
            body=_resend_body(verification_method),
        )
        try:
            return WhatsAppSignup(**data)
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

    async def upload_profile_photo(
        self,
        phone_number: str,
        file: Union[BinaryIO, bytes],
        content_type: str = "image/jpeg",
    ) -> WhatsAppSenderProfile:
        """Upload a sender's profile photo.
        See :meth:`WhatsAppSendersResource.upload_profile_photo`."""
        validate_phone_number(phone_number)
        data = await _multipart_request_async(
            self._http,
            f"/whatsapp/senders/{quote(phone_number, safe='')}/profile/photo",
            {},
            _photo_part(file, content_type),
        )
        try:
            return WhatsAppSenderProfile(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def delete_profile_photo(self, phone_number: str) -> WhatsAppSenderProfile:
        """Remove a sender's profile photo.
        See :meth:`WhatsAppSendersResource.delete_profile_photo`."""
        validate_phone_number(phone_number)
        data = await self._http.request(
            method="DELETE",
            path=f"/whatsapp/senders/{quote(phone_number, safe='')}/profile/photo",
        )
        try:
            return WhatsAppSenderProfile(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def get_conversational_components(
        self, phone_number: str
    ) -> WhatsAppConversationalComponents:
        """Get a sender's ice breakers and commands.
        See :meth:`WhatsAppSendersResource.get_conversational_components`."""
        validate_phone_number(phone_number)
        data = await self._http.request(
            method="GET",
            path=f"/whatsapp/senders/{quote(phone_number, safe='')}/conversational_components",
        )
        try:
            return WhatsAppConversationalComponents(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def update_conversational_components(
        self,
        phone_number: str,
        *,
        ice_breakers: Optional[List[str]] = None,
        commands: Optional[List[Union[WhatsAppCommand, Dict[str, str]]]] = None,
    ) -> WhatsAppConversationalComponents:
        """Replace a sender's ice breakers, commands, or both.
        See :meth:`WhatsAppSendersResource.update_conversational_components`."""
        validate_phone_number(phone_number)
        data = await self._http.request(
            method="PATCH",
            path=f"/whatsapp/senders/{quote(phone_number, safe='')}/conversational_components",
            body=_components_body(ice_breakers, commands),
        )
        try:
            return WhatsAppConversationalComponents(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def set_calling(
        self, phone_number: str, *, enabled: bool
    ) -> WhatsAppCallingSettings:
        """Switch WhatsApp calling on or off.
        See :meth:`WhatsAppSendersResource.set_calling`."""
        validate_phone_number(phone_number)
        data = await self._http.request(
            method="PATCH",
            path=f"/whatsapp/senders/{quote(phone_number, safe='')}/calling",
            body={"enabled": enabled},
        )
        try:
            return WhatsAppCallingSettings(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class AsyncWhatsAppTemplatesResource:
    """Templates sub-resource for Meta-reviewed message templates (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list(self) -> WhatsAppTemplateListResponse:
        """List your WhatsApp templates with review status and quality rating.
        See :meth:`WhatsAppTemplatesResource.list`."""
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


def _signup_body(
    phone_number: str,
    business_account_id: Optional[str],
    verification_method: Optional[str],
    display_name: Optional[str],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"phoneNumber": phone_number}
    if business_account_id is None:
        if verification_method is not None or display_name is not None:
            raise ValidationError(
                "verification_method and display_name need a business_account_id"
            )
        return payload
    if not isinstance(business_account_id, str) or not business_account_id.strip():
        raise ValidationError("business_account_id must be a non-empty string")
    payload["businessAccountId"] = business_account_id
    if verification_method is not None:
        payload["verificationMethod"] = verification_method
    if display_name is not None:
        payload["displayName"] = display_name
    return payload


def _resend_body(verification_method: Optional[str]) -> Dict[str, Any]:
    if verification_method is None:
        return {}
    return {"verificationMethod": verification_method}


def _components_body(
    ice_breakers: Optional[List[str]],
    commands: Optional[List[Union[WhatsAppCommand, Dict[str, str]]]],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    if ice_breakers is not None:
        payload["iceBreakers"] = ice_breakers
    if commands is not None:
        payload["commands"] = [
            c.model_dump() if isinstance(c, WhatsAppCommand) else c for c in commands
        ]
    if not payload:
        raise ValidationError("Provide ice_breakers, commands, or both")
    return payload


def _photo_part(
    file: Union[BinaryIO, bytes], content_type: str
) -> Dict[str, Tuple[str, bytes, str]]:
    content = file if isinstance(file, (bytes, bytearray)) else file.read()
    filename = "profile.png" if content_type == "image/png" else "profile.jpg"
    return {"file": (filename, bytes(content), content_type)}


def _invalid_response(e: PydanticValidationError) -> SendlyError:
    """Wrap a pydantic schema error as a SendlyError, matching the SDK's idiom."""
    return SendlyError(
        message=f"Invalid API response format: {e}",
        code="invalid_response",
        status_code=200,
    )
