"""Sendly SDK Resources"""

from .messages import AsyncMessagesResource, MessagesResource
from .verify import AsyncVerifyResource, VerifyResource
from .templates import AsyncTemplatesResource, TemplatesResource

__all__ = [
    "MessagesResource",
    "AsyncMessagesResource",
    "VerifyResource",
    "AsyncVerifyResource",
    "TemplatesResource",
    "AsyncTemplatesResource",
]
