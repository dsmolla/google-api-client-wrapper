"""Gmail client module for Google API integration."""

from .client import EmailMessage, EmailAddress, EmailAttachment, Label
from .async_client import AsyncEmailMessage, AsyncEmailAddress, AsyncEmailAttachment, AsyncLabel
from .query_builder import EmailQueryBuilder
from .async_query_builder import AsyncEmailQueryBuilder

__all__ = [
    # Sync classes
    "EmailMessage",
    "EmailAddress", 
    "EmailAttachment",
    "Label",
    "EmailQueryBuilder",
    
    # Async classes
    "AsyncEmailMessage",
    "AsyncEmailAddress",
    "AsyncEmailAttachment", 
    "AsyncLabel",
    "AsyncEmailQueryBuilder",
]