"""
Campaigns Resource - Bulk SMS Campaign Management
"""

from typing import Any, Dict, List, Optional

from ..types import (
    Campaign,
    CampaignListResponse,
    CampaignPreview,
)
from ..utils.http import AsyncHttpClient, HttpClient


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
            contact_list_ids: List IDs to send to
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

        data = self._http.request("POST", "/campaigns", json=body)
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
            status: Filter by status (draft, scheduled, sending, sent, cancelled)

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
        data = self._http.request("GET", f"/campaigns/{campaign_id}")
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
        """Update a campaign (draft or scheduled only)"""
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if text is not None:
            body["text"] = text
        if template_id is not None:
            body["templateId"] = template_id
        if contact_list_ids is not None:
            body["contactListIds"] = contact_list_ids

        data = self._http.request("PATCH", f"/campaigns/{campaign_id}", json=body)
        return self._transform_campaign(data)

    def delete(self, campaign_id: str) -> None:
        """Delete a campaign (draft or cancelled only)"""
        self._http.request("DELETE", f"/campaigns/{campaign_id}")

    def preview(self, campaign_id: str) -> CampaignPreview:
        """Preview campaign before sending

        Returns recipient count, credit estimate, and breakdown.
        """
        data = self._http.request("GET", f"/campaigns/{campaign_id}/preview")
        return CampaignPreview(
            id=data["id"],
            recipient_count=data["recipient_count"],
            estimated_segments=data["estimated_segments"],
            estimated_credits=data["estimated_credits"],
            current_balance=data["current_balance"],
            has_enough_credits=data["has_enough_credits"],
            breakdown=data.get("breakdown"),
        )

    def send(self, campaign_id: str) -> Campaign:
        """Send a campaign immediately"""
        data = self._http.request("POST", f"/campaigns/{campaign_id}/send")
        return self._transform_campaign(data)

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

        data = self._http.request("POST", f"/campaigns/{campaign_id}/schedule", json=body)
        return self._transform_campaign(data)

    def cancel(self, campaign_id: str) -> Campaign:
        """Cancel a scheduled campaign"""
        data = self._http.request("POST", f"/campaigns/{campaign_id}/cancel")
        return self._transform_campaign(data)

    def clone(self, campaign_id: str) -> Campaign:
        """Clone a campaign (creates new draft)"""
        data = self._http.request("POST", f"/campaigns/{campaign_id}/clone")
        return self._transform_campaign(data)

    def _transform_campaign(self, data: Dict[str, Any]) -> Campaign:
        return Campaign(
            id=data["id"],
            name=data["name"],
            text=data["text"],
            template_id=data.get("template_id"),
            contact_list_ids=data.get("contact_list_ids", []),
            status=data["status"],
            recipient_count=data.get("recipient_count", 0),
            sent_count=data.get("sent_count", 0),
            delivered_count=data.get("delivered_count", 0),
            failed_count=data.get("failed_count", 0),
            estimated_credits=data.get("estimated_credits", 0),
            credits_used=data.get("credits_used", 0),
            scheduled_at=data.get("scheduled_at"),
            timezone=data.get("timezone"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


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
        """Create a new campaign (draft)"""
        body: Dict[str, Any] = {
            "name": name,
            "text": text,
            "contactListIds": contact_list_ids,
        }
        if template_id:
            body["templateId"] = template_id

        data = await self._http.request("POST", "/campaigns", json=body)
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
        data = await self._http.request("GET", f"/campaigns/{campaign_id}")
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
        """Update a campaign (draft or scheduled only)"""
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if text is not None:
            body["text"] = text
        if template_id is not None:
            body["templateId"] = template_id
        if contact_list_ids is not None:
            body["contactListIds"] = contact_list_ids

        data = await self._http.request("PATCH", f"/campaigns/{campaign_id}", json=body)
        return self._transform_campaign(data)

    async def delete(self, campaign_id: str) -> None:
        """Delete a campaign (draft or cancelled only)"""
        await self._http.request("DELETE", f"/campaigns/{campaign_id}")

    async def preview(self, campaign_id: str) -> CampaignPreview:
        """Preview campaign before sending"""
        data = await self._http.request("GET", f"/campaigns/{campaign_id}/preview")
        return CampaignPreview(
            id=data["id"],
            recipient_count=data["recipient_count"],
            estimated_segments=data["estimated_segments"],
            estimated_credits=data["estimated_credits"],
            current_balance=data["current_balance"],
            has_enough_credits=data["has_enough_credits"],
            breakdown=data.get("breakdown"),
        )

    async def send(self, campaign_id: str) -> Campaign:
        """Send a campaign immediately"""
        data = await self._http.request("POST", f"/campaigns/{campaign_id}/send")
        return self._transform_campaign(data)

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

        data = await self._http.request("POST", f"/campaigns/{campaign_id}/schedule", json=body)
        return self._transform_campaign(data)

    async def cancel(self, campaign_id: str) -> Campaign:
        """Cancel a scheduled campaign"""
        data = await self._http.request("POST", f"/campaigns/{campaign_id}/cancel")
        return self._transform_campaign(data)

    async def clone(self, campaign_id: str) -> Campaign:
        """Clone a campaign (creates new draft)"""
        data = await self._http.request("POST", f"/campaigns/{campaign_id}/clone")
        return self._transform_campaign(data)

    def _transform_campaign(self, data: Dict[str, Any]) -> Campaign:
        return Campaign(
            id=data["id"],
            name=data["name"],
            text=data["text"],
            template_id=data.get("template_id"),
            contact_list_ids=data.get("contact_list_ids", []),
            status=data["status"],
            recipient_count=data.get("recipient_count", 0),
            sent_count=data.get("sent_count", 0),
            delivered_count=data.get("delivered_count", 0),
            failed_count=data.get("failed_count", 0),
            estimated_credits=data.get("estimated_credits", 0),
            credits_used=data.get("credits_used", 0),
            scheduled_at=data.get("scheduled_at"),
            timezone=data.get("timezone"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
