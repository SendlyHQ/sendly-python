"""
Templates Resource - SMS Template Management
"""

from typing import Any, Dict, List, Optional

from ..types import Template, TemplateListResponse, TemplatePreview
from ..utils.http import AsyncHttpClient, HttpClient


class TemplatesResource:
    """Templates API resource for SMS template management (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def list(self) -> TemplateListResponse:
        """List all templates (presets + custom)"""
        data = self._http.request("GET", "/templates")
        return TemplateListResponse(
            templates=[self._transform_template(t) for t in data["templates"]]
        )

    def presets(self) -> TemplateListResponse:
        """List preset templates only"""
        data = self._http.request("GET", "/templates/presets")
        return TemplateListResponse(
            templates=[self._transform_template(t) for t in data["templates"]]
        )

    def get(self, template_id: str) -> Template:
        """Get a template by ID"""
        data = self._http.request("GET", f"/templates/{template_id}")
        return self._transform_template(data)

    def create(self, name: str, text: str) -> Template:
        """Create a new template"""
        data = self._http.request("POST", "/templates", json={"name": name, "text": text})
        return self._transform_template(data)

    def update(
        self,
        template_id: str,
        *,
        name: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Template:
        """Update a template"""
        body: Dict[str, Any] = {}
        if name:
            body["name"] = name
        if text:
            body["text"] = text

        data = self._http.request("PATCH", f"/templates/{template_id}", json=body)
        return self._transform_template(data)

    def publish(self, template_id: str) -> Template:
        """Publish a draft template"""
        data = self._http.request("POST", f"/templates/{template_id}/publish")
        return self._transform_template(data)

    def preview(
        self, template_id: str, variables: Optional[Dict[str, str]] = None
    ) -> TemplatePreview:
        """Preview a template with sample values"""
        body = {"variables": variables} if variables else {}
        data = self._http.request("POST", f"/templates/{template_id}/preview", json=body)
        return TemplatePreview(
            id=data["id"],
            name=data["name"],
            original_text=data["original_text"],
            preview_text=data["preview_text"],
            variables=data["variables"],
        )

    def delete(self, template_id: str) -> None:
        """Delete a template"""
        self._http.request("DELETE", f"/templates/{template_id}")

    def clone(self, template_id: str, name: Optional[str] = None) -> Template:
        """Clone a template

        Args:
            template_id: Template ID to clone
            name: Optional new name for the cloned template
        """
        body = {"name": name} if name else {}
        data = self._http.request("POST", f"/templates/{template_id}/clone", json=body)
        return self._transform_template(data)

    def _transform_template(self, data: Dict[str, Any]) -> Template:
        return Template(
            id=data["id"],
            name=data["name"],
            text=data["text"],
            variables=data["variables"],
            is_preset=data["is_preset"],
            preset_slug=data.get("preset_slug"),
            status=data["status"],
            version=data["version"],
            published_at=data.get("published_at"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


class AsyncTemplatesResource:
    """Templates API resource for SMS template management (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list(self) -> TemplateListResponse:
        """List all templates (presets + custom)"""
        data = await self._http.request("GET", "/templates")
        return TemplateListResponse(
            templates=[self._transform_template(t) for t in data["templates"]]
        )

    async def presets(self) -> TemplateListResponse:
        """List preset templates only"""
        data = await self._http.request("GET", "/templates/presets")
        return TemplateListResponse(
            templates=[self._transform_template(t) for t in data["templates"]]
        )

    async def get(self, template_id: str) -> Template:
        """Get a template by ID"""
        data = await self._http.request("GET", f"/templates/{template_id}")
        return self._transform_template(data)

    async def create(self, name: str, text: str) -> Template:
        """Create a new template"""
        data = await self._http.request("POST", "/templates", json={"name": name, "text": text})
        return self._transform_template(data)

    async def update(
        self,
        template_id: str,
        *,
        name: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Template:
        """Update a template"""
        body: Dict[str, Any] = {}
        if name:
            body["name"] = name
        if text:
            body["text"] = text

        data = await self._http.request("PATCH", f"/templates/{template_id}", json=body)
        return self._transform_template(data)

    async def publish(self, template_id: str) -> Template:
        """Publish a draft template"""
        data = await self._http.request("POST", f"/templates/{template_id}/publish")
        return self._transform_template(data)

    async def preview(
        self, template_id: str, variables: Optional[Dict[str, str]] = None
    ) -> TemplatePreview:
        """Preview a template with sample values"""
        body = {"variables": variables} if variables else {}
        data = await self._http.request("POST", f"/templates/{template_id}/preview", json=body)
        return TemplatePreview(
            id=data["id"],
            name=data["name"],
            original_text=data["original_text"],
            preview_text=data["preview_text"],
            variables=data["variables"],
        )

    async def delete(self, template_id: str) -> None:
        """Delete a template"""
        await self._http.request("DELETE", f"/templates/{template_id}")

    async def clone(self, template_id: str, name: Optional[str] = None) -> Template:
        """Clone a template"""
        body = {"name": name} if name else {}
        data = await self._http.request("POST", f"/templates/{template_id}/clone", json=body)
        return self._transform_template(data)

    def _transform_template(self, data: Dict[str, Any]) -> Template:
        return Template(
            id=data["id"],
            name=data["name"],
            text=data["text"],
            variables=data["variables"],
            is_preset=data["is_preset"],
            preset_slug=data.get("preset_slug"),
            status=data["status"],
            version=data["version"],
            published_at=data.get("published_at"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
