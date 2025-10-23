"""Gmail client module for Google API integration."""

from .api_service import GmailApiService
from .async_api_service import AsyncGmailApiService
from .query_builder import EmailQueryBuilder
from .types import EmailMessage, EmailAddress, EmailAttachment, Label, EmailThread

__all__ = [
    "EmailMessage",
    "EmailAddress", 
    "EmailAttachment",
    "Label",
    "EmailThread",
    "EmailQueryBuilder",
    "GmailApiService",
    "AsyncGmailApiService",
]