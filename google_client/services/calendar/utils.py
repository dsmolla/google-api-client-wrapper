from datetime import datetime
from typing import Optional, List, Dict, Any

from google_client.utils.datetime import iso_to_datetime
from .types import CalendarEvent, Attendee, TimeSlot, FreeBusyResponse


def validate_datetime_range(start: datetime, end: datetime) -> None:
    """Validates that start time is before end time."""
    if start >= end:
        raise ValueError("Event start time must be before end time")


def parse_datetime_from_api(datetime_data: Dict[str, Any], timezone: str) -> Optional[datetime]:
    """
    Parse datetime from Google Calendar API response.
    """
    if datetime_data.get("dateTime"):
        # Handle timezone-aware datetime
        dt_str = datetime_data["dateTime"]
        return iso_to_datetime(dt_str, timezone)
    elif datetime_data.get("date"):
        # Handle all-day events (date only)
        return datetime.strptime(datetime_data["date"], "%Y-%m-%d")


def parse_attendees_from_api(attendees_data: List[Dict[str, Any]]) -> List[Attendee]:
    """
    Parse attendees from Google Calendar API response.
    """
    attendees = []

    for attendee_data in attendees_data:
        attendees.append(Attendee(
            email=attendee_data.get("email"),
            display_name=attendee_data.get("displayName"),
            response_status=attendee_data.get("responseStatus")
        ))

    return attendees


def from_google_event(google_event: Dict[str, Any], calendar_id: str, timezone: str) -> CalendarEvent:
    """
    Create a CalendarEvent instance from a Google Calendar API response.
    """
    try:
        # Parse basic fields
        event_id = google_event.get("id")
        summary = google_event.get("summary")
        description = google_event.get("description")
        location = google_event.get("location")
        html_link = google_event.get("htmlLink")

        # Parse datetimes
        start = parse_datetime_from_api(google_event.get("start", {}), timezone)
        end = parse_datetime_from_api(google_event.get("end", {}), timezone)

        # Parse attendees
        attendees_data = google_event.get("attendees", [])
        attendees = parse_attendees_from_api(attendees_data)

        # Parse recurrence
        recurrence = google_event.get("recurrence", [])
        recurring_event_id = google_event.get("recurringEventId")

        # Parse creator and organizer
        creator_data = google_event.get("creator", {})
        creator = creator_data.get("email") if creator_data else None

        organizer_data = google_event.get("organizer", {})
        organizer = organizer_data.get("email") if organizer_data else None

        # Parse status
        status = google_event.get("status", "confirmed")

        # Parse Google Meets link
        google_meets_link = None
        conference_data = google_event.get('conferenceData', {})
        entry_points = conference_data.get('entryPoints', [])

        for entry in entry_points:
            if entry.get('entryPointType') == 'video':
                google_meets_link = entry.get('uri')

        # Create and return the event
        event = CalendarEvent(
            event_id=event_id,
            calendar_id=calendar_id,
            summary=summary,
            description=description,
            location=location,
            start=start,
            end=end,
            html_link=html_link,
            attendees=attendees,
            google_meets_link=google_meets_link,
            recurrence=recurrence,
            recurring_event_id=recurring_event_id,
            creator=creator,
            organizer=organizer,
            status=status,
            timezone=timezone
        )

        return event

    except Exception:
        raise ValueError("Invalid event data - failed to parse calendar event")


def parse_freebusy_response(freebusy_data: Dict[str, Any], timezone: str) -> FreeBusyResponse:
    """
    Parse a freebusy response from Google Calendar API.

    Args:
        freebusy_data: Dictionary containing freebusy response from API
        timezone: The timezone to convert datetime to

    Returns:
        FreeBusyResponse object with parsed data

    Raises:
        ValueError: If the response data is invalid
    """
    if not freebusy_data:
        raise ValueError("Empty freebusy response data")

    try:
        # Parse time range
        time_min = freebusy_data.get("timeMin")
        time_max = freebusy_data.get("timeMax")

        if not time_min or not time_max:
            raise ValueError("Missing timeMin or timeMax in freebusy response")

        # Parse start and end times
        start = iso_to_datetime(time_min, timezone)
        end = iso_to_datetime(time_max, timezone)

        # Parse calendar busy periods
        calendars = {}
        calendars_data = freebusy_data.get("calendars", {})

        for calendar_id, calendar_data in calendars_data.items():
            busy_periods = []
            busy_data = calendar_data.get("busy", [])

            for busy_period in busy_data:
                period_start_str = busy_period.get("start")
                period_end_str = busy_period.get("end")

                if period_start_str and period_end_str:
                    try:
                        period_start = iso_to_datetime(period_start_str, timezone)
                        period_end = iso_to_datetime(period_end_str, timezone)
                        busy_periods.append(TimeSlot(start=period_start, end=period_end))
                    except (ValueError, TypeError):
                        continue

            calendars[calendar_id] = busy_periods

        # Parse errors
        errors = {}
        errors_data = freebusy_data.get("errors", {})

        for calendar_id, error_data in errors_data.items():
            if isinstance(error_data, list) and error_data:
                error_reason = error_data[0].get("reason", "Unknown error")
                errors[calendar_id] = error_reason
            elif isinstance(error_data, str):
                errors[calendar_id] = error_data

        return FreeBusyResponse(
            start=start,
            end=end,
            calendars=calendars,
            errors=errors
        )

    except Exception as e:
        raise ValueError(f"Failed to parse freebusy response: {str(e)}")
