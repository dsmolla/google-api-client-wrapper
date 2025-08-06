"""Calendar client module for Google API integration."""

from .client import CalendarEvent, Attendee
from .async_client import AsyncCalendarEvent, AsyncAttendee
from .query_builder import EventQueryBuilder
from .async_query_builder import AsyncEventQueryBuilder

__all__ = [
    # Sync classes
    "CalendarEvent",
    "Attendee",
    "EventQueryBuilder",
    
    # Async classes
    "AsyncCalendarEvent",
    "AsyncAttendee", 
    "AsyncEventQueryBuilder",
]