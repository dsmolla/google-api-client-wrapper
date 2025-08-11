

class CalendarError(Exception):
    """Base exception for Calendar API errors."""
    pass


class EventNotFoundError(CalendarError):
    """Raised when a calendar event is not found."""
    pass


class CalendarNotFoundError(CalendarError):
    """Raised when a calendar is not found."""
    pass


class CalendarPermissionError(CalendarError):
    """Raised when the user lacks permission for a calendar operation."""
    pass


class EventConflictError(CalendarError):
    """Raised when there is a conflict with calendar event operations."""
    pass


class InvalidEventDataError(CalendarError):
    """Raised when event data is invalid or malformed."""
    pass


class RecurrenceError(CalendarError):
    """Raised when there are issues with recurring event operations."""
    pass