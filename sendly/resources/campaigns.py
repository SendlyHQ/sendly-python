"""
Campaigns Resource - Bulk SMS Campaign Management
"""

from typing import Any, Dict, List, Optional

from pydantic import ValidationError as PydanticValidationError

from ..errors import SendlyError
from ..types import (
    Campaign,
    CampaignListResponse,
    CampaignPreview,
    CampaignSendResult,
)
from ..utils.http import AsyncHttpClient, HttpClient
from urllib.parse import quote


def _pick(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if data.get(key) is not None:
            return data[key]
    return default


def _invalid_response(e: PydanticValidationError) -> SendlyError:
    return SendlyError(
        message=f"Invalid API response format: {e}",
        code="invalid_response",
        status_code=200,
    )


def _campaign(data: Dict[str, Any]) -> Campaign:
    list_ids = data.get("contact_list_ids")
    if list_ids is None:
        list_ids = [data["targetListId"]] if data.get("targetListId") else []
    try:
        return Campaign(
            id=data["id"],
            name=data["name"],
            text=_pick(data, "text", "messageText"),
            template_id=_pick(data, "template_id", "templateId"),
            contact_list_ids=list_ids,
            status=data["status"],
            recipient_count=_pick(data, "recipient_count", "totalRecipients", default=0),
            sent_count=_pick(data, "sent_count", "sentCount", default=0),
            delivered_count=_pick(data, "delivered_count", "deliveredCount", default=0),
            failed_count=_pick(data, "failed_count", "failedCount", default=0),
            estimated_credits=_pick(data, "estimated_credits", "estimatedCredits", default=0),
            credits_used=_pick(data, "credits_used", "creditsUsed", default=0),
            scheduled_at=_pick(data, "scheduled_at", "scheduledAt"),
            timezone=data.get("timezone"),
            started_at=_pick(data, "started_at", "sentAt"),
            completed_at=_pick(data, "completed_at", "completedAt"),
            created_at=_pick(data, "created_at", "createdAt"),
            updated_at=_pick(data, "updated_at", "updatedAt"),
        )
    except PydanticValidationError as e:
        raise _invalid_response(e) from e


def _preview(campaign_id: str, data: Dict[str, Any]) -> CampaignPreview:
    try:
        return CampaignPreview(
            id=_pick(data, "id", default=campaign_id),
            recipient_count=_pick(
                data, "recipient_count", "recipientCount", "totalRecipients", default=0
            ),
            estimated_segments=data.get("estimated_segments"),
            estimated_credits=_pick(data, "estimated_credits", "estimatedCredits", default=0),
            current_balance=_pick(data, "current_balance", "currentBalance", default=0),
            has_enough_credits=_pick(
                data, "has_enough_credits", "hasEnoughCredits", default=False
            ),
            breakdown=data.get("breakdown"),
            blocked_count=_pick(data, "blocked_count", "blockedCount"),
            sendable_count=_pick(data, "sendable_count", "sendableCount"),
            by_country=_pick(data, "by_country", "byCountry"),
            warnings=data.get("warnings"),
            messaging_profile=_pick(data, "messaging_profile", "messagingProfile"),
            opted_out_count=_pick(data, "opted_out_count", "optedOutCount"),
            invalid_count=_pick(data, "invalid_count", "invalidCount"),
            sample_recipients=_pick(data, "sample_recipients", "sampleRecipients"),
        )
    except PydanticValidationError as e:
        raise _invalid_response(e) from e


def _send_result(data: Dict[str, Any]) -> CampaignSendResult:
    try:
        return CampaignSendResult(**data)
    except PydanticValidationError as e:
        raise _invalid_response(e) from e


class CampaignsResource:
    """Campaigns API resource for bulk SMS campaign management (sync)

    Example:
        >>> campaign = client.campaigns.create(
        ...     name='Welcome Campaign',
        ...     text='Hello {{name}}!',
        ...     contact_list_ids=['lst_xxx']
        ... )
        >>> preview = client.campaigns.preview(campaign.id)
        >>> client.campaigns.send(campaign.id)
    """

    def __init__(self, http: HttpClient):
        self._http = http

    def create(
        self,
        name: str,
        text: str,
        contact_list_ids: List[str],
        template_id: Optional[str] = None,
    ) -> Campaign:
        """Create a new campaign (draft)

        Args:
            name: Campaign name
            text: Message text with optional {{variables}}
            contact_list_ids: One contact list ID, in a one-element list. A
                campaign targets one list; the API answers 400 invalid_request
                to more than one
            template_id: Optional template ID

        Returns:
            The created campaign
        """
        body: Dict[str, Any] = {
            "name": name,
            "text": text,
            "contactListIds": contact_list_ids,
        }
        if template_id:
            body["templateId"] = template_id

        data = self._http.request("POST", "/campaigns", body=body)
        return self._transform_campaign(data)

    def list(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
    ) -> CampaignListResponse:
        """List campaigns with optional filtering

        Args:
            limit: Max campaigns to return
            offset: Pagination offset
            status: Filter by status (draft, scheduled, sending, completed,
                cancelled or failed; 'sent' also lists completed campaigns)

        Returns:
            List of campaigns with pagination
        """
        params: Dict[str, Any] = {}
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        if status:
            params["status"] = status

        data = self._http.request("GET", "/campaigns", params=params if params else None)
        return CampaignListResponse(
            campaigns=[self._transform_campaign(c) for c in data["campaigns"]],
            total=data["total"],
            limit=data["limit"],
            offset=data["offset"],
        )

    def get(self, campaign_id: str) -> Campaign:
        """Get a campaign by ID"""
        data = self._http.request("GET", f"/campaigns/{quote(campaign_id, safe='')}")
        return self._transform_campaign(data)

    def update(
        self,
        campaign_id: str,
        *,
        name: Optional[str] = None,
        text: Optional[str] = None,
        template_id: Optional[str] = None,
        contact_list_ids: Optional[List[str]] = None,
    ) -> Campaign:
        """Update a campaign (draft or scheduled only)

        Args:
            campaign_id: Campaign ID
            name: Campaign name
            text: Message text with optional {{variables}}
            template_id: Optional template ID
            contact_list_ids: One contact list ID, in a one-element list. A
                campaign targets one list; the API answers 400 invalid_request
                to more than one
        """
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if text is not None:
            body["text"] = text
        if template_id is not None:
            body["templateId"] = template_id
        if contact_list_ids is not None:
            body["contactListIds"] = contact_list_ids

        data = self._http.request("PATCH", f"/campaigns/{quote(campaign_id, safe='')}", body=body)
        return self._transform_campaign(data)

    def delete(self, campaign_id: str) -> None:
        """Delete a campaign (draft or cancelled only)"""
        self._http.request("DELETE", f"/campaigns/{quote(campaign_id, safe='')}")

    def preview(self, campaign_id: str) -> CampaignPreview:
        """Preview campaign before sending

        Returns recipient count, credit estimate, balance, and a per-country
        breakdown.
        """
        data = self._http.request("GET", f"/campaigns/{quote(campaign_id, safe='')}/preview")
        return _preview(campaign_id, data)

    def send(self, campaign_id: str, from_: Optional[str] = None) -> CampaignSendResult:
        """Send a campaign immediately

        Args:
            campaign_id: Campaign ID
            from_: Optional number of yours to send from

        Returns:
            The batch the messages went out in. Call :meth:`get` for the
            campaign itself
        """
        body = {"from": from_} if from_ else None
        data = self._http.request(
            "POST", f"/campaigns/{quote(campaign_id, safe='')}/send", body=body
        )
        return _send_result(data)

    def schedule(
        self,
        campaign_id: str,
        scheduled_at: str,
        timezone: Optional[str] = None,
    ) -> Campaign:
        """Schedule a campaign for later

        Args:
            campaign_id: Campaign ID
            scheduled_at: ISO 8601 datetime
            timezone: IANA timezone (e.g., 'America/New_York')
        """
        body: Dict[str, Any] = {"scheduledAt": scheduled_at}
        if timezone:
            body["timezone"] = timezone

        data = self._http.request("POST", f"/campaigns/{quote(campaign_id, safe='')}/schedule", body=body)
        return self._transform_campaign(data)

    def cancel(self, campaign_id: str) -> Campaign:
        """Cancel a scheduled campaign"""
        data = self._http.request("POST", f"/campaigns/{quote(campaign_id, safe='')}/cancel")
        return self._transform_campaign(data)

    def clone(self, campaign_id: str) -> Campaign:
        """Clone a campaign (creates new draft)"""
        data = self._http.request("POST", f"/campaigns/{quote(campaign_id, safe='')}/clone")
        return self._transform_campaign(data)

    def _transform_campaign(self, data: Dict[str, Any]) -> Campaign:
        return _campaign(data)


class AsyncCampaignsResource:
    """Campaigns API resource for bulk SMS campaign management (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def create(
        self,
        name: str,
        text: str,
        contact_list_ids: List[str],
        template_id: Optional[str] = None,
    ) -> Campaign:
        """Create a new campaign (draft)

        Args:
            name: Campaign name
            text: Message text with optional {{variables}}
            contact_list_ids: One contact list ID, in a one-element list. A
                campaign targets one list; the API answers 400 invalid_request
                to more than one
            template_id: Optional template ID
        """
        body: Dict[str, Any] = {
            "name": name,
            "text": text,
            "contactListIds": contact_list_ids,
        }
        if template_id:
            body["templateId"] = template_id

        data = await self._http.request("POST", "/campaigns", body=body)
        return self._transform_campaign(data)

    async def list(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
    ) -> CampaignListResponse:
        """List campaigns with optional filtering"""
        params: Dict[str, Any] = {}
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        if status:
            params["status"] = status

        data = await self._http.request("GET", "/campaigns", params=params if params else None)
        return CampaignListResponse(
            campaigns=[self._transform_campaign(c) for c in data["campaigns"]],
            total=data["total"],
            limit=data["limit"],
            offset=data["offset"],
        )

    async def get(self, campaign_id: str) -> Campaign:
        """Get a campaign by ID"""
        data = await self._http.request("GET", f"/campaigns/{quote(campaign_id, safe='')}")
        return self._transform_campaign(data)

    async def update(
        self,
        campaign_id: str,
        *,
        name: Optional[str] = None,
        text: Optional[str] = None,
        template_id: Optional[str] = None,
        contact_list_ids: Optional[List[str]] = None,
    ) -> Campaign:
        """Update a campaign (draft or scheduled only)

        Args:
            campaign_id: Campaign ID
            name: Campaign name
            text: Message text with optional {{variables}}
            template_id: Optional template ID
            contact_list_ids: One contact list ID, in a one-element list. A
                campaign targets one list; the API answers 400 invalid_request
                to more than one
        """
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if text is not None:
            body["text"] = text
        if template_id is not None:
            body["templateId"] = template_id
        if contact_list_ids is not None:
            body["contactListIds"] = contact_list_ids

        data = await self._http.request("PATCH", f"/campaigns/{quote(campaign_id, safe='')}", body=body)
        return self._transform_campaign(data)

    async def delete(self, campaign_id: str) -> None:
        """Delete a campaign (draft or cancelled only)"""
        await self._http.request("DELETE", f"/campaigns/{quote(campaign_id, safe='')}")

    async def preview(self, campaign_id: str) -> CampaignPreview:
        """Preview campaign before sending"""
        data = await self._http.request("GET", f"/campaigns/{quote(campaign_id, safe='')}/preview")
        return _preview(campaign_id, data)

    async def send(self, campaign_id: str, from_: Optional[str] = None) -> CampaignSendResult:
        """Send a campaign immediately

        Returns the batch the messages went out in; see
        :meth:`CampaignsResource.send`.
        """
        body = {"from": from_} if from_ else None
        data = await self._http.request(
            "POST", f"/campaigns/{quote(campaign_id, safe='')}/send", body=body
        )
        return _send_result(data)

    async def schedule(
        self,
        campaign_id: str,
        scheduled_at: str,
        timezone: Optional[str] = None,
    ) -> Campaign:
        """Schedule a campaign for later"""
        body: Dict[str, Any] = {"scheduledAt": scheduled_at}
        if timezone:
            body["timezone"] = timezone

        data = await self._http.request("POST", f"/campaigns/{quote(campaign_id, safe='')}/schedule", body=body)
        return self._transform_campaign(data)

    async def cancel(self, campaign_id: str) -> Campaign:
        """Cancel a scheduled campaign"""
        data = await self._http.request("POST", f"/campaigns/{quote(campaign_id, safe='')}/cancel")
        return self._transform_campaign(data)

    async def clone(self, campaign_id: str) -> Campaign:
        """Clone a campaign (creates new draft)"""
        data = await self._http.request("POST", f"/campaigns/{quote(campaign_id, safe='')}/clone")
        return self._transform_campaign(data)

    def _transform_campaign(self, data: Dict[str, Any]) -> Campaign:
        return _campaign(data)
