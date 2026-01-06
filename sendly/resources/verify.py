"""
Verify Resource - OTP Verification API
"""

from typing import Any, Dict, List, Optional

from ..types import (
    CheckVerificationResponse,
    SendVerificationResponse,
    Verification,
    VerificationListResponse,
    VerifySession,
    ValidateSessionResponse,
)
from ..utils.http import AsyncHttpClient, HttpClient


class SessionsResource:
    """Sessions sub-resource for hosted verification flow (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def create(
        self,
        success_url: str,
        *,
        cancel_url: Optional[str] = None,
        brand_name: Optional[str] = None,
        brand_color: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VerifySession:
        """Create a hosted verification session"""
        body: Dict[str, Any] = {"success_url": success_url}
        if cancel_url:
            body["cancel_url"] = cancel_url
        if brand_name:
            body["brand_name"] = brand_name
        if brand_color:
            body["brand_color"] = brand_color
        if metadata:
            body["metadata"] = metadata

        data = self._http.request("POST", "/verify/sessions", json=body)
        return VerifySession(
            id=data["id"],
            url=data["url"],
            status=data["status"],
            success_url=data["success_url"],
            cancel_url=data.get("cancel_url"),
            brand_name=data.get("brand_name"),
            brand_color=data.get("brand_color"),
            phone=data.get("phone"),
            verification_id=data.get("verification_id"),
            token=data.get("token"),
            metadata=data.get("metadata"),
            expires_at=data["expires_at"],
            created_at=data["created_at"],
        )

    def validate(self, token: str) -> ValidateSessionResponse:
        """Validate a session token after user completes verification"""
        data = self._http.request("POST", "/verify/sessions/validate", json={"token": token})
        return ValidateSessionResponse(
            valid=data["valid"],
            session_id=data.get("session_id"),
            phone=data.get("phone"),
            verified_at=data.get("verified_at"),
            metadata=data.get("metadata"),
        )


class AsyncSessionsResource:
    """Sessions sub-resource for hosted verification flow (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def create(
        self,
        success_url: str,
        *,
        cancel_url: Optional[str] = None,
        brand_name: Optional[str] = None,
        brand_color: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VerifySession:
        """Create a hosted verification session"""
        body: Dict[str, Any] = {"success_url": success_url}
        if cancel_url:
            body["cancel_url"] = cancel_url
        if brand_name:
            body["brand_name"] = brand_name
        if brand_color:
            body["brand_color"] = brand_color
        if metadata:
            body["metadata"] = metadata

        data = await self._http.request("POST", "/verify/sessions", json=body)
        return VerifySession(
            id=data["id"],
            url=data["url"],
            status=data["status"],
            success_url=data["success_url"],
            cancel_url=data.get("cancel_url"),
            brand_name=data.get("brand_name"),
            brand_color=data.get("brand_color"),
            phone=data.get("phone"),
            verification_id=data.get("verification_id"),
            token=data.get("token"),
            metadata=data.get("metadata"),
            expires_at=data["expires_at"],
            created_at=data["created_at"],
        )

    async def validate(self, token: str) -> ValidateSessionResponse:
        """Validate a session token after user completes verification"""
        data = await self._http.request("POST", "/verify/sessions/validate", json={"token": token})
        return ValidateSessionResponse(
            valid=data["valid"],
            session_id=data.get("session_id"),
            phone=data.get("phone"),
            verified_at=data.get("verified_at"),
            metadata=data.get("metadata"),
        )


class VerifyResource:
    """Verify API resource for OTP verification (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http
        self.sessions = SessionsResource(http)

    def send(
        self,
        to: str,
        *,
        template_id: Optional[str] = None,
        profile_id: Optional[str] = None,
        app_name: Optional[str] = None,
        timeout_secs: Optional[int] = None,
        code_length: Optional[int] = None,
    ) -> SendVerificationResponse:
        """Send an OTP verification code"""
        body: Dict[str, Any] = {"to": to}
        if template_id:
            body["template_id"] = template_id
        if profile_id:
            body["profile_id"] = profile_id
        if app_name:
            body["app_name"] = app_name
        if timeout_secs:
            body["timeout_secs"] = timeout_secs
        if code_length:
            body["code_length"] = code_length

        data = self._http.request("POST", "/verify", json=body)
        return SendVerificationResponse(
            id=data["id"],
            status=data["status"],
            phone=data["phone"],
            expires_at=data["expires_at"],
            sandbox=data["sandbox"],
            sandbox_code=data.get("sandbox_code"),
            message=data.get("message"),
        )

    def resend(self, verification_id: str) -> SendVerificationResponse:
        """Resend an OTP verification code"""
        data = self._http.request("POST", f"/verify/{verification_id}/resend")
        return SendVerificationResponse(
            id=data["id"],
            status=data["status"],
            phone=data["phone"],
            expires_at=data["expires_at"],
            sandbox=data["sandbox"],
            sandbox_code=data.get("sandbox_code"),
            message=data.get("message"),
        )

    def check(self, verification_id: str, code: str) -> CheckVerificationResponse:
        """Check/verify an OTP code"""
        data = self._http.request("POST", f"/verify/{verification_id}/check", json={"code": code})
        return CheckVerificationResponse(
            id=data["id"],
            status=data["status"],
            phone=data["phone"],
            verified_at=data.get("verified_at"),
            remaining_attempts=data.get("remaining_attempts"),
        )

    def get(self, verification_id: str) -> Verification:
        """Get a verification by ID"""
        data = self._http.request("GET", f"/verify/{verification_id}")
        return Verification(
            id=data["id"],
            status=data["status"],
            phone=data["phone"],
            delivery_status=data["delivery_status"],
            attempts=data["attempts"],
            max_attempts=data["max_attempts"],
            expires_at=data["expires_at"],
            verified_at=data.get("verified_at"),
            created_at=data["created_at"],
            sandbox=data["sandbox"],
            app_name=data.get("app_name"),
            template_id=data.get("template_id"),
            profile_id=data.get("profile_id"),
        )

    def list(
        self,
        *,
        limit: Optional[int] = None,
        status: Optional[str] = None,
    ) -> VerificationListResponse:
        """List recent verifications"""
        params: Dict[str, Any] = {}
        if limit:
            params["limit"] = limit
        if status:
            params["status"] = status

        data = self._http.request("GET", "/verify", params=params)
        return VerificationListResponse(
            verifications=[
                Verification(
                    id=v["id"],
                    status=v["status"],
                    phone=v["phone"],
                    delivery_status=v["delivery_status"],
                    attempts=v["attempts"],
                    max_attempts=v["max_attempts"],
                    expires_at=v["expires_at"],
                    verified_at=v.get("verified_at"),
                    created_at=v["created_at"],
                    sandbox=v["sandbox"],
                    app_name=v.get("app_name"),
                    template_id=v.get("template_id"),
                    profile_id=v.get("profile_id"),
                )
                for v in data["verifications"]
            ],
            pagination=data["pagination"],
        )


class AsyncVerifyResource:
    """Verify API resource for OTP verification (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http
        self.sessions = AsyncSessionsResource(http)

    async def send(
        self,
        to: str,
        *,
        template_id: Optional[str] = None,
        profile_id: Optional[str] = None,
        app_name: Optional[str] = None,
        timeout_secs: Optional[int] = None,
        code_length: Optional[int] = None,
    ) -> SendVerificationResponse:
        """Send an OTP verification code"""
        body: Dict[str, Any] = {"to": to}
        if template_id:
            body["template_id"] = template_id
        if profile_id:
            body["profile_id"] = profile_id
        if app_name:
            body["app_name"] = app_name
        if timeout_secs:
            body["timeout_secs"] = timeout_secs
        if code_length:
            body["code_length"] = code_length

        data = await self._http.request("POST", "/verify", json=body)
        return SendVerificationResponse(
            id=data["id"],
            status=data["status"],
            phone=data["phone"],
            expires_at=data["expires_at"],
            sandbox=data["sandbox"],
            sandbox_code=data.get("sandbox_code"),
            message=data.get("message"),
        )

    async def resend(self, verification_id: str) -> SendVerificationResponse:
        """Resend an OTP verification code"""
        data = await self._http.request("POST", f"/verify/{verification_id}/resend")
        return SendVerificationResponse(
            id=data["id"],
            status=data["status"],
            phone=data["phone"],
            expires_at=data["expires_at"],
            sandbox=data["sandbox"],
            sandbox_code=data.get("sandbox_code"),
            message=data.get("message"),
        )

    async def check(self, verification_id: str, code: str) -> CheckVerificationResponse:
        """Check/verify an OTP code"""
        data = await self._http.request(
            "POST", f"/verify/{verification_id}/check", json={"code": code}
        )
        return CheckVerificationResponse(
            id=data["id"],
            status=data["status"],
            phone=data["phone"],
            verified_at=data.get("verified_at"),
            remaining_attempts=data.get("remaining_attempts"),
        )

    async def get(self, verification_id: str) -> Verification:
        """Get a verification by ID"""
        data = await self._http.request("GET", f"/verify/{verification_id}")
        return Verification(
            id=data["id"],
            status=data["status"],
            phone=data["phone"],
            delivery_status=data["delivery_status"],
            attempts=data["attempts"],
            max_attempts=data["max_attempts"],
            expires_at=data["expires_at"],
            verified_at=data.get("verified_at"),
            created_at=data["created_at"],
            sandbox=data["sandbox"],
            app_name=data.get("app_name"),
            template_id=data.get("template_id"),
            profile_id=data.get("profile_id"),
        )

    async def list(
        self,
        *,
        limit: Optional[int] = None,
        status: Optional[str] = None,
    ) -> VerificationListResponse:
        """List recent verifications"""
        params: Dict[str, Any] = {}
        if limit:
            params["limit"] = limit
        if status:
            params["status"] = status

        data = await self._http.request("GET", "/verify", params=params)
        return VerificationListResponse(
            verifications=[
                Verification(
                    id=v["id"],
                    status=v["status"],
                    phone=v["phone"],
                    delivery_status=v["delivery_status"],
                    attempts=v["attempts"],
                    max_attempts=v["max_attempts"],
                    expires_at=v["expires_at"],
                    verified_at=v.get("verified_at"),
                    created_at=v["created_at"],
                    sandbox=v["sandbox"],
                    app_name=v.get("app_name"),
                    template_id=v.get("template_id"),
                    profile_id=v.get("profile_id"),
                )
                for v in data["verifications"]
            ],
            pagination=data["pagination"],
        )
