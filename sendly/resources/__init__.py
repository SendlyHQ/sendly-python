"""Sendly SDK Resources"""

from .campaigns import AsyncCampaignsResource, CampaignsResource
from .contacts import AsyncContactsResource, ContactsResource
from .conversations import AsyncConversationsResource, ConversationsResource
from .enterprise import AsyncEnterpriseResource, EnterpriseResource
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
    "EnterpriseResource",
    "AsyncEnterpriseResource",
    "MediaResource",
    "AsyncMediaResource",
    "MessagesResource",
    "AsyncMessagesResource",
    "VerifyResource",
    "AsyncVerifyResource",
    "TemplatesResource",
    "AsyncTemplatesResource",
]
