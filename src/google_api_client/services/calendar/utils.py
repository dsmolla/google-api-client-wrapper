from datetime import datetime
from typing import Optional, List, Dict, Any

from .types import CalendarEvent, Attendee, TimeSlot, FreeBusyResponse
from .constants import (
    MAX_SUMMARY_LENGTH, MAX_DESCRIPTION_LENGTH, MAX_LOCATION_LENGTH,
    VALID_EVENT_STATUSES, VALID_RESPONSE_STATUSES
)
from ...utils.datetime import convert_datetime_to_iso


# Import from shared utilities
from ...utils.validation import is_valid_email, validate_text_field, sanitize_header_value


def validate_datetime_range(start: Optional[datetime], end: Optional[datetime]) -> None:
    """Validates that start time is before end time."""
    if start and end and start >= end:
        raise ValueError("Event start time must be before end time")


def parse_datetime_from_api(datetime_data: Dict[str, Any]) -> Optional[datetime]:
    """
    Parse datetime from Google Calendar API response.
    
    Args:
        datetime_data: Dictionary containing dateTime or date fields
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not datetime_data:
        return None
        
    try:
        if datetime_data.get("dateTime"):
            # Handle timezone-aware datetime
            dt_str = datetime_data["dateTime"]
            if dt_str.endswith("Z"):
                dt_str = dt_str.replace("Z", "+00:00")
            return datetime.fromisoformat(dt_str)
        elif datetime_data.get("date"):
            # Handle all-day events (date only)
            return datetime.strptime(datetime_data["date"], "%Y-%m-%d")
    except (ValueError, TypeError):
        pass
        
    return None


def parse_attendees_from_api(attendees_data: List[Dict[str, Any]]) -> List[Attendee]:
    """
    Parse attendees from Google Calendar API response.
    
    Args:
        attendees_data: List of attendee dictionaries from API
        
    Returns:
        List of Attendee objects
    """
    attendees = []
    
    for attendee_data in attendees_data:
        email = attendee_data.get("email")
        if email and is_valid_email(email):
            try:
                response_status = attendee_data.get("responseStatus")
                if response_status and response_status not in VALID_RESPONSE_STATUSES:
                    response_status = None
                    
                attendees.append(Attendee(
                    email=email,
                    display_name=attendee_data.get("displayName"),
                    response_status=response_status
                ))
            except ValueError:
                pass
                
    return attendees


def from_google_event(google_event: Dict[str, Any]) -> CalendarEvent:
    """
    Create a CalendarEvent instance from a Google Calendar API response.
    
    Args:
        google_event: Dictionary containing event data from Google Calendar API
        
    Returns:
        CalendarEvent instance populated with the data from the dictionary
    """
    try:
        # Parse basic fields
        event_id = google_event.get("id")
        summary = google_event.get("summary", "").strip()
        description = google_event.get("description", "").strip() if google_event.get("description") else None
        location = google_event.get("location", "").strip() if google_event.get("location") else None
        html_link = google_event.get("htmlLink")
        
        # Parse datetimes
        start = parse_datetime_from_api(google_event.get("start", {}))
        end = parse_datetime_from_api(google_event.get("end", {}))
        
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
        if status not in VALID_EVENT_STATUSES:
            status = "confirmed"
        
        # Create and return the event
        event = CalendarEvent(
            event_id=event_id,
            summary=summary,
            description=description,
            location=location,
            start=start,
            end=end,
            html_link=html_link,
            attendees=attendees,
            recurrence=recurrence,
            recurring_event_id=recurring_event_id,
            creator=creator,
            organizer=organizer,
            status=status
        )
        
        return event
        
    except Exception:
        raise ValueError("Invalid event data - failed to parse calendar event")


def create_event_body(
    start: datetime,
    end: datetime,
    summary: str = None,
    description: str = None,
    location: str = None,
    attendees: List[Attendee] = None,
    recurrence: List[str] = None
) -> Dict[str, Any]:
    """
    Create event body dictionary for Google Calendar API.
    
    Args:
        start: Event start datetime
        end: Event end datetime  
        summary: Event summary/title
        description: Event description
        location: Event location
        attendees: List of attendees
        recurrence: List of recurrence rules
        
    Returns:
        Dictionary suitable for Calendar API requests
        
    Raises:
        ValueError: If required fields are invalid
    """
    if not start or not end:
        raise ValueError("Event must have both start and end times")
    if start >= end:
        raise ValueError("Event start time must be before end time")
    
    # Validate text fields
    validate_text_field(summary, MAX_SUMMARY_LENGTH, "summary")
    validate_text_field(description, MAX_DESCRIPTION_LENGTH, "description")
    validate_text_field(location, MAX_LOCATION_LENGTH, "location")
    
    # Build event body
    event_body = {
        'summary': summary or "New Event",
        'start': {'dateTime': convert_datetime_to_iso(start)},
        'end': {'dateTime': convert_datetime_to_iso(end)}
    }
    
    # Add optional fields
    if description:
        event_body['description'] = sanitize_header_value(description)
    if location:
        event_body['location'] = sanitize_header_value(location)
    if attendees:
        event_body['attendees'] = [attendee.to_dict() for attendee in attendees]
    if recurrence:
        event_body['recurrence'] = recurrence
        
    return event_body


def parse_freebusy_response(freebusy_data: Dict[str, Any]) -> FreeBusyResponse:
    """
    Parse a freebusy response from Google Calendar API.
    
    Args:
        freebusy_data: Dictionary containing freebusy response from API
        
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
        start = datetime.fromisoformat(time_min.replace('Z', '+00:00'))
        end = datetime.fromisoformat(time_max.replace('Z', '+00:00'))
        
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
                        period_start = datetime.fromisoformat(period_start_str.replace('Z', '+00:00'))
                        period_end = datetime.fromisoformat(period_end_str.replace('Z', '+00:00'))
                        busy_periods.append(TimeSlot(period_start, period_end))
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


def merge_overlapping_time_slots(time_slots: List[TimeSlot]) -> List[TimeSlot]:
    """
    Merge overlapping time slots into consolidated periods.
    
    Args:
        time_slots: List of TimeSlot objects that may overlap
        
    Returns:
        List of merged TimeSlot objects with no overlaps
    """
    if not time_slots:
        return []
    
    # Sort by start time
    sorted_slots = sorted(time_slots, key=lambda x: x.start)
    merged = [sorted_slots[0]]
    
    for current in sorted_slots[1:]:
        last_merged = merged[-1]
        
        # Check if current slot overlaps with the last merged slot
        if current.start <= last_merged.end:
            # Merge by extending the end time if necessary
            if current.end > last_merged.end:
                merged[-1] = TimeSlot(last_merged.start, current.end)
        else:
            # No overlap, add as new slot
            merged.append(current)
    
    return merged


def validate_freebusy_request(
    start: datetime,
    end: datetime,
    calendar_ids: List[str]
) -> None:
    """
    Validate parameters for a freebusy request.
    
    Args:
        start: Start datetime for the query
        end: End datetime for the query
        calendar_ids: List of calendar IDs to query
        
    Raises:
        ValueError: If any parameter is invalid
    """
    from .constants import MAX_FREEBUSY_DAYS_RANGE, MAX_CALENDARS_PER_FREEBUSY_QUERY
    
    if start >= end:
        raise ValueError("Start time must be before end time")
    
    # Check maximum time range (Google's API limit)
    days_diff = (end - start).days
    if days_diff > MAX_FREEBUSY_DAYS_RANGE:
        raise ValueError(f"Time range cannot exceed {MAX_FREEBUSY_DAYS_RANGE} days")
    
    if not calendar_ids:
        raise ValueError("At least one calendar ID must be specified")
    
    if len(calendar_ids) > MAX_CALENDARS_PER_FREEBUSY_QUERY:
        raise ValueError(f"Cannot query more than {MAX_CALENDARS_PER_FREEBUSY_QUERY} calendars at once")