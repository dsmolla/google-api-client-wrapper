"""Gmail client module for Google API integration."""

from .api_service import GmailApiService
from .query_builder import EmailQueryBuilder
from .types import EmailMessage, EmailAddress, EmailAttachment, Label

__all__ = [
    # Sync classes
    "EmailMessage",
    "EmailAddress", 
    "EmailAttachment",
    "Label",
    "EmailQueryBuilder",

]