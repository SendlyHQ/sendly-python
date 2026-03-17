"""Sendly SDK Resources"""

from .campaigns import AsyncCampaignsResource, CampaignsResource
from .contacts import AsyncContactsResource, ContactsResource
from .conversations import AsyncConversationsResource, ConversationsResource
from .drafts import AsyncDraftsResource, DraftsResource
from .enterprise import AsyncEnterpriseResource, EnterpriseResource
from .labels import AsyncLabelsResource, LabelsResource
from .media import AsyncMediaResource, MediaResource
from .messages import AsyncMessagesResource, MessagesResource
from .templates import AsyncTemplatesResource, TemplatesResource
from .verify import AsyncVerifyResource, VerifyResource

__all__ = [
    "CampaignsResource",
    "AsyncCampaignsResource",
    "ContactsResource",
    "AsyncContactsResource",
    "ConversationsResource",
    "AsyncConversationsResource",
    "DraftsResource",
    "AsyncDraftsResource",
    "EnterpriseResource",
    "AsyncEnterpriseResource",
    "LabelsResource",
    "AsyncLabelsResource",
    "MediaResource",
    "AsyncMediaResource",
    "MessagesResource",
    "AsyncMessagesResource",
    "VerifyResource",
    "AsyncVerifyResource",
    "TemplatesResource",
    "AsyncTemplatesResource",
]
