"""Calendar client module for Google API integration."""

from .api_service import CalendarApiService
from .types import CalendarEvent, Attendee
from .query_builder import EventQueryBuilder

__all__ = [
    # Service layer
    "CalendarApiService",
    
    # Data types
    "CalendarEvent",
    "Attendee",
    
    # Query builder
    "EventQueryBuilder",
]