from datetime import datetime
import pytz


def current_datetime(timezone: str) -> datetime:
    """
    Returns the current date and time in the given timezone.
    """
    now = datetime.now(pytz.utc)
    return now.astimezone(pytz.timezone(timezone))


def datetime_to_iso(date_time: datetime, timezone: str) -> str:
    """
    Converts a given datetime object to a string in ISO format, adjusted
    to the given timezone.
    """
    return datetime_to_zone(date_time, timezone).isoformat()


def iso_to_datetime(iso: str, timezone: str) -> datetime:
    """
    Converts a given iso format datetime to a timezone aware datetime object
    """
    date_time = datetime.fromisoformat(iso)
    return date_time.astimezone(pytz.timezone(timezone))


def datetime_to_zone(date_time: datetime, timezone: str) -> datetime:
    """
    Converts a given datetime object to a timezone-aware object.
    """
    return pytz.timezone(timezone).localize(date_time)

def convert_timezone(date_time: datetime, original_timezone: str, new_timezone: str) -> datetime:
    og_datetime = datetime_to_zone(date_time, original_timezone)
    return og_datetime.astimezone(pytz.timezone(new_timezone))

def datetime_to_readable(start: datetime, end: datetime = None) -> str:
    """
    Converts one or two ISO datetime strings into a human-readable format.
    """
    start = start.strftime("%a, %b %d, %Y %I:%M%p")

    if end:
        if end.day == datetime.strptime(start, "%a, %b %d, %Y %I:%M%p").day:
            end = end.strftime("%I:%M%p")
        else:
            end = end.strftime("%a, %b %d, %Y %I:%M%p")
    return f"{start} - {end}" if end else f"{start}"
