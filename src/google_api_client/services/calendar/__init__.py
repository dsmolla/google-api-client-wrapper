"""Calendar client module for Google API integration."""

from .client import CalendarEvent, Attendee
from .query_builder import EventQueryBuilder

__all__ = [
    # Sync classes
    "CalendarEvent",
    "Attendee",
    "EventQueryBuilder",
]