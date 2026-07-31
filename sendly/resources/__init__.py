"""Sendly SDK Resources"""

from .campaigns import AsyncCampaignsResource, CampaignsResource
from .contacts import AsyncContactsResource, ContactsResource
from .conversations import AsyncConversationsResource, ConversationsResource
from .drafts import AsyncDraftsResource, DraftsResource
from .enterprise import AsyncEnterpriseResource, EnterpriseResource
from .labels import AsyncLabelsResource, LabelsResource
from .links import AsyncLinksResource, LinksResource
from .media import AsyncMediaResource, MediaResource
from .messages import AsyncMessagesResource, MessagesResource
from .numbers import AsyncNumbersResource, NumbersResource
from .rules import AsyncRulesResource, RulesResource
from .templates import AsyncTemplatesResource, TemplatesResource
from .tendlc import AsyncTenDlcResource, TenDlcResource
from .verify import AsyncVerifyResource, VerifyResource
from .whatsapp import AsyncWhatsAppResource, WhatsAppResource

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
    "LinksResource",
    "AsyncLinksResource",
    "MediaResource",
    "AsyncMediaResource",
    "MessagesResource",
    "AsyncMessagesResource",
    "NumbersResource",
    "AsyncNumbersResource",
    "VerifyResource",
    "AsyncVerifyResource",
    "TemplatesResource",
    "AsyncTemplatesResource",
    "RulesResource",
    "AsyncRulesResource",
    "TenDlcResource",
    "AsyncTenDlcResource",
    "WhatsAppResource",
    "AsyncWhatsAppResource",
]
