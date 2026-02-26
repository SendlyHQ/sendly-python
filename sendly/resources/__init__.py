"""Sendly SDK Resources"""

from .campaigns import AsyncCampaignsResource, CampaignsResource
from .contacts import AsyncContactsResource, ContactsResource
from .media import AsyncMediaResource, MediaResource
from .messages import AsyncMessagesResource, MessagesResource
from .templates import AsyncTemplatesResource, TemplatesResource
from .verify import AsyncVerifyResource, VerifyResource

__all__ = [
    "CampaignsResource",
    "AsyncCampaignsResource",
    "ContactsResource",
    "AsyncContactsResource",
    "MediaResource",
    "AsyncMediaResource",
    "MessagesResource",
    "AsyncMessagesResource",
    "VerifyResource",
    "AsyncVerifyResource",
    "TemplatesResource",
    "AsyncTemplatesResource",
]
