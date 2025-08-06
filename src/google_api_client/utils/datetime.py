from datetime import datetime, date, time, timedelta
import tzlocal


def current_datetime_local_timezone() -> datetime:
    """
    Returns the current date and time in the local timezone.

    Returns:
        A datetime object representing the current date and time.
    """
    return datetime.now(tzlocal.get_localzone())


def convert_datetime_to_iso(date_time: datetime) -> str:
    """
    Converts a given datetime object to a string in ISO format, adjusted
    to the local timezone.

    Args:
        date_time: The datetime object to be converted.

    Returns:
        The ISO formatted string of the datetime in the local timezone.
    """
    return date_time.astimezone(tzlocal.get_localzone()).isoformat()

def convert_datetime_to_readable(start: datetime, end: datetime = None) -> str:
    """
    Converts one or two ISO datetime strings into a human-readable format.
    This function accepts a mandatory `start` time and an optional `end` time.
    Both inputs are expected to be in ISO format. The output will be a
    formatted string where the time is displayed in a readable format with varying
    detail based on the relationship between the provided `start` and `end`
    timestamps. If only the `start` time is provided, the result will contain only
    the formatted `start` time. If an `end` time is provided, the display will
    depend on whether the two timestamps occur on the same day or on different days.

    Args:
        start: A datetime string in ISO format representing the starting
            time of the event.
        end: An optional datetime string in ISO format representing the
            ending time of the event. Default is None.

    Returns:
        A formatted string combining `start` and `end` times in a
            human-readable form.
    """
    start = start.strftime("%a, %d %b %Y %I:%M %p")
    
    if end:
        if end.day == datetime.strptime(start, "%a, %d %b %Y %I:%M %p").day:
            # If start and end are on the same day
            end = end.strftime("%I:%M %p")
        else:
            end = end.strftime("%a, %d %b %Y %I:%M %p")
    return f"{start} - {end}" if end else f"{start}"

def convert_datetime_to_local_timezone(date_time: datetime) -> datetime:
    """
    Converts a given datetime object to a local-timezone-aware timezone.
    Args:
        date_time: The datetime object to be converted.

    Returns:
        A datetime object representing the local-timezone-aware timezone.
    """
    return datetime.astimezone(date_time, tzlocal.get_localzone())


def combine_with_timezone(date_obj: date, time_obj: time) -> datetime:
    """
    Combines a date and time into a timezone-aware datetime using the local timezone.
    
    Args:
        date_obj: The date component
        time_obj: The time component
        
    Returns:
        A timezone-aware datetime object in the local timezone
    """
    naive_datetime = datetime.combine(date_obj, time_obj)
    local_tz = tzlocal.get_localzone()
    return naive_datetime.replace(tzinfo=local_tz)


def today_start() -> datetime:
    """
    Returns the start of today (00:00:00) in the local timezone.
    
    Returns:
        A timezone-aware datetime representing the start of today
    """
    return combine_with_timezone(date.today(), time.min)


def today_end() -> datetime:
    """
    Returns the end of today (23:59:59.999999) in the local timezone.
    
    Returns:
        A timezone-aware datetime representing the end of today
    """
    return combine_with_timezone(date.today(), time.max)


def date_start(target_date: date) -> datetime:
    """
    Returns the start of the specified date (00:00:00) in the local timezone.
    
    Args:
        target_date: The date to get the start of
        
    Returns:
        A timezone-aware datetime representing the start of the specified date
    """
    return combine_with_timezone(target_date, time.min)


def date_end(target_date: date) -> datetime:
    """
    Returns the end of the specified date (23:59:59.999999) in the local timezone.
    
    Args:
        target_date: The date to get the end of
        
    Returns:
        A timezone-aware datetime representing the end of the specified date
    """
    return combine_with_timezone(target_date, time.max)


def days_from_today(days: int) -> datetime:
    """
    Returns the start of a date that is N days from today in the local timezone.
    
    Args:
        days: Number of days from today (positive for future, negative for past)
        
    Returns:
        A timezone-aware datetime representing the start of the target date
    """
    target_date = date.today() + timedelta(days=days)
    return date_start(target_date)
