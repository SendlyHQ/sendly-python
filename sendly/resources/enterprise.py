from typing import Any, Dict, List, Optional
from urllib.parse import quote

from ..types import (
    AnalyticsOverview,
    AutoTopUpSettings,
    BillingBreakdown,
    BulkProvisionResult,
    CreatedApiKey,
    CreateOptInPageResult,
    CreditAnalytics,
    DeliveryAnalyticsItem,
    EnterpriseAccount,
    EnterpriseWebhook,
    EnterpriseWebhookTestResult,
    EnterpriseWorkspace,
    EnterpriseWorkspaceDetail,
    EnterpriseWorkspaceKey,
    EnterpriseWorkspaceListResponse,
    Invitation,
    MessageAnalytics,
    OptInPage,
    QuotaSettings,
    ResumeWorkspaceResult,
    SetCustomDomainResult,
    SetWorkspaceWebhookResult,
    SuspendWorkspaceResult,
    TransferCreditsResult,
    WorkspaceCredits,
    WorkspaceWebhook,
)
from ..utils.http import AsyncHttpClient, HttpClient


class WorkspacesSubResource:
    def __init__(self, http: HttpClient):
        self._http = http

    def create(self, name: str, description: Optional[str] = None) -> EnterpriseWorkspace:
        body: Dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description

        response = self._http.request("POST", "/enterprise/workspaces", body=body)
        return EnterpriseWorkspace(**response)

    def list(self) -> EnterpriseWorkspaceListResponse:
        response = self._http.request("GET", "/enterprise/workspaces")
        return EnterpriseWorkspaceListResponse(**response)

    def get(self, workspace_id: str) -> EnterpriseWorkspaceDetail:
        response = self._http.request(
            "GET", f"/enterprise/workspaces/{quote(workspace_id, safe='')}"
        )
        return EnterpriseWorkspaceDetail(**response)

    def delete(self, workspace_id: str) -> None:
        self._http.request("DELETE", f"/enterprise/workspaces/{quote(workspace_id, safe='')}")

    def submit_verification(self, workspace_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "business_name": data.get("business_name"),
            "business_type": data.get("business_type"),
            "ein": data.get("ein"),
            "address": data.get("address"),
            "city": data.get("city"),
            "state": data.get("state"),
            "zip": data.get("zip"),
            "use_case": data.get("use_case"),
            "sample_messages": data.get("sample_messages"),
        }
        if data.get("monthly_volume") is not None:
            body["monthly_volume"] = data["monthly_volume"]

        response = self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/verification/submit",
            body=body,
        )
        return response

    def inherit_verification(self, workspace_id: str, source_workspace_id: str) -> Dict[str, Any]:
        response = self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/verification/inherit",
            body={"source_workspace_id": source_workspace_id},
        )
        return response

    def get_verification(self, workspace_id: str) -> Dict[str, Any]:
        response = self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/verification",
        )
        return response

    def transfer_credits(
        self, workspace_id: str, source_workspace_id: str, amount: int
    ) -> TransferCreditsResult:
        response = self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/transfer-credits",
            body={
                "source_workspace_id": source_workspace_id,
                "amount": amount,
            },
        )
        return TransferCreditsResult(**response)

    def get_credits(self, workspace_id: str) -> WorkspaceCredits:
        response = self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/credits",
        )
        return WorkspaceCredits(**response)

    def create_key(
        self,
        workspace_id: str,
        name: Optional[str] = None,
        type: Optional[str] = None,
    ) -> CreatedApiKey:
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if type is not None:
            body["type"] = type

        response = self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/keys",
            body=body,
        )
        return CreatedApiKey(**response)

    def list_keys(self, workspace_id: str) -> List[EnterpriseWorkspaceKey]:
        response = self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/keys",
        )
        return [EnterpriseWorkspaceKey(**k) for k in response]

    def revoke_key(self, workspace_id: str, key_id: str) -> None:
        self._http.request(
            "DELETE",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/keys/{quote(key_id, safe='')}",
        )

    def list_opt_in_pages(self, workspace_id: str) -> List[OptInPage]:
        response = self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/opt-in-pages",
        )
        return [OptInPage(**item) for item in response]

    def create_opt_in_page(
        self,
        workspace_id: str,
        business_name: str,
        use_case: Optional[str] = None,
        use_case_summary: Optional[str] = None,
        sample_messages: Optional[str] = None,
    ) -> CreateOptInPageResult:
        body: Dict[str, Any] = {"businessName": business_name}
        if use_case is not None:
            body["useCase"] = use_case
        if use_case_summary is not None:
            body["useCaseSummary"] = use_case_summary
        if sample_messages is not None:
            body["sampleMessages"] = sample_messages

        response = self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/opt-in-pages",
            body=body,
        )
        return CreateOptInPageResult(**response)

    def update_opt_in_page(
        self,
        workspace_id: str,
        page_id: str,
        logo_url: Optional[str] = None,
        header_color: Optional[str] = None,
        button_color: Optional[str] = None,
        custom_headline: Optional[str] = None,
        custom_benefits: Optional[List[str]] = None,
    ) -> OptInPage:
        body: Dict[str, Any] = {}
        if logo_url is not None:
            body["logoUrl"] = logo_url
        if header_color is not None:
            body["headerColor"] = header_color
        if button_color is not None:
            body["buttonColor"] = button_color
        if custom_headline is not None:
            body["customHeadline"] = custom_headline
        if custom_benefits is not None:
            body["customBenefits"] = custom_benefits

        response = self._http.request(
            "PATCH",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/opt-in-pages/{quote(page_id, safe='')}",
            body=body,
        )
        return OptInPage(**response)

    def delete_opt_in_page(self, workspace_id: str, page_id: str) -> None:
        self._http.request(
            "DELETE",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/opt-in-pages/{quote(page_id, safe='')}",
        )

    def set_webhook(
        self,
        workspace_id: str,
        url: str,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> SetWorkspaceWebhookResult:
        body: Dict[str, Any] = {"url": url}
        if events is not None:
            body["events"] = events
        if description is not None:
            body["description"] = description

        response = self._http.request(
            "PUT",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/webhooks",
            body=body,
        )
        return SetWorkspaceWebhookResult(**response)

    def list_webhooks(self, workspace_id: str) -> List[WorkspaceWebhook]:
        response = self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/webhooks",
        )
        return [WorkspaceWebhook(**item) for item in response]

    def delete_webhooks(self, workspace_id: str, webhook_id: Optional[str] = None) -> None:
        params: Dict[str, Any] = {}
        if webhook_id is not None:
            params["webhookId"] = webhook_id

        self._http.request(
            "DELETE",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/webhooks",
            params=params if params else None,
        )

    def test_webhook(self, workspace_id: str) -> EnterpriseWebhookTestResult:
        response = self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/webhooks/test",
        )
        return EnterpriseWebhookTestResult(**response)

    def suspend(self, workspace_id: str, reason: Optional[str] = None) -> SuspendWorkspaceResult:
        body: Dict[str, Any] = {}
        if reason is not None:
            body["reason"] = reason

        response = self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/suspend",
            body=body if body else None,
        )
        return SuspendWorkspaceResult(**response)

    def resume(self, workspace_id: str) -> ResumeWorkspaceResult:
        response = self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/resume",
        )
        return ResumeWorkspaceResult(**response)

    def provision_bulk(self, workspaces: List[Dict[str, Any]]) -> BulkProvisionResult:
        response = self._http.request(
            "POST",
            "/enterprise/workspaces/provision/bulk",
            body={"workspaces": workspaces},
        )
        return BulkProvisionResult(**response)

    def set_custom_domain(
        self, workspace_id: str, page_id: str, domain: str
    ) -> SetCustomDomainResult:
        response = self._http.request(
            "PUT",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/pages/{quote(page_id, safe='')}/domain",
            body={"domain": domain},
        )
        return SetCustomDomainResult(**response)

    def send_invitation(self, workspace_id: str, email: str, role: str) -> Invitation:
        response = self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/invitations",
            body={"email": email, "role": role},
        )
        return Invitation(**response)

    def list_invitations(self, workspace_id: str) -> List[Invitation]:
        response = self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/invitations",
        )
        return [Invitation(**item) for item in response]

    def cancel_invitation(self, workspace_id: str, invite_id: str) -> None:
        self._http.request(
            "DELETE",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/invitations/{quote(invite_id, safe='')}",
        )

    def get_quota(self, workspace_id: str) -> QuotaSettings:
        response = self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/quota",
        )
        return QuotaSettings(**response)

    def set_quota(self, workspace_id: str, monthly_message_quota: Optional[int]) -> QuotaSettings:
        response = self._http.request(
            "PUT",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/quota",
            body={"monthlyMessageQuota": monthly_message_quota},
        )
        return QuotaSettings(**response)


class WebhooksSubResource:
    def __init__(self, http: HttpClient):
        self._http = http

    def set(self, url: str) -> EnterpriseWebhook:
        response = self._http.request("PUT", "/enterprise/webhooks", body={"url": url})
        return EnterpriseWebhook(**response)

    def get(self) -> EnterpriseWebhook:
        response = self._http.request("GET", "/enterprise/webhooks")
        return EnterpriseWebhook(**response)

    def delete(self) -> None:
        self._http.request("DELETE", "/enterprise/webhooks")

    def test(self) -> EnterpriseWebhookTestResult:
        response = self._http.request("POST", "/enterprise/webhooks/test")
        return EnterpriseWebhookTestResult(**response)


class AnalyticsSubResource:
    def __init__(self, http: HttpClient):
        self._http = http

    def overview(self) -> AnalyticsOverview:
        response = self._http.request("GET", "/enterprise/analytics/overview")
        return AnalyticsOverview(**response)

    def messages(
        self,
        period: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> MessageAnalytics:
        params: Dict[str, Any] = {}
        if period is not None:
            params["period"] = period
        if workspace_id is not None:
            params["workspaceId"] = workspace_id

        response = self._http.request("GET", "/enterprise/analytics/messages", params=params)
        return MessageAnalytics(**response)

    def delivery(self) -> List[DeliveryAnalyticsItem]:
        response = self._http.request("GET", "/enterprise/analytics/delivery")
        return [DeliveryAnalyticsItem(**item) for item in response]

    def credits(self, period: Optional[str] = None) -> CreditAnalytics:
        params: Dict[str, Any] = {}
        if period is not None:
            params["period"] = period

        response = self._http.request("GET", "/enterprise/analytics/credits", params=params)
        return CreditAnalytics(**response)


class SettingsSubResource:
    def __init__(self, http: HttpClient):
        self._http = http

    def get_auto_top_up(self) -> AutoTopUpSettings:
        response = self._http.request("GET", "/enterprise/settings/auto-top-up")
        return AutoTopUpSettings(**response)

    def update_auto_top_up(
        self,
        enabled: bool,
        threshold: int,
        amount: int,
        source_workspace_id: Optional[str] = None,
    ) -> AutoTopUpSettings:
        body: Dict[str, Any] = {
            "enabled": enabled,
            "threshold": threshold,
            "amount": amount,
        }
        if source_workspace_id is not None:
            body["sourceWorkspaceId"] = source_workspace_id

        response = self._http.request("PUT", "/enterprise/settings/auto-top-up", body=body)
        return AutoTopUpSettings(**response)


class BillingSubResource:
    def __init__(self, http: HttpClient):
        self._http = http

    def get_breakdown(
        self,
        period: Optional[str] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> BillingBreakdown:
        params: Dict[str, Any] = {}
        if period is not None:
            params["period"] = period
        if page is not None:
            params["page"] = str(page)
        if limit is not None:
            params["limit"] = str(limit)

        response = self._http.request(
            "GET",
            "/enterprise/billing/workspace-breakdown",
            params=params if params else None,
        )
        return BillingBreakdown(**response)


class EnterpriseResource:
    def __init__(self, http: HttpClient):
        self._http = http
        self.workspaces = WorkspacesSubResource(http)
        self.webhooks = WebhooksSubResource(http)
        self.analytics = AnalyticsSubResource(http)
        self.settings = SettingsSubResource(http)
        self.billing = BillingSubResource(http)

    def get_account(self) -> EnterpriseAccount:
        response = self._http.request("GET", "/enterprise/account")
        return EnterpriseAccount(**response)

    def provision(self, opts: Dict[str, Any]) -> Dict[str, Any]:
        body: Dict[str, Any] = {"name": opts["name"]}
        if opts.get("sourceWorkspaceId"):
            body["sourceWorkspaceId"] = opts["sourceWorkspaceId"]
        if opts.get("inheritWithNewNumber"):
            body["inheritWithNewNumber"] = True
        if opts.get("verification"):
            body["verification"] = opts["verification"]
        if opts.get("creditAmount") is not None:
            body["creditAmount"] = opts["creditAmount"]
        if opts.get("creditSourceWorkspaceId"):
            body["creditSourceWorkspaceId"] = opts["creditSourceWorkspaceId"]
        if opts.get("keyName"):
            body["keyName"] = opts["keyName"]
        if opts.get("keyType"):
            body["keyType"] = opts["keyType"]
        if opts.get("webhookUrl"):
            body["webhookUrl"] = opts["webhookUrl"]
        if opts.get("generateOptInPage") is not None:
            body["generateOptInPage"] = opts["generateOptInPage"]

        response = self._http.request("POST", "/enterprise/workspaces/provision", body=body)
        return response


class AsyncWorkspacesSubResource:
    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def create(self, name: str, description: Optional[str] = None) -> EnterpriseWorkspace:
        body: Dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description

        response = await self._http.request("POST", "/enterprise/workspaces", body=body)
        return EnterpriseWorkspace(**response)

    async def list(self) -> EnterpriseWorkspaceListResponse:
        response = await self._http.request("GET", "/enterprise/workspaces")
        return EnterpriseWorkspaceListResponse(**response)

    async def get(self, workspace_id: str) -> EnterpriseWorkspaceDetail:
        response = await self._http.request(
            "GET", f"/enterprise/workspaces/{quote(workspace_id, safe='')}"
        )
        return EnterpriseWorkspaceDetail(**response)

    async def delete(self, workspace_id: str) -> None:
        await self._http.request("DELETE", f"/enterprise/workspaces/{quote(workspace_id, safe='')}")

    async def submit_verification(self, workspace_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "business_name": data.get("business_name"),
            "business_type": data.get("business_type"),
            "ein": data.get("ein"),
            "address": data.get("address"),
            "city": data.get("city"),
            "state": data.get("state"),
            "zip": data.get("zip"),
            "use_case": data.get("use_case"),
            "sample_messages": data.get("sample_messages"),
        }
        if data.get("monthly_volume") is not None:
            body["monthly_volume"] = data["monthly_volume"]

        response = await self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/verification/submit",
            body=body,
        )
        return response

    async def inherit_verification(
        self, workspace_id: str, source_workspace_id: str
    ) -> Dict[str, Any]:
        response = await self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/verification/inherit",
            body={"source_workspace_id": source_workspace_id},
        )
        return response

    async def get_verification(self, workspace_id: str) -> Dict[str, Any]:
        response = await self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/verification",
        )
        return response

    async def transfer_credits(
        self, workspace_id: str, source_workspace_id: str, amount: int
    ) -> TransferCreditsResult:
        response = await self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/transfer-credits",
            body={
                "source_workspace_id": source_workspace_id,
                "amount": amount,
            },
        )
        return TransferCreditsResult(**response)

    async def get_credits(self, workspace_id: str) -> WorkspaceCredits:
        response = await self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/credits",
        )
        return WorkspaceCredits(**response)

    async def create_key(
        self,
        workspace_id: str,
        name: Optional[str] = None,
        type: Optional[str] = None,
    ) -> CreatedApiKey:
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if type is not None:
            body["type"] = type

        response = await self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/keys",
            body=body,
        )
        return CreatedApiKey(**response)

    async def list_keys(self, workspace_id: str) -> List[EnterpriseWorkspaceKey]:
        response = await self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/keys",
        )
        return [EnterpriseWorkspaceKey(**k) for k in response]

    async def revoke_key(self, workspace_id: str, key_id: str) -> None:
        await self._http.request(
            "DELETE",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/keys/{quote(key_id, safe='')}",
        )

    async def list_opt_in_pages(self, workspace_id: str) -> List[OptInPage]:
        response = await self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/opt-in-pages",
        )
        return [OptInPage(**item) for item in response]

    async def create_opt_in_page(
        self,
        workspace_id: str,
        business_name: str,
        use_case: Optional[str] = None,
        use_case_summary: Optional[str] = None,
        sample_messages: Optional[str] = None,
    ) -> CreateOptInPageResult:
        body: Dict[str, Any] = {"businessName": business_name}
        if use_case is not None:
            body["useCase"] = use_case
        if use_case_summary is not None:
            body["useCaseSummary"] = use_case_summary
        if sample_messages is not None:
            body["sampleMessages"] = sample_messages

        response = await self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/opt-in-pages",
            body=body,
        )
        return CreateOptInPageResult(**response)

    async def update_opt_in_page(
        self,
        workspace_id: str,
        page_id: str,
        logo_url: Optional[str] = None,
        header_color: Optional[str] = None,
        button_color: Optional[str] = None,
        custom_headline: Optional[str] = None,
        custom_benefits: Optional[List[str]] = None,
    ) -> OptInPage:
        body: Dict[str, Any] = {}
        if logo_url is not None:
            body["logoUrl"] = logo_url
        if header_color is not None:
            body["headerColor"] = header_color
        if button_color is not None:
            body["buttonColor"] = button_color
        if custom_headline is not None:
            body["customHeadline"] = custom_headline
        if custom_benefits is not None:
            body["customBenefits"] = custom_benefits

        response = await self._http.request(
            "PATCH",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/opt-in-pages/{quote(page_id, safe='')}",
            body=body,
        )
        return OptInPage(**response)

    async def delete_opt_in_page(self, workspace_id: str, page_id: str) -> None:
        await self._http.request(
            "DELETE",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/opt-in-pages/{quote(page_id, safe='')}",
        )

    async def set_webhook(
        self,
        workspace_id: str,
        url: str,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> SetWorkspaceWebhookResult:
        body: Dict[str, Any] = {"url": url}
        if events is not None:
            body["events"] = events
        if description is not None:
            body["description"] = description

        response = await self._http.request(
            "PUT",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/webhooks",
            body=body,
        )
        return SetWorkspaceWebhookResult(**response)

    async def list_webhooks(self, workspace_id: str) -> List[WorkspaceWebhook]:
        response = await self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/webhooks",
        )
        return [WorkspaceWebhook(**item) for item in response]

    async def delete_webhooks(self, workspace_id: str, webhook_id: Optional[str] = None) -> None:
        params: Dict[str, Any] = {}
        if webhook_id is not None:
            params["webhookId"] = webhook_id

        await self._http.request(
            "DELETE",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/webhooks",
            params=params if params else None,
        )

    async def test_webhook(self, workspace_id: str) -> EnterpriseWebhookTestResult:
        response = await self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/webhooks/test",
        )
        return EnterpriseWebhookTestResult(**response)

    async def suspend(
        self, workspace_id: str, reason: Optional[str] = None
    ) -> SuspendWorkspaceResult:
        body: Dict[str, Any] = {}
        if reason is not None:
            body["reason"] = reason

        response = await self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/suspend",
            body=body if body else None,
        )
        return SuspendWorkspaceResult(**response)

    async def resume(self, workspace_id: str) -> ResumeWorkspaceResult:
        response = await self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/resume",
        )
        return ResumeWorkspaceResult(**response)

    async def provision_bulk(self, workspaces: List[Dict[str, Any]]) -> BulkProvisionResult:
        response = await self._http.request(
            "POST",
            "/enterprise/workspaces/provision/bulk",
            body={"workspaces": workspaces},
        )
        return BulkProvisionResult(**response)

    async def set_custom_domain(
        self, workspace_id: str, page_id: str, domain: str
    ) -> SetCustomDomainResult:
        response = await self._http.request(
            "PUT",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/pages/{quote(page_id, safe='')}/domain",
            body={"domain": domain},
        )
        return SetCustomDomainResult(**response)

    async def send_invitation(self, workspace_id: str, email: str, role: str) -> Invitation:
        response = await self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/invitations",
            body={"email": email, "role": role},
        )
        return Invitation(**response)

    async def list_invitations(self, workspace_id: str) -> List[Invitation]:
        response = await self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/invitations",
        )
        return [Invitation(**item) for item in response]

    async def cancel_invitation(self, workspace_id: str, invite_id: str) -> None:
        await self._http.request(
            "DELETE",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/invitations/{quote(invite_id, safe='')}",
        )

    async def get_quota(self, workspace_id: str) -> QuotaSettings:
        response = await self._http.request(
            "GET",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/quota",
        )
        return QuotaSettings(**response)

    async def set_quota(
        self, workspace_id: str, monthly_message_quota: Optional[int]
    ) -> QuotaSettings:
        response = await self._http.request(
            "PUT",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/quota",
            body={"monthlyMessageQuota": monthly_message_quota},
        )
        return QuotaSettings(**response)


class AsyncWebhooksSubResource:
    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def set(self, url: str) -> EnterpriseWebhook:
        response = await self._http.request("PUT", "/enterprise/webhooks", body={"url": url})
        return EnterpriseWebhook(**response)

    async def get(self) -> EnterpriseWebhook:
        response = await self._http.request("GET", "/enterprise/webhooks")
        return EnterpriseWebhook(**response)

    async def delete(self) -> None:
        await self._http.request("DELETE", "/enterprise/webhooks")

    async def test(self) -> EnterpriseWebhookTestResult:
        response = await self._http.request("POST", "/enterprise/webhooks/test")
        return EnterpriseWebhookTestResult(**response)


class AsyncAnalyticsSubResource:
    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def overview(self) -> AnalyticsOverview:
        response = await self._http.request("GET", "/enterprise/analytics/overview")
        return AnalyticsOverview(**response)

    async def messages(
        self,
        period: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> MessageAnalytics:
        params: Dict[str, Any] = {}
        if period is not None:
            params["period"] = period
        if workspace_id is not None:
            params["workspaceId"] = workspace_id

        response = await self._http.request("GET", "/enterprise/analytics/messages", params=params)
        return MessageAnalytics(**response)

    async def delivery(self) -> List[DeliveryAnalyticsItem]:
        response = await self._http.request("GET", "/enterprise/analytics/delivery")
        return [DeliveryAnalyticsItem(**item) for item in response]

    async def credits(self, period: Optional[str] = None) -> CreditAnalytics:
        params: Dict[str, Any] = {}
        if period is not None:
            params["period"] = period

        response = await self._http.request("GET", "/enterprise/analytics/credits", params=params)
        return CreditAnalytics(**response)


class AsyncSettingsSubResource:
    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def get_auto_top_up(self) -> AutoTopUpSettings:
        response = await self._http.request("GET", "/enterprise/settings/auto-top-up")
        return AutoTopUpSettings(**response)

    async def update_auto_top_up(
        self,
        enabled: bool,
        threshold: int,
        amount: int,
        source_workspace_id: Optional[str] = None,
    ) -> AutoTopUpSettings:
        body: Dict[str, Any] = {
            "enabled": enabled,
            "threshold": threshold,
            "amount": amount,
        }
        if source_workspace_id is not None:
            body["sourceWorkspaceId"] = source_workspace_id

        response = await self._http.request("PUT", "/enterprise/settings/auto-top-up", body=body)
        return AutoTopUpSettings(**response)


class AsyncBillingSubResource:
    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def get_breakdown(
        self,
        period: Optional[str] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> BillingBreakdown:
        params: Dict[str, Any] = {}
        if period is not None:
            params["period"] = period
        if page is not None:
            params["page"] = str(page)
        if limit is not None:
            params["limit"] = str(limit)

        response = await self._http.request(
            "GET",
            "/enterprise/billing/workspace-breakdown",
            params=params if params else None,
        )
        return BillingBreakdown(**response)


class AsyncEnterpriseResource:
    def __init__(self, http: AsyncHttpClient):
        self._http = http
        self.workspaces = AsyncWorkspacesSubResource(http)
        self.webhooks = AsyncWebhooksSubResource(http)
        self.analytics = AsyncAnalyticsSubResource(http)
        self.settings = AsyncSettingsSubResource(http)
        self.billing = AsyncBillingSubResource(http)

    async def get_account(self) -> EnterpriseAccount:
        response = await self._http.request("GET", "/enterprise/account")
        return EnterpriseAccount(**response)

    async def provision(self, opts: Dict[str, Any]) -> Dict[str, Any]:
        body: Dict[str, Any] = {"name": opts["name"]}
        if opts.get("sourceWorkspaceId"):
            body["sourceWorkspaceId"] = opts["sourceWorkspaceId"]
        if opts.get("inheritWithNewNumber"):
            body["inheritWithNewNumber"] = True
        if opts.get("verification"):
            body["verification"] = opts["verification"]
        if opts.get("creditAmount") is not None:
            body["creditAmount"] = opts["creditAmount"]
        if opts.get("creditSourceWorkspaceId"):
            body["creditSourceWorkspaceId"] = opts["creditSourceWorkspaceId"]
        if opts.get("keyName"):
            body["keyName"] = opts["keyName"]
        if opts.get("keyType"):
            body["keyType"] = opts["keyType"]
        if opts.get("webhookUrl"):
            body["webhookUrl"] = opts["webhookUrl"]
        if opts.get("generateOptInPage") is not None:
            body["generateOptInPage"] = opts["generateOptInPage"]

        response = await self._http.request("POST", "/enterprise/workspaces/provision", body=body)
        return response
