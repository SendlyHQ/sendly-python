from typing import Any, Dict, List, Optional
from urllib.parse import quote

from ..errors import NotFoundError, RateLimitError, SendlyError
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


def _workspace_detail(response: Dict[str, Any]) -> EnterpriseWorkspaceDetail:
    data = dict(response)
    verification = data.get("verification")
    if isinstance(verification, dict):
        data.setdefault("verificationStatus", verification.get("status"))
        data.setdefault("verificationType", verification.get("type"))
        data.setdefault("tollFreeNumber", verification.get("tollFreeNumber"))
        data.setdefault("businessName", verification.get("businessName"))
    if "creditBalance" not in data and isinstance(data.get("credits"), (int, float)):
        data["creditBalance"] = data["credits"]
    return EnterpriseWorkspaceDetail(**data)


def _submit_body(data: Optional[Dict[str, Any]], kwargs: Dict[str, Any]) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if data:
        body.update(data)
    body.update(kwargs)
    return {k: v for k, v in body.items() if v is not None}


def _inherit_body(source_workspace_id: str, purchase_new_number: bool) -> Dict[str, Any]:
    body: Dict[str, Any] = {"source_workspace_id": source_workspace_id}
    if purchase_new_number:
        body["purchaseNewNumber"] = True
    return body


def _set_webhook(response: Dict[str, Any]) -> EnterpriseWebhook:
    if response.get("url") is None:
        raise NotFoundError("No webhook is set", status_code=200)
    return EnterpriseWebhook(**response)


def _webhook_body(
    url: str, events: Optional[List[str]], workspaces: Optional[List[str]]
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"url": url}
    if events is not None:
        body["events"] = events
    if workspaces is not None:
        body["workspaces"] = workspaces
    return body



def _document_upload_error(response: Any) -> SendlyError:
    resp_data = (
        response.json()
        if "application/json" in response.headers.get("content-type", "")
        else {}
    )
    if isinstance(resp_data, dict):
        return SendlyError.from_response(response.status_code, resp_data)
    return SendlyError(
        message=str(resp_data) or f"HTTP {response.status_code}",
        code="internal_error",
        status_code=response.status_code,
    )

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
        return _workspace_detail(response)

    def delete(self, workspace_id: str) -> None:
        self._http.request("DELETE", f"/enterprise/workspaces/{quote(workspace_id, safe='')}")

    def submit_verification(
        self,
        workspace_id: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Submit (or resubmit) a verification for an enterprise workspace.

        Partial-update friendly (May 2026): for resubmit on an existing
        workspace, you only need to send the fields you want to change —
        everything else is preserved from the existing record. So if you
        rejected with a missing-field error, just resend with the missing
        bits and you're done.

        Accepts either a `data` dict or kwargs:

            client.enterprise.workspaces.submit_verification(
                workspace_id,
                businessName="Acme LLC",
                website="https://acme.com",
                address={"street": "...", "city": "...", "state": "California",
                         "zip": "90001", "country": "US"},
                contact={"firstName": "...", "lastName": "...",
                         "email": "...", "phone": "+15551234567"},
                useCase="Insurance Services",
                useCaseSummary="...",
                sampleMessages="...",
                optInWorkflow="...",
                entityType="SOLE_PROPRIETOR",  # leave brn fields null for sole props
            )

        For partial-update resubmits, send only what changed:

            client.enterprise.workspaces.submit_verification(
                workspace_id, contact={"email": "new@email.com"}
            )

        All other fields (businessName, website, address, etc.) carry over
        from the existing verification record. Hosted page URLs (/biz/,
        /opt-in/, /legal/) generated during provision are auto-preserved —
        you do not need to re-fetch them.
        """
        response = self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/verification/submit",
            body=_submit_body(data, kwargs),
        )
        return response

    def resubmit_verification(
        self,
        workspace_id: str,
        **partial_updates: Any,
    ) -> Dict[str, Any]:
        """
        Convenience alias for resubmits. Identical to submit_verification
        but reads as a more obvious name when you only want to update a
        few fields after a rejection.

            client.enterprise.workspaces.resubmit_verification(
                workspace_id, contact={"email": "new@email.com"}
            )
        """
        return self.submit_verification(workspace_id, **partial_updates)

    def inherit_verification(
        self,
        workspace_id: str,
        source_workspace_id: str,
        *,
        purchase_new_number: bool = False,
    ) -> Dict[str, Any]:
        """
        Give a workspace the verification of another workspace you own.

        By default the workspace shares the source's verification and number.
        With ``purchase_new_number=True`` it gets a copy of the business
        details and orders its own toll-free number, which is submitted for
        verification when the copied details are complete.

        Returns:
            Dict with 'verificationId', 'status', 'type', 'tollFreeNumber' and
            'inheritedFrom', plus 'newNumber' when a new number was ordered
        """
        response = self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/verification/inherit",
            body=_inherit_body(source_workspace_id, purchase_new_number),
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

    def set(
        self,
        url: str,
        events: Optional[List[str]] = None,
        workspaces: Optional[List[str]] = None,
    ) -> EnterpriseWebhook:
        """
        Set the webhook for events across your workspaces.

        Args:
            url: HTTPS endpoint URL
            events: Event types to deliver (default: every event)
            workspaces: Workspace IDs to deliver events for (default: every workspace)

        Returns:
            The webhook. The first call returns its ``signing_secret``, shown
            only once
        """
        response = self._http.request(
            "POST", "/enterprise/webhooks", body=_webhook_body(url, events, workspaces)
        )
        return EnterpriseWebhook(**response)

    def get(self) -> EnterpriseWebhook:
        """
        Get the webhook set for events across your workspaces.

        Returns:
            The webhook's URL, events and workspaces. The signing secret is
            returned only by the first :meth:`set`

        Raises:
            NotFoundError: If no webhook is set
        """
        response = self._http.request("GET", "/enterprise/webhooks")
        return _set_webhook(response)

    def delete(self) -> None:
        self._http.request("DELETE", "/enterprise/webhooks")

    def test(self) -> EnterpriseWebhookTestResult:
        response = self._http.request("POST", "/enterprise/webhooks/test")
        return EnterpriseWebhookTestResult(**response)

    def rotate_secret(self) -> Dict[str, Any]:
        response = self._http.request("POST", "/enterprise/webhooks/rotate-secret")
        return response


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


class CreditsSubResource:
    def __init__(self, http: HttpClient):
        self._http = http

    def get(self) -> Dict[str, Any]:
        response = self._http.request("GET", "/enterprise/credits")
        return response

    def deposit(self, amount: int, description: Optional[str] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {"amount": amount}
        if description is not None:
            body["description"] = description
        response = self._http.request("POST", "/enterprise/credits/deposit", body=body)
        return response


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
        self.credits = CreditsSubResource(http)

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
        if opts.get("generateBusinessPage") is not None:
            body["generateBusinessPage"] = opts["generateBusinessPage"]

        response = self._http.request("POST", "/enterprise/workspaces/provision", body=body)
        return response

    def generate_business_page(
        self,
        business_name: str,
        use_case: Optional[str] = None,
        use_case_summary: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        business_address: Optional[str] = None,
        social_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"businessName": business_name}
        if use_case is not None:
            body["useCase"] = use_case
        if use_case_summary is not None:
            body["useCaseSummary"] = use_case_summary
        if contact_email is not None:
            body["contactEmail"] = contact_email
        if contact_phone is not None:
            body["contactPhone"] = contact_phone
        if business_address is not None:
            body["businessAddress"] = business_address
        if social_url is not None:
            body["socialUrl"] = social_url

        response = self._http.request(
            "POST", "/enterprise/business-page/generate", body=body
        )
        return response

    def upload_verification_document(
        self,
        file_path: str,
        workspace_id: Optional[str] = None,
        verification_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        import os
        import mimetypes

        if not file_path or not os.path.exists(file_path):
            raise ValueError("A valid file path is required")

        filename = os.path.basename(file_path)
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

        with open(file_path, "rb") as f:
            files = {"file": (filename, f.read(), content_type)}

        data: Dict[str, str] = {}
        if workspace_id is not None:
            data["workspaceId"] = workspace_id
        if verification_id is not None:
            data["verificationId"] = verification_id

        headers = {
            "Authorization": f"Bearer {self._http.api_key}",
            "Accept": "application/json",
        }
        if self._http.organization_id:
            headers["X-Organization-Id"] = self._http.organization_id
        headers["Idempotency-Key"] = self._http._generate_idempotency_key()

        url = f"{self._http.base_url}/enterprise/verification-document/upload"
        import time

        import httpx
        with httpx.Client(timeout=self._http.timeout) as client:
            for attempt in range(self._http.max_retries + 1):
                response = client.post(url, files=files, data=data, headers=headers)
                if response.is_success:
                    return response.json()
                error = _document_upload_error(response)
                if (
                    isinstance(error, RateLimitError)
                    and error.code == "too_many_concurrent_verifications"
                    and error.retry_after <= 60
                    and attempt < self._http.max_retries
                ):
                    time.sleep(error.retry_after)
                    continue
                raise error
        raise SendlyError("Request failed after retries")


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
        return _workspace_detail(response)

    async def delete(self, workspace_id: str) -> None:
        await self._http.request("DELETE", f"/enterprise/workspaces/{quote(workspace_id, safe='')}")

    async def submit_verification(
        self,
        workspace_id: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Submit (or resubmit) a verification for an enterprise workspace (async).

        Takes a ``data`` dict or keyword arguments with the API's camelCase
        keys (``businessName``, ``website``, ``address``, ``contact``,
        ``useCase``, ...) and drops None values; see
        :meth:`WorkspacesSubResource.submit_verification`.
        """
        response = await self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/verification/submit",
            body=_submit_body(data, kwargs),
        )
        return response

    async def resubmit_verification(
        self,
        workspace_id: str,
        **partial_updates: Any,
    ) -> Dict[str, Any]:
        """
        Convenience alias for resubmits (async): send only the fields that
        changed; the rest carry over from the existing verification.
        """
        return await self.submit_verification(workspace_id, **partial_updates)

    async def inherit_verification(
        self,
        workspace_id: str,
        source_workspace_id: str,
        *,
        purchase_new_number: bool = False,
    ) -> Dict[str, Any]:
        """
        Give a workspace the verification of another workspace you own
        (async). Pass ``purchase_new_number=True`` for its own toll-free
        number; see :meth:`WorkspacesSubResource.inherit_verification`.
        """
        response = await self._http.request(
            "POST",
            f"/enterprise/workspaces/{quote(workspace_id, safe='')}/verification/inherit",
            body=_inherit_body(source_workspace_id, purchase_new_number),
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

    async def set(
        self,
        url: str,
        events: Optional[List[str]] = None,
        workspaces: Optional[List[str]] = None,
    ) -> EnterpriseWebhook:
        """Set the webhook for events across your workspaces (async).

        See :meth:`WebhooksSubResource.set`; the first call returns the
        ``signing_secret``, shown only once.
        """
        response = await self._http.request(
            "POST", "/enterprise/webhooks", body=_webhook_body(url, events, workspaces)
        )
        return EnterpriseWebhook(**response)

    async def get(self) -> EnterpriseWebhook:
        """Get the webhook set for events across your workspaces (async).

        Raises NotFoundError if no webhook is set; see
        :meth:`WebhooksSubResource.get`.
        """
        response = await self._http.request("GET", "/enterprise/webhooks")
        return _set_webhook(response)

    async def delete(self) -> None:
        await self._http.request("DELETE", "/enterprise/webhooks")

    async def test(self) -> EnterpriseWebhookTestResult:
        response = await self._http.request("POST", "/enterprise/webhooks/test")
        return EnterpriseWebhookTestResult(**response)

    async def rotate_secret(self) -> Dict[str, Any]:
        response = await self._http.request("POST", "/enterprise/webhooks/rotate-secret")
        return response


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


class AsyncCreditsSubResource:
    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def get(self) -> Dict[str, Any]:
        response = await self._http.request("GET", "/enterprise/credits")
        return response

    async def deposit(self, amount: int, description: Optional[str] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {"amount": amount}
        if description is not None:
            body["description"] = description
        response = await self._http.request("POST", "/enterprise/credits/deposit", body=body)
        return response


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
        self.credits = AsyncCreditsSubResource(http)

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
        if opts.get("generateBusinessPage") is not None:
            body["generateBusinessPage"] = opts["generateBusinessPage"]

        response = await self._http.request("POST", "/enterprise/workspaces/provision", body=body)
        return response

    async def generate_business_page(
        self,
        business_name: str,
        use_case: Optional[str] = None,
        use_case_summary: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        business_address: Optional[str] = None,
        social_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"businessName": business_name}
        if use_case is not None:
            body["useCase"] = use_case
        if use_case_summary is not None:
            body["useCaseSummary"] = use_case_summary
        if contact_email is not None:
            body["contactEmail"] = contact_email
        if contact_phone is not None:
            body["contactPhone"] = contact_phone
        if business_address is not None:
            body["businessAddress"] = business_address
        if social_url is not None:
            body["socialUrl"] = social_url

        response = await self._http.request(
            "POST", "/enterprise/business-page/generate", body=body
        )
        return response

    async def upload_verification_document(
        self,
        file_path: str,
        workspace_id: Optional[str] = None,
        verification_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        import os
        import mimetypes

        if not file_path or not os.path.exists(file_path):
            raise ValueError("A valid file path is required")

        filename = os.path.basename(file_path)
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

        with open(file_path, "rb") as f:
            files = {"file": (filename, f.read(), content_type)}

        data: Dict[str, str] = {}
        if workspace_id is not None:
            data["workspaceId"] = workspace_id
        if verification_id is not None:
            data["verificationId"] = verification_id

        headers = {
            "Authorization": f"Bearer {self._http.api_key}",
            "Accept": "application/json",
        }
        if self._http.organization_id:
            headers["X-Organization-Id"] = self._http.organization_id
        headers["Idempotency-Key"] = self._http._generate_idempotency_key()

        url = f"{self._http.base_url}/enterprise/verification-document/upload"
        import asyncio

        import httpx
        async with httpx.AsyncClient(timeout=self._http.timeout) as client:
            for attempt in range(self._http.max_retries + 1):
                response = await client.post(url, files=files, data=data, headers=headers)
                if response.is_success:
                    return response.json()
                error = _document_upload_error(response)
                if (
                    isinstance(error, RateLimitError)
                    and error.code == "too_many_concurrent_verifications"
                    and error.retry_after <= 60
                    and attempt < self._http.max_retries
                ):
                    await asyncio.sleep(error.retry_after)
                    continue
                raise error
        raise SendlyError("Request failed after retries")
