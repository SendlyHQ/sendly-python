"""
Contacts Resource - Contact & List Management
"""

from typing import Any, Dict, List, Optional

from ..types import (
    Contact,
    ContactList,
    ContactListResponse,
    ContactListsResponse,
    ImportContactItem,
    ImportContactsResponse,
)
from ..utils.http import AsyncHttpClient, HttpClient


class ContactListsResource:
    """Contact Lists sub-resource (sync)"""

    def __init__(self, http: HttpClient):
        self._http = http

    def list(self) -> ContactListsResponse:
        """List all contact lists"""
        data = self._http.request("GET", "/contact-lists")
        return ContactListsResponse(lists=[self._transform_list(lst) for lst in data["lists"]])

    def get(
        self,
        list_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> ContactList:
        """Get a contact list by ID with optional member pagination"""
        params: Dict[str, Any] = {}
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        data = self._http.request(
            "GET", f"/contact-lists/{list_id}", params=params if params else None
        )
        return self._transform_list(data)

    def create(self, name: str, description: Optional[str] = None) -> ContactList:
        """Create a new contact list"""
        body: Dict[str, Any] = {"name": name}
        if description:
            body["description"] = description

        data = self._http.request("POST", "/contact-lists", json=body)
        return self._transform_list(data)

    def update(
        self,
        list_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ContactList:
        """Update a contact list"""
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description

        data = self._http.request("PATCH", f"/contact-lists/{list_id}", json=body)
        return self._transform_list(data)

    def delete(self, list_id: str) -> None:
        """Delete a contact list (does not delete the contacts)"""
        self._http.request("DELETE", f"/contact-lists/{list_id}")

    def add_contacts(self, list_id: str, contact_ids: List[str]) -> Dict[str, int]:
        """Add contacts to a list

        Returns:
            Dict with 'added_count' key
        """
        data = self._http.request(
            "POST",
            f"/contact-lists/{list_id}/contacts",
            json={"contact_ids": contact_ids},
        )
        return {"added_count": data["added_count"]}

    def remove_contact(self, list_id: str, contact_id: str) -> None:
        """Remove a contact from a list"""
        self._http.request("DELETE", f"/contact-lists/{list_id}/contacts/{contact_id}")

    def _transform_list(self, data: Dict[str, Any]) -> ContactList:
        contacts = None
        if "contacts" in data and data["contacts"]:
            contacts = [
                {
                    "id": c["id"],
                    "phone_number": c["phone_number"],
                    "name": c.get("name"),
                    "email": c.get("email"),
                }
                for c in data["contacts"]
            ]

        return ContactList(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            contact_count=data.get("contact_count", 0),
            created_at=data["created_at"],
            updated_at=data.get("updated_at"),
            contacts=contacts,
            contacts_total=data.get("contacts_total"),
        )


class ContactsResource:
    """Contacts API resource (sync)

    Example:
        >>> contact = client.contacts.create(
        ...     phone_number='+15551234567',
        ...     name='John Doe'
        ... )
        >>> lst = client.contacts.lists.create(name='Newsletter')
        >>> client.contacts.lists.add_contacts(lst.id, [contact.id])
    """

    def __init__(self, http: HttpClient):
        self._http = http
        self.lists = ContactListsResource(http)

    def list(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        list_id: Optional[str] = None,
    ) -> ContactListResponse:
        """List contacts with optional filtering

        Args:
            limit: Max contacts to return (default 50, max 100)
            offset: Pagination offset
            search: Search query (name, phone, email)
            list_id: Filter by contact list ID
        """
        params: Dict[str, Any] = {}
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        if search:
            params["search"] = search
        if list_id:
            params["list_id"] = list_id

        data = self._http.request("GET", "/contacts", params=params if params else None)
        return ContactListResponse(
            contacts=[self._transform_contact(c) for c in data["contacts"]],
            total=data["total"],
            limit=data["limit"],
            offset=data["offset"],
        )

    def get(self, contact_id: str) -> Contact:
        """Get a contact by ID"""
        data = self._http.request("GET", f"/contacts/{contact_id}")
        return self._transform_contact(data)

    def create(
        self,
        phone_number: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Contact:
        """Create a new contact

        Args:
            phone_number: E.164 format (e.g., +15551234567)
            name: Contact name
            email: Contact email
            metadata: Custom key-value data
        """
        body: Dict[str, Any] = {"phone_number": phone_number}
        if name:
            body["name"] = name
        if email:
            body["email"] = email
        if metadata:
            body["metadata"] = metadata

        data = self._http.request("POST", "/contacts", json=body)
        return self._transform_contact(data)

    def update(
        self,
        contact_id: str,
        *,
        name: Optional[str] = None,
        email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Contact:
        """Update a contact"""
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if email is not None:
            body["email"] = email
        if metadata is not None:
            body["metadata"] = metadata

        data = self._http.request("PATCH", f"/contacts/{contact_id}", json=body)
        return self._transform_contact(data)

    def delete(self, contact_id: str) -> None:
        """Delete a contact"""
        self._http.request("DELETE", f"/contacts/{contact_id}")

    def import_contacts(
        self,
        contacts: List[ImportContactItem],
        *,
        list_id: Optional[str] = None,
        opted_in_at: Optional[str] = None,
    ) -> ImportContactsResponse:
        """Bulk import contacts

        Args:
            contacts: List of ImportContactItem objects
            list_id: Optional list ID to add imported contacts to
            opted_in_at: Batch consent date (ISO 8601)
        """
        body: Dict[str, Any] = {
            "contacts": [c.model_dump(exclude_none=True) for c in contacts],
        }
        if list_id:
            body["listId"] = list_id
        if opted_in_at:
            body["optedInAt"] = opted_in_at

        data = self._http.request("POST", "/contacts/import", json=body)
        return ImportContactsResponse(
            imported=data["imported"],
            skipped_duplicates=data["skippedDuplicates"],
            errors=data.get("errors", []),
            total_errors=data.get("totalErrors", 0),
        )

    def _transform_contact(self, data: Dict[str, Any]) -> Contact:
        lists = None
        if "lists" in data and data["lists"]:
            lists = [{"id": lst["id"], "name": lst["name"]} for lst in data["lists"]]

        return Contact(
            id=data["id"],
            phone_number=data["phone_number"],
            name=data.get("name"),
            email=data.get("email"),
            metadata=data.get("metadata"),
            opted_out=data.get("opted_out", False),
            created_at=data["created_at"],
            updated_at=data.get("updated_at"),
            lists=lists,
        )


class AsyncContactListsResource:
    """Contact Lists sub-resource (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http

    async def list(self) -> ContactListsResponse:
        """List all contact lists"""
        data = await self._http.request("GET", "/contact-lists")
        return ContactListsResponse(lists=[self._transform_list(lst) for lst in data["lists"]])

    async def get(
        self,
        list_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> ContactList:
        """Get a contact list by ID with optional member pagination"""
        params: Dict[str, Any] = {}
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        data = await self._http.request(
            "GET", f"/contact-lists/{list_id}", params=params if params else None
        )
        return self._transform_list(data)

    async def create(self, name: str, description: Optional[str] = None) -> ContactList:
        """Create a new contact list"""
        body: Dict[str, Any] = {"name": name}
        if description:
            body["description"] = description

        data = await self._http.request("POST", "/contact-lists", json=body)
        return self._transform_list(data)

    async def update(
        self,
        list_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ContactList:
        """Update a contact list"""
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description

        data = await self._http.request("PATCH", f"/contact-lists/{list_id}", json=body)
        return self._transform_list(data)

    async def delete(self, list_id: str) -> None:
        """Delete a contact list (does not delete the contacts)"""
        await self._http.request("DELETE", f"/contact-lists/{list_id}")

    async def add_contacts(self, list_id: str, contact_ids: List[str]) -> Dict[str, int]:
        """Add contacts to a list"""
        data = await self._http.request(
            "POST",
            f"/contact-lists/{list_id}/contacts",
            json={"contact_ids": contact_ids},
        )
        return {"added_count": data["added_count"]}

    async def remove_contact(self, list_id: str, contact_id: str) -> None:
        """Remove a contact from a list"""
        await self._http.request("DELETE", f"/contact-lists/{list_id}/contacts/{contact_id}")

    def _transform_list(self, data: Dict[str, Any]) -> ContactList:
        contacts = None
        if "contacts" in data and data["contacts"]:
            contacts = [
                {
                    "id": c["id"],
                    "phone_number": c["phone_number"],
                    "name": c.get("name"),
                    "email": c.get("email"),
                }
                for c in data["contacts"]
            ]

        return ContactList(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            contact_count=data.get("contact_count", 0),
            created_at=data["created_at"],
            updated_at=data.get("updated_at"),
            contacts=contacts,
            contacts_total=data.get("contacts_total"),
        )


class AsyncContactsResource:
    """Contacts API resource (async)"""

    def __init__(self, http: AsyncHttpClient):
        self._http = http
        self.lists = AsyncContactListsResource(http)

    async def list(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        list_id: Optional[str] = None,
    ) -> ContactListResponse:
        """List contacts with optional filtering"""
        params: Dict[str, Any] = {}
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        if search:
            params["search"] = search
        if list_id:
            params["list_id"] = list_id

        data = await self._http.request("GET", "/contacts", params=params if params else None)
        return ContactListResponse(
            contacts=[self._transform_contact(c) for c in data["contacts"]],
            total=data["total"],
            limit=data["limit"],
            offset=data["offset"],
        )

    async def get(self, contact_id: str) -> Contact:
        """Get a contact by ID"""
        data = await self._http.request("GET", f"/contacts/{contact_id}")
        return self._transform_contact(data)

    async def create(
        self,
        phone_number: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Contact:
        """Create a new contact"""
        body: Dict[str, Any] = {"phone_number": phone_number}
        if name:
            body["name"] = name
        if email:
            body["email"] = email
        if metadata:
            body["metadata"] = metadata

        data = await self._http.request("POST", "/contacts", json=body)
        return self._transform_contact(data)

    async def update(
        self,
        contact_id: str,
        *,
        name: Optional[str] = None,
        email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Contact:
        """Update a contact"""
        body: Dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if email is not None:
            body["email"] = email
        if metadata is not None:
            body["metadata"] = metadata

        data = await self._http.request("PATCH", f"/contacts/{contact_id}", json=body)
        return self._transform_contact(data)

    async def delete(self, contact_id: str) -> None:
        """Delete a contact"""
        await self._http.request("DELETE", f"/contacts/{contact_id}")

    async def import_contacts(
        self,
        contacts: List[ImportContactItem],
        *,
        list_id: Optional[str] = None,
        opted_in_at: Optional[str] = None,
    ) -> ImportContactsResponse:
        """Bulk import contacts

        Args:
            contacts: List of ImportContactItem objects
            list_id: Optional list ID to add imported contacts to
            opted_in_at: Batch consent date (ISO 8601)
        """
        body: Dict[str, Any] = {
            "contacts": [c.model_dump(exclude_none=True) for c in contacts],
        }
        if list_id:
            body["listId"] = list_id
        if opted_in_at:
            body["optedInAt"] = opted_in_at

        data = await self._http.request("POST", "/contacts/import", json=body)
        return ImportContactsResponse(
            imported=data["imported"],
            skipped_duplicates=data["skippedDuplicates"],
            errors=data.get("errors", []),
            total_errors=data.get("totalErrors", 0),
        )

    def _transform_contact(self, data: Dict[str, Any]) -> Contact:
        lists = None
        if "lists" in data and data["lists"]:
            lists = [{"id": lst["id"], "name": lst["name"]} for lst in data["lists"]]

        return Contact(
            id=data["id"],
            phone_number=data["phone_number"],
            name=data.get("name"),
            email=data.get("email"),
            metadata=data.get("metadata"),
            opted_out=data.get("opted_out", False),
            created_at=data["created_at"],
            updated_at=data.get("updated_at"),
            lists=lists,
        )
