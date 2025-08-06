from .base import APIError


class CalendarError(APIError):
    """Base exception for Calendar API errors."""
    pass


class EventNotFoundError(CalendarError):
    """Raised when a calendar event is not found."""
    pass


class CalendarNotFoundError(CalendarError):
    """Raised when a calendar is not found."""
    pass