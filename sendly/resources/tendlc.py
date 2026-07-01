"""
10DLC Resource - Register for carrier review to text from local US numbers

Exposes the public 10DLC API. The flow has three steps:

1. Brand - register your business identity with ``create_brand()``. The brand
   starts ``pending``; poll ``get_brand()`` until it becomes ``verified`` (or
   ``failed``, with ``failure_reasons`` explaining why).
2. Campaign - describe your messaging use case under a verified brand with
   ``create_campaign()`` and submit it for carrier review. Starts ``pending``;
   poll ``get_campaign()`` until it becomes ``active``. ``qualify()``
   pre-checks a use case before you create the campaign.
3. Assign - attach a number you own to the active campaign with
   ``assign_number()``. Once the assignment is ``Active``, the number can
   send.

Brand, campaign, and number-assignment writes require a live API key
(``sk_live_v1_xxx``) with the ``tendlc:write`` scope.
"""

from typing import Any, Dict, List, Optional

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError
from ..types import (
    TenDlcAssignmentListResponse,
    TenDlcAssignmentResponse,
    TenDlcBrandListResponse,
    TenDlcBrandResponse,
    TenDlcCampaignListResponse,
    TenDlcCampaignResponse,
    TenDlcQualifyResponse,
)
from ..utils.http import AsyncHttpClient, HttpClient


class TenDlcResource:
    """10DLC API resource (sync)

    Example:
        >>> brand = client.ten_dlc.create_brand(
        ...     legal_name='Acme Holdings LLC',
        ...     ein='12-3456789',
        ...     website='https://acme.example',
        ...     email='ops@acme.example',
        ... ).data
        >>> # ...poll client.ten_dlc.get_brand(brand.id) until status == 'verified'
        >>> check = client.ten_dlc.qualify(brand.id, 'MIXED').data
        >>> if check.qualified:
        ...     campaign = client.ten_dlc.create_campaign(
        ...         brand_id=brand.id,
        ...         use_case='MIXED',
        ...         description='Order updates and support replies for Acme customers',
        ...         message_flow='Customers opt in at checkout on acme.example',
        ...         sample_messages=['Your order #123 has shipped!'],
        ...     ).data
        ...     # ...poll client.ten_dlc.get_campaign(campaign.id) until status == 'active'
        ...     client.ten_dlc.assign_number(campaign.id, '+15551234567')
    """

    def __init__(self, http: HttpClient):
        self._http = http

    def list_brands(self) -> TenDlcBrandListResponse:
        """List the brands registered for carrier review."""
        data = self._http.request(method="GET", path="/tendlc/brands")
        try:
            return TenDlcBrandListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def create_brand(
        self,
        legal_name: str,
        *,
        dba: Optional[str] = None,
        ein: Optional[str] = None,
        entity_type: Optional[str] = None,
        vertical: Optional[str] = None,
        website: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        mobile_phone: Optional[str] = None,
        street: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        postal_code: Optional[str] = None,
        country: Optional[str] = None,
        verification_id: Optional[str] = None,
    ) -> TenDlcBrandResponse:
        """Register a brand for carrier review - step 1 of enabling local-number
        texting. Requires a live API key.

        The brand starts ``pending``. Poll :meth:`get_brand` until it becomes
        ``verified`` before creating a campaign.

        Args:
            legal_name: Legal business name.
            dba: "Doing business as" name, if different from the legal name.
            ein: Business registration number (e.g. EIN).
            entity_type: Business entity type (e.g. ``PRIVATE_PROFIT``,
                ``SOLE_PROPRIETOR``); defaults to ``PRIVATE_PROFIT``.
            vertical: Industry vertical.
            website: Business website URL.
            email: Business contact email.
            phone: Business phone number.
            mobile_phone: Business mobile phone number.
            street: Street address.
            city: City.
            state: State or region.
            postal_code: Postal code.
            country: ISO 3166-1 alpha-2 country code; defaults to ``US``.
            verification_id: Existing Sendly verification to prefill business
                details from.
        """
        body = _brand_body(
            legal_name,
            dba,
            ein,
            entity_type,
            vertical,
            website,
            email,
            phone,
            mobile_phone,
            street,
            city,
            state,
            postal_code,
            country,
            verification_id,
        )
        data = self._http.request(method="POST", path="/tendlc/brands", body=body)
        try:
            return TenDlcBrandResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def get_brand(self, id: str) -> TenDlcBrandResponse:
        """Fetch one brand. Also refreshes its carrier-review status, so polling
        this method shows progress (``pending`` -> ``verified``/``failed``).

        Args:
            id: Brand identifier.
        """
        data = self._http.request(method="GET", path=f"/tendlc/brands/{id}")
        try:
            return TenDlcBrandResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def qualify(self, brand_id: str, use_case: str) -> TenDlcQualifyResponse:
        """Pre-check whether a use case qualifies for a brand on the carrier
        network before creating a campaign.

        Args:
            brand_id: Brand identifier.
            use_case: Use-case code (e.g. ``MIXED``, ``MARKETING``,
                ``ACCOUNT_NOTIFICATION``, ``2FA``).
        """
        data = self._http.request(
            method="GET", path=f"/tendlc/brands/{brand_id}/qualify/{use_case}"
        )
        try:
            return TenDlcQualifyResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def list_campaigns(self) -> TenDlcCampaignListResponse:
        """List your messaging campaigns."""
        data = self._http.request(method="GET", path="/tendlc/campaigns")
        try:
            return TenDlcCampaignListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def create_campaign(
        self,
        brand_id: str,
        use_case: str,
        description: str,
        message_flow: str,
        sample_messages: List[str],
        *,
        sub_use_cases: Optional[List[str]] = None,
        opt_in_keywords: Optional[str] = None,
        opt_out_keywords: Optional[str] = None,
        help_keywords: Optional[str] = None,
        opt_in_message: Optional[str] = None,
        opt_out_message: Optional[str] = None,
        help_message: Optional[str] = None,
        embedded_link: Optional[bool] = None,
        embedded_phone: Optional[bool] = None,
    ) -> TenDlcCampaignResponse:
        """Create a messaging campaign under a verified brand and submit it for
        carrier review. Requires a live API key.

        The campaign starts ``pending``. Poll :meth:`get_campaign` until it
        becomes ``active`` before assigning numbers.

        Args:
            brand_id: The verified brand to create the campaign under.
            use_case: Primary use-case code (e.g. ``MIXED``, ``MARKETING``).
            description: What the campaign sends and why.
            message_flow: How recipients opt in to receive messages.
            sample_messages: Example messages the campaign sends (the first 5
                are used).
            sub_use_cases: Sub-use-case codes.
            opt_in_keywords: Comma-separated keywords that opt a recipient in.
            opt_out_keywords: Comma-separated keywords that opt a recipient out.
            help_keywords: Comma-separated keywords that request help.
            opt_in_message: Auto-reply sent on opt-in.
            opt_out_message: Auto-reply sent on opt-out.
            help_message: Auto-reply sent on a help request.
            embedded_link: Whether messages may contain links; defaults to True.
            embedded_phone: Whether messages may contain phone numbers;
                defaults to False.
        """
        body = _campaign_body(
            brand_id,
            use_case,
            description,
            message_flow,
            sample_messages,
            sub_use_cases,
            opt_in_keywords,
            opt_out_keywords,
            help_keywords,
            opt_in_message,
            opt_out_message,
            help_message,
            embedded_link,
            embedded_phone,
        )
        data = self._http.request(method="POST", path="/tendlc/campaigns", body=body)
        try:
            return TenDlcCampaignResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def get_campaign(self, id: str) -> TenDlcCampaignResponse:
        """Fetch one campaign. Also refreshes its carrier-review status, so
        polling shows progress (``pending`` -> ``active``) including throughput
        once carriers approve.

        Args:
            id: Campaign identifier.
        """
        data = self._http.request(method="GET", path=f"/tendlc/campaigns/{id}")
        try:
            return TenDlcCampaignResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def assign_number(self, campaign_id: str, phone_number: str) -> TenDlcAssignmentResponse:
        """Assign a phone number you own to an active (carrier-approved)
        campaign, making the number sendable. Requires a live API key.

        Idempotent - re-assigning the same number to the same campaign returns
        the existing assignment.

        Args:
            campaign_id: Campaign identifier.
            phone_number: E.164 number the workspace already owns.
        """
        data = self._http.request(
            method="POST",
            path=f"/tendlc/campaigns/{campaign_id}/assign",
            body={"phoneNumber": phone_number},
        )
        try:
            return TenDlcAssignmentResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    def list_assignments(self) -> TenDlcAssignmentListResponse:
        """List your number-to-campaign assignments."""
        data = self._http.request(method="GET", path="/tendlc/assignments")
        try:
            return TenDlcAssignmentListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


class AsyncTenDlcResource:
    """10DLC API resource (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list_brands(self) -> TenDlcBrandListResponse:
        """List the brands registered for carrier review."""
        data = await self._http.request(method="GET", path="/tendlc/brands")
        try:
            return TenDlcBrandListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def create_brand(
        self,
        legal_name: str,
        *,
        dba: Optional[str] = None,
        ein: Optional[str] = None,
        entity_type: Optional[str] = None,
        vertical: Optional[str] = None,
        website: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        mobile_phone: Optional[str] = None,
        street: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        postal_code: Optional[str] = None,
        country: Optional[str] = None,
        verification_id: Optional[str] = None,
    ) -> TenDlcBrandResponse:
        """Register a brand for carrier review. See :meth:`TenDlcResource.create_brand`."""
        body = _brand_body(
            legal_name,
            dba,
            ein,
            entity_type,
            vertical,
            website,
            email,
            phone,
            mobile_phone,
            street,
            city,
            state,
            postal_code,
            country,
            verification_id,
        )
        data = await self._http.request(method="POST", path="/tendlc/brands", body=body)
        try:
            return TenDlcBrandResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def get_brand(self, id: str) -> TenDlcBrandResponse:
        """Fetch one brand with its current carrier-review status."""
        data = await self._http.request(method="GET", path=f"/tendlc/brands/{id}")
        try:
            return TenDlcBrandResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def qualify(self, brand_id: str, use_case: str) -> TenDlcQualifyResponse:
        """Pre-check whether a use case qualifies for a brand on the carrier network."""
        data = await self._http.request(
            method="GET", path=f"/tendlc/brands/{brand_id}/qualify/{use_case}"
        )
        try:
            return TenDlcQualifyResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def list_campaigns(self) -> TenDlcCampaignListResponse:
        """List your messaging campaigns."""
        data = await self._http.request(method="GET", path="/tendlc/campaigns")
        try:
            return TenDlcCampaignListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def create_campaign(
        self,
        brand_id: str,
        use_case: str,
        description: str,
        message_flow: str,
        sample_messages: List[str],
        *,
        sub_use_cases: Optional[List[str]] = None,
        opt_in_keywords: Optional[str] = None,
        opt_out_keywords: Optional[str] = None,
        help_keywords: Optional[str] = None,
        opt_in_message: Optional[str] = None,
        opt_out_message: Optional[str] = None,
        help_message: Optional[str] = None,
        embedded_link: Optional[bool] = None,
        embedded_phone: Optional[bool] = None,
    ) -> TenDlcCampaignResponse:
        """Create a messaging campaign. See :meth:`TenDlcResource.create_campaign`."""
        body = _campaign_body(
            brand_id,
            use_case,
            description,
            message_flow,
            sample_messages,
            sub_use_cases,
            opt_in_keywords,
            opt_out_keywords,
            help_keywords,
            opt_in_message,
            opt_out_message,
            help_message,
            embedded_link,
            embedded_phone,
        )
        data = await self._http.request(method="POST", path="/tendlc/campaigns", body=body)
        try:
            return TenDlcCampaignResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def get_campaign(self, id: str) -> TenDlcCampaignResponse:
        """Fetch one campaign with its current carrier-review status."""
        data = await self._http.request(method="GET", path=f"/tendlc/campaigns/{id}")
        try:
            return TenDlcCampaignResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def assign_number(
        self, campaign_id: str, phone_number: str
    ) -> TenDlcAssignmentResponse:
        """Assign a number to an active campaign. See :meth:`TenDlcResource.assign_number`."""
        data = await self._http.request(
            method="POST",
            path=f"/tendlc/campaigns/{campaign_id}/assign",
            body={"phoneNumber": phone_number},
        )
        try:
            return TenDlcAssignmentResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e

    async def list_assignments(self) -> TenDlcAssignmentListResponse:
        """List your number-to-campaign assignments."""
        data = await self._http.request(method="GET", path="/tendlc/assignments")
        try:
            return TenDlcAssignmentListResponse(**data)
        except PydanticValidationError as e:
            raise _invalid_response(e) from e


def _brand_body(
    legal_name: str,
    dba: Optional[str],
    ein: Optional[str],
    entity_type: Optional[str],
    vertical: Optional[str],
    website: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    mobile_phone: Optional[str],
    street: Optional[str],
    city: Optional[str],
    state: Optional[str],
    postal_code: Optional[str],
    country: Optional[str],
    verification_id: Optional[str],
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"legalName": legal_name}
    optional: Dict[str, Any] = {
        "dba": dba,
        "ein": ein,
        "entityType": entity_type,
        "vertical": vertical,
        "website": website,
        "email": email,
        "phone": phone,
        "mobilePhone": mobile_phone,
        "street": street,
        "city": city,
        "state": state,
        "postalCode": postal_code,
        "country": country,
        "verificationId": verification_id,
    }
    for key, value in optional.items():
        if value is not None:
            body[key] = value
    return body


def _campaign_body(
    brand_id: str,
    use_case: str,
    description: str,
    message_flow: str,
    sample_messages: List[str],
    sub_use_cases: Optional[List[str]],
    opt_in_keywords: Optional[str],
    opt_out_keywords: Optional[str],
    help_keywords: Optional[str],
    opt_in_message: Optional[str],
    opt_out_message: Optional[str],
    help_message: Optional[str],
    embedded_link: Optional[bool],
    embedded_phone: Optional[bool],
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "brandId": brand_id,
        "useCase": use_case,
        "description": description,
        "messageFlow": message_flow,
        "sampleMessages": sample_messages,
    }
    optional: Dict[str, Any] = {
        "subUseCases": sub_use_cases,
        "optInKeywords": opt_in_keywords,
        "optOutKeywords": opt_out_keywords,
        "helpKeywords": help_keywords,
        "optInMessage": opt_in_message,
        "optOutMessage": opt_out_message,
        "helpMessage": help_message,
        "embeddedLink": embedded_link,
        "embeddedPhone": embedded_phone,
    }
    for key, value in optional.items():
        if value is not None:
            body[key] = value
    return body


def _invalid_response(e: PydanticValidationError) -> SendlyError:
    """Wrap a pydantic schema error as a SendlyError, matching the SDK's idiom."""
    return SendlyError(
        message=f"Invalid API response format: {e}",
        code="invalid_response",
        status_code=200,
    )
