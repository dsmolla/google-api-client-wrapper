import re
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from .types import CalendarEvent, Attendee
from .constants import (
    MAX_SUMMARY_LENGTH, MAX_DESCRIPTION_LENGTH, MAX_LOCATION_LENGTH,
    VALID_EVENT_STATUSES, VALID_RESPONSE_STATUSES
)
from ...utils.datetime import convert_datetime_to_iso

logger = logging.getLogger(__name__)


def is_valid_email(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_text_field(value: Optional[str], max_length: int, field_name: str) -> None:
    """Validates text field length and content."""
    if value and len(value) > max_length:
        raise ValueError(f"Event {field_name} cannot exceed {max_length} characters")


def sanitize_header_value(value: str) -> str:
    """
    Sanitize a string value for safe use in API requests.
    
    Args:
        value: The string to sanitize
    
    Returns:
        Sanitized string safe for use in API calls
    """
    if not value:
        return ""
    
    # Remove control characters that could cause issues
    sanitized = re.sub(r'[\r\n\x00-\x1f\x7f-\x9f]', '', value)
    
    # Remove any quotes that could break the structure
    sanitized = sanitized.replace('"', '')
    
    return sanitized.strip()


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
    except (ValueError, TypeError) as e:
        logger.warning("Failed to parse datetime: %s", e)
        
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
                    logger.warning("Invalid response status: %s, setting to None", response_status)
                    response_status = None
                    
                attendees.append(Attendee(
                    email=email,
                    display_name=attendee_data.get("displayName"),
                    response_status=response_status
                ))
            except ValueError as e:
                logger.warning("Skipping invalid attendee: %s", e)
                
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
            logger.warning("Invalid event status: %s, defaulting to confirmed", status)
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
        
    except Exception as e:
        logger.error("Failed to parse Google Calendar event: %s", e)
        logger.debug("Event data: %s", str(google_event)[:500])
        raise ValueError(f"Invalid event data: {e}")


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