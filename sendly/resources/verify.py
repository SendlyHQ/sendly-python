"""
Verify Resource - OTP Verification API
"""

from typing import Any, Dict, List, Optional

from ..types import (
    Verification,
    VerificationListResponse,
    SendVerificationResponse,
    CheckVerificationResponse,
)
from ..utils.http import HttpClient, AsyncHttpClient


class VerifyResource:
    """Verify API resource for OTP verification (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

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

    def check(self, verification_id: str, code: str) -> CheckVerificationResponse:
        """Check/verify an OTP code"""
        data = self._http.request(
            "POST", f"/verify/{verification_id}/check", json={"code": code}
        )
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
